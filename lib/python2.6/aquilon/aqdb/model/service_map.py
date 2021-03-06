# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2012,2013  Contributor
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Maps service instances to locations. See class.__doc__ """

from datetime import datetime

from sqlalchemy import (Column, Integer, Sequence, String, DateTime, ForeignKey,
                        UniqueConstraint, Index)
from sqlalchemy.orm import relation, deferred, backref

from aquilon.aqdb.model import Base, Location, ServiceInstance, Network

_TN = 'service_map'
_ABV = 'svc_map'


class ServiceMap(Base):
    """ Service Map: mapping a service_instance to a location.
        The rows in this table assert that an instance is a valid useable
        default that clients can choose as their provider during service
        autoconfiguration. """

    __tablename__ = _TN

    id = Column(Integer, Sequence('service_map_id_seq'), primary_key=True)

    service_instance_id = Column(Integer,
                                 ForeignKey('service_instance.id',
                                            name='%s_svc_inst_fk' % _ABV,
                                            ondelete='CASCADE'),
                                 nullable=False)

    location_id = Column(Integer, ForeignKey('location.id',
                                             ondelete='CASCADE',
                                             name='%s_loc_fk' % _ABV),
                         nullable=True)

    network_id = Column(Integer, ForeignKey('network.id', ondelete='CASCADE',
                                             name='%s_net_fk' % _ABV),
                         nullable=True)

    creation_date = deferred(Column(DateTime, default=datetime.now,
                                    nullable=False))
    comments = deferred(Column(String(255), nullable=True))

    location = relation(Location)
    service_instance = relation(ServiceInstance, innerjoin=True,
                                backref=backref('service_map',
                                                cascade="all, delete-orphan"))
    network = relation(Network)

    __table_args__ = (UniqueConstraint(service_instance_id, location_id,
                                       network_id,
                                       name='%s_loc_net_inst_uk' % _ABV),
                      Index("%s_location_idx" % _ABV, location_id),
                      Index("%s_network_idx" % _ABV, network_id))

    @property
    def service(self):
        return self.service_instance.service

    @property
    def mapped_to(self):
        if self.location:
            mapped_to = self.location
        else:
            mapped_to = self.network

        return mapped_to

    def __init__(self, network=None, location=None, **kwargs):
        super(ServiceMap, self).__init__(network=network, location=location,
                                         **kwargs)
        if network and location:  # pragma: no cover
            raise ValueError("A service can't be mapped to a Network and a "
                             "Location at the same time")

        if network is None and location is None:  # pragma: no cover
            raise ValueError("A service should by mapped to a Network or a "
                             "Location")
