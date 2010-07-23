# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2009,2010  Contributor
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
""" tables/classes applying to clusters """
from datetime import datetime

from sqlalchemy import (Column, Integer, String, DateTime, Sequence, ForeignKey,
                        UniqueConstraint)

from sqlalchemy.orm import relation, backref, object_session
from sqlalchemy.ext.associationproxy import association_proxy

from aquilon.exceptions_ import ArgumentError
from aquilon.aqdb.column_types import AqStr
from aquilon.aqdb.model import (Base, Host, Service, Location, Personality,
                                ServiceInstance, Machine, Branch, TorSwitch,
                                UserPrincipal)

# List of functions allowed to be used in vmhost_capacity_function
restricted_builtins = {'None': None,
                       'dict': dict,
                       'divmod': divmod,
                       'float': float,
                       'int': int,
                       'len': len,
                       'long': long,
                       'max': max,
                       'min': min,
                       'pow': pow,
                       'round': round}


def convert_resources(resources):
    """ Convert a list of dicts to a dict of lists """
    # Turn this: [{'a': 1, 'b': 1},
    #             {'a': 2, 'b': 2}]
    #
    # Into this: {'a': [1, 2],
    #             'b': [1, 2]}
    resmap = {}
    for res in resources:
        for name, value in res.items():
            if name not in resmap:
                resmap[name] = []
            resmap[name].append(value)
    return resmap


#cluster is a reserved word in oracle and may not
_TN = 'clstr'
class Cluster(Base):
    """
        A group of two or more hosts for high availablility or grid capabilities
        Location constraint is nullable as it may or may not be used
    """
    __tablename__ = _TN

    id = Column(Integer, Sequence('%s_seq'%(_TN)), primary_key=True)
    cluster_type = Column(AqStr(16), nullable=False)
    name = Column(AqStr(64), nullable=False)

    #Lack of cascaded deletion is intentional on personality
    personality_id = Column(Integer, ForeignKey('personality.id',
                                                name='cluster_prsnlty_fk'),
                            nullable=False)

    branch_id = Column(Integer, ForeignKey('branch.id',
                                           name='cluster_branch_fk'),
                                           nullable=False)

    sandbox_author_id = Column(Integer,
                               ForeignKey('user_principal.id',
                                          name='cluster_sandbox_author_fk'),
                               nullable=True)

    location_constraint_id = Column(ForeignKey('location.id',
                                               name='cluster_location_fk'))

    #esx cluster __init__ method overrides this default
    max_hosts = Column(Integer, default=2, nullable=True)
    creation_date = Column(DateTime, default=datetime.now, nullable=False)
    comments      = Column(String(255))

    location_constraint = relation(Location,
                                   uselist=False,
                                   lazy=False)

    personality = relation(Personality, uselist=False, lazy=False)
    branch = relation(Branch, uselist=False, lazy=False, backref='clusters')
    sandbox_author = relation(UserPrincipal, uselist=False)

    #FIXME: Is it possible to have an append that checks the max_members?
    hosts = association_proxy('_hosts', 'host',
                              creator=lambda host: HostClusterMember(host=host))
    machines = association_proxy('_machines', 'machine',
                         creator=lambda mach: MachineClusterMember(machine=mach))

    service_bindings = association_proxy('_cluster_svc_binding',
                                         'service_instance')

    _metacluster = None
    metacluster = association_proxy('_metacluster', 'metacluster')

    __mapper_args__ = {'polymorphic_on': cluster_type}

    @property
    def required_services(self):
        return object_session(self).query(ClusterAlignedService).filter_by(
            cluster_type = self.cluster_type).all()

    @property
    def authored_branch(self):
        if self.sandbox_author:
            return "%s/%s" % (self.sandbox_author.name, self.branch.name)
        return str(self.branch.name)

    @property
    def personality_info(self):
        if self.cluster_type in self.personality.cluster_infos:
            return self.personality.cluster_infos[self.cluster_type]
        else:
            return None

    def validate(self, max_hosts=None, error=ArgumentError, **kwargs):
        if max_hosts is None:
            max_hosts = self.max_hosts
        if len(self.hosts) > self.max_hosts:
            raise error("{0} is over capacity of {1} hosts.".format(self,
                                                                    max_hosts))

