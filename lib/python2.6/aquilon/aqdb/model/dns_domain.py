# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2009  Contributor
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
""" DNS Domains, as simple names """

from datetime import datetime

from sqlalchemy import (Column, Integer, DateTime, Sequence, String,
                        UniqueConstraint)

from aquilon.aqdb.model import Base
from aquilon.utils import monkeypatch
from aquilon.aqdb.column_types.aqstr import AqStr

_domains = ['ms.com', 'one-nyp.ms.com', 'devin1.ms.com', 'the-ha.ms.com',
            'devin2.ms.com', 'msad.ms.com']

_TN = 'dns_domain'


class DnsDomain(Base):
    """ Dns Domain (simple names that compose bigger records) """

    __tablename__ = _TN
    _class_label = 'DNS Domain'

    id = Column(Integer, Sequence('%s_id_seq' % (_TN)), primary_key=True)
    name = Column(AqStr(32), nullable=False)

    creation_date = Column(DateTime, default=datetime.now, nullable=False)
    comments = Column(String(255), nullable=True)

    def __str__(self):
        return str(self.name)


table = DnsDomain.__table__

table.primary_key.name = '%s_pk' % (_TN)
table.append_constraint(UniqueConstraint('name', name='%s_uk' % (_TN)))

@monkeypatch(table)
def populate(sess, **kw):
    """ populate some well known domains """

    if len(sess.query(DnsDomain).all()) < 1:

        for domain in _domains:
            dmn = DnsDomain(name=domain)
            sess.add(dmn)

        try:
            sess.commit()
        except Exception, e:
            sess.rollback()
            raise e