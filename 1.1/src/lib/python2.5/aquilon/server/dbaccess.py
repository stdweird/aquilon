#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# $Header$
# $Change$
# $DateTime$
# $Author$
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""All database access should funnel through this module to ensure that it
is properly backgrounded within twisted, and not blocking execution.

Most methods will be called as part of a callback chain, and should
expect to handle a generic result from whatever happened earlier in
the chain.

"""

import os
import re
import exceptions

from sasync.database import AccessBroker, transact
from sqlalchemy.exceptions import InvalidRequestError
from sqlalchemy import and_, or_
from twisted.internet import defer
from twisted.python import log
from twisted.python.failure import Failure

from aquilon import const
from aquilon.exceptions_ import RollbackException, NotFoundException, \
        AuthorizationException, ArgumentError
from formats import printprep
from aquilon.aqdb.location import Location, LocationType, Company, Hub, \
        Continent, Country, City, Building, Rack, Chassis, Desk
from aquilon.aqdb.network import DnsDomain
from aquilon.aqdb.service import Host, QuattorServer, Domain
from aquilon.aqdb.configuration import Archetype
from aquilon.aqdb.auth import UserPrincipal
from aquilon.aqdb.hardware import Vendor, HardwareType, Model, Machine

# FIXME: This probably belongs in location.py
const.location_types = ("company", "hub", "continent", "country", "city",
        "building", "rack", "chassis", "desk")

class DatabaseBroker(AccessBroker):
    """All database access eventually funnels through this class, to
    correctly handle backgrounding / threading within twisted.

    As a general rule, the methods here should reflect the actions
    being invoked by the client.
    """

    def startup(self):
        """This method normally creates Deferred objects for setting up
        the tables.  However, in our setup, all this work has already
        been done by importing aquilon.aqdb modules.
        """
        pass

    @transact
    def add_host(self, result, hostname, machine):
        # To be able to enter this host into DSDB, there must be
        # - A valid machine being attached
        # - A bootable interface attached to the machine
        # - An IP Address attached to the interface
        # All interfaces present must be entered into DSDB at this
        # point.  Calls to add_interface will need to check if the
        # machine is associated with a host... if it is, a DSDB
        # call will need to be made there to create the interface.
        # The same goes for del_interface... if a host is associated
        # with the machine, a dsdb command will need to be issued.
        newHost = Host(name)
        self.session.save(newHost)
        return printprep(newHost)

    @transact
    def del_host(self, result, hostname):
        # Not sure whether to delete the host first from DSDB or from
        # here.  Both need to happen.
        oldHost = self.session.query(Host).filter_by(name=name).one()
        self.session.delete(oldHost)
        return

    @transact
    def show_host_all(self, result, **kwargs):
        """Hacked such that printing the list out to a client only
        shows fqdn.  Ideally, the printing layer would handle this
        intelligently - print only fqdn for a list of hosts in raw 
        mode, or fqdn plus links in html.
        
        """
        return [host.fqdn for host in self.session.query(Host).all()]

    @transact
    def show_host(self, result, hostname, **kwargs):
        return printprep(self._hostname_to_host(hostname))

    @transact
    def add_location(self, result, name, type, parentname, parenttype,
            fullname, comments, user, **kwargs):
        newLocation = self.session.query(Location).filter_by(name=name
                ).join('type').filter_by(type=type).first()
        if newLocation:
            # FIXME: Technically this is coming in with an http PUT,
            # which should try to adjust state and succeed if everything
            # is alright.
            raise ArgumentError("Location name=%s type=%s already exists."
                    % (name, type))
        try:
            parent = self.session.query(Location).filter_by(name=parentname
                    ).join('type').filter_by(type=parenttype).one()
        except InvalidRequestError:
            raise ArgumentError(
                    "Parent Location type='%s' name='%s' not found."
                    % (parenttype, parentname))
        # Incoming looks like 'city', need the City class.
        location_type = globals()[type.capitalize()]
        if not issubclass(location_type, Location):
            raise ArgumentError("%s is not a known location type" % type)
        try:
            dblt = self.session.query(LocationType).filter_by(type=type).one()
        except InvalidRequestError:
            raise ArgumentError("Invalid type '%s'" % type)

        # Figure out if it is valid to add this type of child to the parent...
        found_parent = False
        found_new = False
        for t in const.location_types:
            if t == parenttype:
                # Great, found the parent type in the list before requested type
                found_parent = True
                continue
            if t != type:
                # This item is neither parent nor new, keep going...
                continue
            # Moment of truth.
            if found_parent:
                # We saw the parent earlier - life is good.
                found_new = True
                break
            raise ArgumentError("type %s cannot be a parent of %s",
                    (parenttype, type))
        if not found_new:
            raise ArgumentError("unknown type %s", type)

        optional_args = {}
        if fullname:
            optional_args["fullname"] = fullname
        if comments:
            optional_args["comments"] = comments

        newLocation = location_type(name=name, type_name=dblt,
                parent=parent, owner=user, **optional_args)
        return printprep([newLocation])

    @transact
    def del_location(self, result, name, type, user, **kwargs):
        try:
            oldLocation = self.session.query(Location).filter_by(name=name
                    ).join('type').filter_by(type=type).one()
        except InvalidRequestError:
            raise NotFoundException(
                    "Location type='%s' name='%s' not found."
                    % (type, name))
        self.session.delete(oldLocation)
        return

    @transact
    def show_location(self, result, type=None, name=None, **kwargs):
        #log.msg("Attempting to generate a query...")
        query = self.session.query(Location)
        if type:
            # Not this easy...
            #kwargs["LocationType.type"] = type
            #log.msg("Attempting to add a type...")
            query = query.join('type').filter_by(type=type)
            query = query.reset_joinpoint()
        if name:
            try:
                #log.msg("Attempting query for one...")
                return printprep([query.filter_by(name=name).one()])
            except InvalidRequestError:
                raise NotFoundException(
                        "Location type='%s' name='%s' not found."
                        % (type, name))
        #log.msg("Attempting to query for all...")
        return printprep(query.all())

    @transact
    def show_location_type(self, result, user, **kwargs):
        return printprep(
                self.session.query(LocationType).filter_by(**kwargs).all())

    @transact
    def make_aquilon(self, result, hostname, os, **kwargs):
        """This creates a template file and saves a copy in the DB.

        It does *not* do pan compile... that happens outside this method.
        """

        dbhost = self._hostname_to_host(hostname)
        # Currently, for the Host to be created it *must* be associated with
        # a Machine already.  If that ever changes, need to check here and
        # bail if dbhost.machine does not exist.

        # FIXME: This should be saved/stored with the Host.
        # The archetype will factor into the include path for the compiler.
        archetype = self.session.query(Archetype).filter(
                Archetype.name=="aquilon").one()

        # For now, these are assumed.
        base_template = "archetype/base"
        final_template = "archetype/final"

        # Need to get all the BuildItem objects for this host.
        # They should include:
        # - exactly one OS
        # - exactly one personality
        # And may include:
        # - many services
        # - many features

        # So, OS and personality probably stored with BuildItem.
        os_template = "os/linux/4.0.1-x86_64/config"
        personality_template = "usage/grid/config"


        # The hardware should be a file in basedir/"plenary", and refers
        # to nodename of the machine.  It should include any info passed
        # in from 'add machine'.
        hardware = "machine/na/np/6/31_c1n3"
        #hardware = "plenary/machine/<fullname hub>/<fullname building>/<name rack>/nodename"

        # machine should have interfaces as a list
        # Need at least one interface marked boot - that one first
        # Currently missing netmask / broadcast / gateway
        # because the IPAddress table has not yet been defined in interface.py
        # Since we are only creating from certain chassis at the moment...
        # Hard code for now for 172.31.29.0-127 and 128-255.
        interfaces = [ {"ip":"172.31.29.82", "netmask":"255.255.255.128",
                "broadcast":"172.31.29.127", "gateway":"172.31.29.1",
                "bootproto":"dhcp", "name":"eth0"} ]

        # Services are on the build item table...
        # Features are on the build item table...
        services = [ "service/afs/q.ny.ms.com/client/config" ]
        # Service - has a CfgPath
        # ServiceInstance - combo of Service and System
        # ServiceMap

        templates = []
        templates.append(base_template)
        templates.append(os_template)
        for service in services:
            templates.append(service)
        templates.append(personality_template)
        templates.append(final_template)

        template_lines = []
        template_lines.append("object template %s;\n" % dbhost.fqdn)
        template_lines.append("""include { "pan/units" };\n""")
        template_lines.append(""""/hardware" = create("%s");\n""" % hardware)
        for interface in interfaces:
            template_lines.append(""""/system/network/interfaces/%(name)s" = nlist("ip", "%(ip)s", "netmask", "%(netmask)s", "broadcast", "%(broadcast)s", "gateway", "%(gateway)s", "bootproto", "%(bootproto)s");""")
        for template in templates:
            template_lines.append("""include { "%s" };""" % template)
        template_string = "\n".join(template_lines)

        # FIXME: Save this to the build table...
        buildid = -1
        return dbhost.fqdn, dbhost.domain.name, buildid, template_string

    @transact
    def cancel_make(self, failure):
        """Gets called as an Errback if the make_aquilon build fails."""
        error = failure.check(RollbackException)
        if not error:
            return failure
        # FIXME: Do the actual work of cancelling the make.
        return Failure(failure.value.cause)

    @transact
    def confirm_make(self, buildid):
        """Gets called if the make_aquilon build succeeds."""
        # FIXME: Should finalize the build table...

    # This should probably move over to UserPrincipal
    principal_re = re.compile(r'^(.*)@([^@]+)$')
    def split_principal(self, user):
        if not user:
            return (user, None)
        m = self.principal_re.match(user)
        if m:
            return (m.group(1), m.group(2))
        return (user, None)

    @transact
    def add_domain(self, result, domain, user, **kwargs):
        """Add the domain to the database, initialize as necessary."""
        (user, realm) = self.split_principal(user)
        # FIXME: UserPrincipal should include the realm...
        dbuser = self.session.query(UserPrincipal).filter_by(name=user).first()
        if not dbuser:
            if not user:
                raise AuthorizationException("Cannot create a domain without"
                        + " an authenticated connection.")
            dbuser = UserPrincipal(user)
            self.session.save_or_update(dbuser)
        # NOTE: Defaulting the name of the quattor server to quattorsrv.
        quattorsrv = self.session.query(QuattorServer).filter_by(
                name='quattorsrv').one()
        # For now, succeed without error if the domain already exists.
        dbdomain = self.session.query(Domain).filter_by(name=domain).first()
        # FIXME: Check that the domain name is composed only of characters
        # that are valid for a directory name.
        if not dbdomain:
            dbdomain = Domain(domain, quattorsrv, dbuser)
            self.session.save_or_update(dbdomain)
        # We just need to confirm that the new domain can be added... do
        # not need anything from the DB to be passed to pbroker.
        return dbdomain.name

    @transact
    def del_domain(self, result, domain, user, **kwargs):
        """Remove the domain from the database."""
        # Do we need to delete any dependencies before deleting the domain?
        (user, realm) = self.split_principal(user)
        # NOTE: Defaulting the name of the quattor server to quattorsrv.
        quattorsrv = self.session.query(QuattorServer).filter_by(
                name='quattorsrv').one()
        # For now, succeed without error if the domain does not exist.
        try:
            dbdomain = self.session.query(Domain).filter_by(name=domain).one()
        except InvalidRequestError:
            return domain
        if quattorsrv != dbdomain.server:
            log.err("FIXME: Should be redirecting this operation.")
        # FIXME: Entitlements will need to happen at this point.
        if dbdomain:
            self.session.delete(dbdomain)
        # We just need to confirm that domain was removed from the db...
        # do not need anything from the DB to be passed to pbroker.
        return domain

    @transact
    def verify_domain(self, result, domain, **kwargs):
        """This checks both that the domain exists *and* that this is
        the correct server to handle requests for the domain."""
        # NOTE: Defaulting the name of the quattor server to quattorsrv.
        quattorsrv = self.session.query(QuattorServer).filter_by(
                name='quattorsrv').one()
        try:
            dbdomain = self.session.query(Domain).filter_by(name=domain).one()
        except InvalidRequestError:
            raise NotFoundException("Domain '%s' not found." % domain)
        if quattorsrv != dbdomain.server:
            log.err("FIXME: Should be redirecting this operation.")
        return dbdomain.name

    @transact
    def status(self, result, stat, user, **kwargs):
        """Return status information from the database."""
        stat.extend(self.session.query(Domain).all())
        (user, realm) = self.split_principal(user)
        # FIXME: UserPrincipal should include the realm...
        dbuser = self.session.query(UserPrincipal).filter_by(name=user).first()
        if user and not dbuser:
            dbuser = UserPrincipal(user)
            self.session.save_or_update(dbuser)
        if dbuser:
            stat.append(dbuser)
        for line in stat:
            printprep(line)


    @transact
    def add_model(self, result, name, vendor, hardware, **kwargs):
        v = self.session.query(Vendor).filter_by(name = vendor).first()
        if (v is None):
            raise ArgumentError("Vendor '"+vendor+"' not found!")

        h = self.session.query(HardwareType).filter_by(type = hardware).first()
        if (h is None):
            raise ArgumentError("Hardware type '"+hardware+"' not found!")

        try:
            model = Model(name, v, h)
            self.session.save(model)
        except InvalidRequestError, e:
            raise ValueError("Requested operation could not be completed!\n"+ e.__str__())
        return "New model successfully created"

    @transact
    def del_model(self, result, name, vendor, hardware, **kwargs):
        v = self.session.query(Vendor).filter_by(name = vendor).first()
        if (v is None):
            raise ArgumentError("Vendor '"+vendor+"' not found!")

        h = self.session.query(HardwareType).filter_by(type = hardware).first()
        if (h is None):
            raise ArgumentError("Hardware type '"+hardware+"' not found!")

        m = self.session.query(Model).filter_by(name = name, vendor = v, hardware_type = h).first()
        if (m is None):
            raise ArgumentError('Requested model was not found in the database')

        try:
            self.session.delete(m)
        except InvalidRequestError, e:
            raise ValueError("Requested operation could not be completed!\n"+ e.__str__())
        return "Model successfully deleted"

    @transact
    def add_machine(self, result, name, location, type, model, **kwargs):
        if (type not in ['chassis', 'rack', 'desk']):
            raise ArgumentError ('Invalid location type: '+type)
        if (type == 'chassis'):
            loc = self.session.query(Chassis).filter_by(name = location).first()
        elif (type == 'rack'):
            loc = self.session.query(Rack).filter_by(name = location).first()
        else:
            loc = self.session.query(Desk).filter_by(name = location).first()
        if (loc is None):
            raise ArgumentError("Location name '"+location+"' not found!")

        mod = self.session.query(Model).filter_by(name = model).first()
        if (mod is None):
            raise ArgumentError("Model name '"+model+"' not found!");

        try:
            m = Machine(loc, mod, name=name)
            self.session.save(m)
        except InvalidRequestError, e:
            raise ValueError("Requested machine could not be created!\n"+e.__str__())
        return "New machine succesfully created"

    @transact
    def show_machine(self, result, **kwargs):
        try:
            q = self.session.query(Machine)
            if (kwargs['name'] is not None):
                q = q.filter(Machine.name.like(kwargs['name']+'%'))
            if (kwargs['location'] is not None and 
                kwargs['type'] is not None):
                if (kwargs['type'] not in ['chassis', 'rack', 'desk']):
                    raise ArgumentError ('Invalid location type')
                q = q.join('location').filter(Location.name.like(kwargs['location']+'%'))
                q = q.filter(LocationType.type == kwargs['type'])
                q = q.reset_joinpoint()
            if (kwargs['model'] is not None):
                q = q.join('model').filter(Model.name.like(kwargs['model']+'%'))
            return printprep(q.all())
        except InvalidRequestError, e:
            raise ValueError("Error while querying the database!\n"+e.__str__())

    @transact
    def del_machine(self, result, name, location, type, **kwargs):
        if (type not in ['chassis', 'rack', 'desk']):
            raise ArgumentError ('Invalid location type: '+type)
        if (type == 'chassis'):
            loc = self.session.query(Chassis).filter_by(name = location).first()
        elif (type == 'rack'):
            loc = self.session.query(Rack).filter_by(name = location).first()
        else:
            loc = self.session.query(Desk).filter_by(name = location).first()
        if (loc is None):
            raise ArgumentError("Location name '"+location+"' not found!")

        try:
            m = self.session.query(Machine).filter_by(name = name, location = loc).one()
            self.session.delete(m)
        except InvalidRequestError, e:
            raise ValueError("Requested machine could not be deleted!\n"+e.__str__())
        return "Successfull deletion"

    @transact
    def manage(self, result, domain, hostname, user, **kwargs):
        try:
            dbdomain = self.session.query(Domain).filter_by(name=domain).one()
        except InvalidRequestError:
            raise NotFoundException("Domain '%s' not found." % domain)
        dbhost = self._hostname_to_host(hostname)
        dbhost.domain = dbdomain
        self.session.save_or_update(dbhost)
        return

    # Expects to be run under a @transact method with session=True.
    def _hostname_to_host(self, hostname):
        components = hostname.split(".")
        if len(components) <= 1:
            raise ArgumentError(
                    "'%s' invalid, hostname must be fully qualified."
                    % hostname)
        if len(components) == 2:
            # Try .ms.com?
            raise ArgumentError(
                    "'%s' invalid, hostname must be fully qualified."
                    % hostname)
        short = components.pop(0)
        root = components.pop(-2) + "." + components.pop(-1)
        try:
            dns_domain = self.session.query(DnsDomain).filter_by(
                    name=root, parent=None).one()
        except InvalidRequestError, e:
            raise NotFoundException("Root DNS domain '%s' not found." % root)
        while components:
            component = components.pop(-1)
            try:
                dns_domain = self.session.query(DnsDomain).filter_by(
                        name=component, parent=dns_domain).one()
            except InvalidRequestError, e:
                raise NotFoundException(
                        "DNS domain '%s' with parent '%s' not found."
                        % (component, repr(domain)))
        try:
            host = self.session.query(Host).filter_by(
                    name=short, dns_domain=dns_domain).one()
        except InvalidRequestError, e:
            raise NotFoundException("Host '%s' with DNS domain '%s' not found."
                    % (short, repr(dns_domain)))
        return printprep(host)