cluster = Cluster.__table__
cluster.primary_key.name = 'cluster_pk'
cluster.append_constraint(UniqueConstraint('name', name='cluster_uk'))
cluster.info['unique_fields'] = ['name']


class EsxCluster(Cluster):
    """
        Specifically for our VMware esx based clusters.
    """
    __tablename__ = 'esx_cluster'
    __mapper_args__ = {'polymorphic_identity': 'esx'}
    _class_label = 'ESX Cluster'

    esx_cluster_id = Column(Integer, ForeignKey('%s.id'%(_TN),
                                            name='esx_cluster_fk',
                                            ondelete='CASCADE'),
                            #if the cluster record is deleted so is esx_cluster
                            primary_key=True)

    vm_count = Column(Integer, default=16, nullable=True)
    host_count = Column(Integer, default=1, nullable=False)
    down_hosts_threshold = Column(Integer, nullable=False)

    switch_id = Column(Integer,
                       ForeignKey('tor_switch.id',
                                  name='esx_cluster_switch_fk'),
                       nullable=True)

    switch = relation(TorSwitch, uselist=False, lazy=False,
                      backref=backref('esx_clusters'))

    @property
    def vm_to_host_ratio(self):
        return '%s:%s'% (self.vm_count, self.host_count)

    @property
    def max_vm_count(self):
        if self.host_count == 0:
            return 0
        effective_vmhost_count = len(self.hosts) - self.down_hosts_threshold
        if effective_vmhost_count < 0:
            return 0
        return effective_vmhost_count * self.vm_count / self.host_count

    @property
    def minimum_location(self):
        location = None
        for host in self.hosts:
            if location:
                location = location.merge(host.location)
            else:
                location = host.location
        return location

    @property
    def vmhost_capacity_function(self):
        """ Return the compiled VM host capacity function """
        info = self.personality_info
        if info:
            return info.compiled_vmhost_capacity_function
        else:
            return None

    @property
    def virtmachine_capacity_function(self):
        """ Return the compiled virtual machine capacity function """
        # Only identity mapping for now
        return None

    def get_total_capacity(self, down_hosts_threshold=None):
        """ Return the total capacity available for use by virtual machines """
        if down_hosts_threshold is None:
            down_hosts_threshold = self.down_hosts_threshold

        if len(self.hosts) <= down_hosts_threshold:
            return {'memory': 0}

        func = self.vmhost_capacity_function

        # No access for anything except built-in functions
        global_vars = {'__builtins__': restricted_builtins}

        resources = []
        for host in self.hosts:
            # This is the list of variables we want to pass to the capacity
            # function
            local_vars = {'memory': host.machine.memory}
            if func:
                resources.append(eval(func, global_vars, local_vars))
            else:
                resources.append(local_vars)
        # Convert the list of dicts to a dict of lists
        resmap = convert_resources(resources)

        # Drop the <down_hosts_threshold> largest elements from every list, and
        # sum the rest
        for name in resmap:
            reslist = sorted(resmap[name])
            if down_hosts_threshold > 0:
                reslist = reslist[:-down_hosts_threshold]
            resmap[name] = sum(reslist)
        return resmap

    def get_total_usage(self):
        """ Return the amount of resources used by the virtual machines """
        func = self.virtmachine_capacity_function

        # No access for anything except built-in functions
        global_vars = {'__builtins__': restricted_builtins}

        resmap = {}
        for machine in self.machines:
            # This is the list of variables we want to pass to the capacity
            # function
            local_vars = {'memory': machine.memory}
            if func:
                res = eval(func, global_vars, local_vars)
            else:
                res = local_vars
            for name, value in res.items():
                if name not in resmap:
                    resmap[name] = value
                else:
                    resmap[name] += value
        return resmap

    def validate(self, vm_part=None, host_part=None, current_vm_count=None,
                 current_host_count=None, down_hosts_threshold=None,
                 error=ArgumentError, **kwargs):
        super(EsxCluster, self).validate(error=error, **kwargs)

        if vm_part is None:
            vm_part = self.vm_count
        if host_part is None:
            host_part = self.host_count
        if current_vm_count is None:
            current_vm_count = len(self.machines)
        if current_host_count is None:
            current_host_count = len(self.hosts)
        if down_hosts_threshold is None:
            down_hosts_threshold = self.down_hosts_threshold

        # It doesn't matter how many vmhosts we have if there are no
        # virtual machines.
        if current_vm_count <= 0:
            return

        if host_part == 0:
            raise error("Invalid ratio of {0}:{1} for {2:l}.".format(
                        vm_part, host_part, self))

        # For calculations, assume that down_hosts_threshold vmhosts
        # are not available from the number currently configured.
        adjusted_host_count = current_host_count - down_hosts_threshold

        if adjusted_host_count <= 0:
            raise error("%s cannot support VMs with %s "
                        "vmhosts and a down_hosts_threshold of %s" %
                        (format(self), current_host_count,
                         down_hosts_threshold))

        # The current ratio must be less than the requirement...
        # cur_vm / cur_host <= vm_part / host_part
        # cur_vm * host_part <= vm_part * cur_host
        # Apply a logical not to test for the error condition...
        if current_vm_count * host_part > vm_part * adjusted_host_count:
            raise error("%s VMs:%s hosts in %s violates "
                        "ratio %s:%s with down_hosts_threshold %s" %
                        (current_vm_count, current_host_count, format(self),
                         vm_part, host_part, down_hosts_threshold))

        capacity = self.get_total_capacity()
        usage = self.get_total_usage()
        for name, value in usage.items():
            # Skip resources that are not restricted
            if name not in capacity:
                continue
            if value > capacity[name]:
                raise error("{0} is over capacity regarding {1}: wanted {2}, "
                            "but the limit is {3}.".format(self, name, value,
                                                           capacity[name]))
        return

    def __init__(self, **kw):
        if 'max_hosts' not in kw:
            kw['max_hosts'] = 8
        super(EsxCluster, self).__init__(**kw)

