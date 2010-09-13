# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2008,2009,2010  Contributor
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the EU DataGrid Software License.  You should
# have received a copy of the license with this program, and the
# license is published at
# http://eu-datagrid.web.cern.ch/eu-datagrid/license.html.
#
# THE FOLLOWING DISCLAIMER APPLIES TO ALL SOFTWARE CODE AND OTHER
# MATERIALS CONTRIBUTED IN CONNECTION WITH THIS PROGRAM.
#
# THIS SOFTWARE IS LICENSED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE AND ANY WARRANTY OF NON-INFRINGEMENT, ARE
# DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY,
# OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT
# OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. THIS
# SOFTWARE MAY BE REDISTRIBUTED TO OTHERS ONLY BY EFFECTIVELY USING
# THIS OR ANOTHER EQUIVALENT DISCLAIMER AS WELL AS ANY OTHER LICENSE
# TERMS THAT MAY APPLY.
"""Contains the logic for `aq add switch`."""


from aquilon.exceptions_ import ArgumentError, ProcessException
from aquilon.server.broker import BrokerCommand
from aquilon.server.dbwrappers.location import get_location
from aquilon.server.dbwrappers.hardware_entity import parse_primary_name
from aquilon.server.processes import DSDBRunner
from aquilon.aqdb.model import Switch, Model


class CommandAddSwitch(BrokerCommand):

    required_parameters = ["switch", "model", "rack", "type", "ip"]

    def render(self, session, logger, switch, label, model, rack, type, ip,
               vendor, serial, comments, **arguments):
        dbmodel = Model.get_unique(session, name=model, vendor=vendor,
                                   machine_type='switch', compel=True)

        dblocation = get_location(session, rack=rack)

        dbdns_rec = parse_primary_name(session, switch, ip)
        if not label:
            label = dbdns_rec.name

        # FIXME: What do the error messages for an invalid enum (switch_type)
        # look like?
        dbswitch = Switch(label=label, switch_type=type, location=dblocation,
                          model=dbmodel, serial_no=serial, comments=comments)
        session.add(dbswitch)
        dbswitch.primary_name = dbdns_rec

        session.flush()

        dsdb_runner = DSDBRunner(logger=logger)
        try:
            dsdb_runner.add_host_details(dbswitch.fqdn, dbswitch.primary_ip,
                                         name=None, mac=None)
        except ProcessException, e:
            raise ArgumentError("Could not add switch to DSDB: %s" % e)
        return
