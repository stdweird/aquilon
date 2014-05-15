# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2008,2009,2010,2011,2013,2014  Contributor
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
"""Contains the logic for `aq show user --user`."""


from aquilon.exceptions_ import NotFoundException
from aquilon.aqdb.model import User
from aquilon.worker.broker import BrokerCommand  # pylint: disable=W0611


class CommandShowUser(BrokerCommand):

    required_parameters = ["username"]

    def render(self, session, username, **arguments):
        q = session.query(User)
        q = q.filter_by(name=username)
        result = q.all()
        if not result:
            raise NotFoundException("User %s not found." % username)
        return result