esx_cluster = EsxCluster.__table__
esx_cluster.primary_key.name = 'esx_cluster_pk'
esx_cluster.info['unique_fields'] = ['name']


_HCM = 'host_cluster_member'
class HostClusterMember(Base):
    """ Specific Class for EsxCluster vmhosts """
    __tablename__ = _HCM

    cluster_id = Column(Integer, ForeignKey('%s.id'% (_TN),
                                                name='hst_clstr_mmbr_clstr_fk',
                                                ondelete='CASCADE'),
                        #if the cluster is deleted, so is membership
                        primary_key=True)

    host_id = Column(Integer, ForeignKey('host.id',
                                         name='hst_clstr_mmbr_hst_fk',
                                         ondelete='CASCADE'),
                        #if the host is deleted, so is the membership
                        primary_key=True)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)

    """
        Association Proxy and relation cascading:
        We need cascade=all on backrefs so that deletion propagates to avoid
        AssertionError: Dependency rule tried to blank-out primary key column on
        deletion of the Cluster and it's links. On the contrary do not have
        cascade='all' on the forward mapper here, else deletion of clusters
        and their links also causes deleteion of hosts (BAD)
    """
    cluster = relation(Cluster, uselist=False, lazy=False,
                       backref=backref('_hosts', cascade='all'))

    host = relation(Host, lazy=False,
                    backref=backref('_cluster', uselist=False, cascade='all'))

    def __init__(self, **kw):
        if kw.has_key('cluster'):
            """
                when we append to the association proxy, there's no metacluster
                argument which prevents this from being checked.
            """
            cl = kw['cluster']
            if len(cl.hosts) >= cl.max_hosts:
                msg = '%s already at maximum capacity (%s)'% (cl.name,
                                                          cl.max_hosts)
                raise ValueError(msg)

        #TODO: enforce cluster members are inside the location constraint?
        super(HostClusterMember, self).__init__(**kw)

hcm = HostClusterMember.__table__
hcm.primary_key.name = '%s_pk'% (_HCM)
hcm.append_constraint(
    UniqueConstraint('host_id', name='host_cluster_member_host_uk'))
