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
"""
    A metacluster is a grouping of two or more clusters grouped together for
    wide-area failover scenarios (So far only for vmware based clusters)
"""

from datetime import datetime

from sqlalchemy import (Column, Integer, String, DateTime, Sequence,
                        ForeignKey, UniqueConstraint, Boolean)

from sqlalchemy.orm import relation, backref
from sqlalchemy.orm.attributes import instance_state
from sqlalchemy.orm.interfaces import MapperExtension
from sqlalchemy.orm.session import object_session
from sqlalchemy.ext.associationproxy import association_proxy

from aquilon.exceptions_ import ArgumentError
from aquilon.aqdb.model import Base, Cluster, ServiceInstance
from aquilon.aqdb.model.cluster import convert_resources
from aquilon.aqdb.column_types.aqstr import AqStr

_MCT = 'metacluster'
_MCM = 'metacluster_member'


class MetaCluster(Base):
    """
        A metacluster is a grouping of two or more clusters grouped together for
        wide-area failover scenarios (So far only for vmware based clusters).
        Network is nullable for metaclusters that do not utilize IP failover.
    """

    __tablename__ = _MCT
    _class_label = "Metacluster"

    id = Column(Integer, Sequence('%s_seq' % _MCT), primary_key=True)

    name = Column(AqStr(64), nullable=False)

    max_clusters = Column(Integer, default=2, nullable=False)

    max_shares = Column(Integer, nullable=False)

    high_availability = Column(Boolean(name="%s_ha_ck" % _MCT), default=False,
                               nullable=False)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)

    comments = Column(String(255))

    members = association_proxy('_clusters', 'cluster',
                                creator=lambda x: MetaClusterMember(cluster=x))

    @property
    def shares(self):
        q = object_session(self).query(ServiceInstance)
        q = q.join('nas_disks', 'machine', '_cluster', 'cluster',
                   '_metacluster')
        q = q.filter_by(metacluster=self)
        return q.all()

    def get_total_capacity(self):
        # Key: building; value: list of cluster capacities inside that building
        building_capacity = {}
        for cluster in self.members:
            building = cluster.location_constraint.building
            if building not in building_capacity:
                building_capacity[building] = {}
            cap = cluster.get_total_capacity()
            for name, value in cap.items():
                if name in building_capacity[building]:
                    building_capacity[building][name] += value
                else:
                    building_capacity[building][name] = value

        # Convert the per-building dict of resources to per-resource list of
        # building-provided values
        resmap = convert_resources(building_capacity.values())

        # high_availability is down_buildings_threshold == 1. So if high
        # availability is enabled, drop the largest value from every resource
        # list
        for name in resmap:
            reslist = sorted(resmap[name])
            if self.high_availability:
                reslist = reslist[:-1]
            resmap[name] = sum(reslist)

        return resmap

    def get_total_usage(self):
        usage = {}
        for cluster in self.members:
            for name, value in cluster.get_total_usage().items():
                if name in usage:
                    usage[name] += value
                else:
                    usage[name] = value
        return usage

    def validate(self, error=ArgumentError):
        """ Validate metacluster constraints """
        if len(self.members) > self.max_clusters:
            raise error("{0} already has the maximum number of clusters "
                        "({1}).".format(self, self.max_clusters))
        if len(self.shares) > self.max_shares:
            raise error("{0} already has the maximum number of shares "
                        "({1}).".format(self, self.max_shares))

        # Small optimization: avoid enumerating all the clusters/VMs if high
        # availability is not enabled
        if self.high_availability:
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

metacluster = MetaCluster.__table__  # pylint: disable-msg=C0103, E1101
metacluster.primary_key.name = '%s_pk' % _MCT
metacluster.append_constraint(UniqueConstraint('name', name='%s_uk' % _MCT))
metacluster.info['unique_fields'] = ['name']


class ValidateMetaCluster(MapperExtension):
    """ Helper class to perform validation on metacluster membership changes """

    def after_insert(self, mapper, connection, instance):
        """ Validate the metacluster after a new member has been added """
        instance.metacluster.validate()

    def after_delete(self, mapper, connection, instance):
        """ Validate the metacluster after a member has been deleted """
        # This is a little tricky. If the instance got deleted through an
        # association proxy, then instance.cluster will be None (although
        # instance.cluster_id still has the right value).
        if instance.metacluster:
            metacluster = instance.metacluster
        else:
            state = instance_state(instance)
            metacluster = state.committed_state['metacluster']
        metacluster.validate()


class MetaClusterMember(Base):
    """ Binds clusters to metaclusters """
    __tablename__ = _MCM

    metacluster_id = Column(Integer, ForeignKey('metacluster.id',
                                                name='%s_meta_fk' % _MCM,
                                                ondelete='CASCADE'),
                            #if a metacluser is delete so is the association
                            primary_key=True)

    cluster_id = Column(Integer, ForeignKey('clstr.id',
                                            name='%s_clstr_fk' % _MCM,
                                            ondelete='CASCADE'),
                        #if a cluster is deleted, so is the association
                        primary_key=True)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)

    """
        Association Proxy and relation cascading:
        We need cascade=all on backrefs so that deletion propagates to avoid
        AssertionError: Dependency rule tried to blank-out primary key column on
        deletion of the Metacluster and it's links. On the contrary do not have
        cascade='all' on the forward mapper here, else deletion of metaclusters
        and their links also causes deleteion of clusters (BAD)
    """

    metacluster = relation(MetaCluster, lazy='subquery', uselist=False,
                            backref=backref('_clusters',
                                            cascade='all, delete-orphan'))

    cluster = relation(Cluster, lazy='subquery',
                       backref=backref('_metacluster', uselist=False,
                                       cascade='all, delete-orphan'))

    __mapper_args__ = {'extension': ValidateMetaCluster()}

metamember = MetaClusterMember.__table__  # pylint: disable-msg=C0103, E1101
metamember.primary_key.name = '%s_pk' % _MCM
metamember.append_constraint(
    UniqueConstraint('cluster_id', name='%s_uk' % _MCM))
metamember.info['unique_fields'] = ['metacluster', 'cluster']