hcm.info['unique_fields'] = ['cluster', 'host']

Host.cluster = association_proxy('_cluster', 'cluster')

_MCM = 'machine_cluster_member'
class MachineClusterMember(Base):
    """ Binds machines into clusters """
    __tablename__ = _MCM

    cluster_id = Column(Integer, ForeignKey('%s.id'% (_TN),
                                                name='mchn_clstr_mmbr_clstr_fk',
                                                ondelete='CASCADE'),
                            primary_key=True)

    machine_id = Column(Integer, ForeignKey('machine.machine_id',
                                            name='mchn_clstr_mmbr_mchn_fk',
                                            ondelete='CASCADE'),
                        primary_key=True)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)

    """ See comments for HostClusterMembers relations """
    cluster = relation(Cluster, uselist=False, lazy=False,
                       backref=backref('_machines', cascade='all'))

    machine = relation(Machine, lazy=False,
                  backref=backref('_cluster', uselist=False, cascade='all'))

    #TODO: __init__ that checks the sanity of adding new machines to clusters?

mcm = MachineClusterMember.__table__
mcm.primary_key.name = '%s_pk'% (_MCM)
mcm.append_constraint(UniqueConstraint('machine_id',
                                       name='machine_cluster_member_uk'))
mcm.info['unique_fields'] = ['cluster', 'machine']

Machine.cluster = association_proxy('_cluster', 'cluster')

_CRS = 'cluster_aligned_service'
_ABV = 'clstr_alnd_svc'
class ClusterAlignedService(Base):
    """
        Express services that must be the same for cluster types. As SQL Alchemy
        doesn't yet support FK or functionally determined discrimators for
        polymorphic inheritance, cluster_type is currently being expressed as a
        string. As ESX is the only type for now, it's seems a reasonable corner
        to cut.
    """
    __tablename__ = _CRS
    _class_label = 'Cluster Aligned Service'

    service_id = Column(Integer, ForeignKey('service.id',
                                            name='%s_svc_fk'%(_ABV),
                                            ondelete='CASCADE'),
                        #if the service is deleted, delete the link?
                        primary_key=True)

    cluster_type = Column(AqStr(16), primary_key=True)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)
    comments = Column(String(255))

    service = relation(Service, uselist=False, lazy=False,
                       backref=backref('_clusters', cascade='all'))
    #cascade deleted services to delete their being required to cluster_types

cas = ClusterAlignedService.__table__
cas.primary_key.name = '%s_pk'% (_ABV)
cas.info['unique_fields'] = ['cluster_type', 'service']

_CSB = 'cluster_service_binding'
_CAB = 'clstr_svc_bndg'
class ClusterServiceBinding(Base):
    """
        Makes bindings of service instances to clusters
    """
    __tablename__ = _CSB
    _class_label = 'Cluster Service Binding'

    cluster_id = Column(Integer, ForeignKey('%s.id'%(_TN),
                                            name='%s_cluster_fk'%(_CAB),
                                            ondelete='CASCADE'),
                        primary_key=True)

    service_instance_id = Column(Integer,
                                 ForeignKey('service_instance.id',
                                            name='%s_srv_inst_fk'%(_CAB)),
                                 primary_key=True)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)
    comments = Column(String(255))

    cluster = relation(Cluster, uselist=False, lazy=False,
                       backref=backref('_cluster_svc_binding',
                                       cascade='all'))

    """
        backref name != forward reference name intentional as it seems more
        readable for the following reason:
        If you instantiate a ClusterServiceBinding, you do it with
                ClusterServiceBinding(cluster=foo, service_instance=bar)
        But if you append to the association_proxy
                cluster.service_bindings.append(svc_inst)
    """
    service_instance = relation(ServiceInstance, lazy=False,
                                backref='service_instances')

    """
        cfg_path will die soon. using service instance here to
        ease later transition.
    """
    @property
    def cfg_path(self):
        return self.service_instance.cfg_path

csb = ClusterServiceBinding.__table__
csb.primary_key.name = '%s_pk'% (_CSB)
csb.info['unique_fields'] = ['cluster', 'service_instance']
