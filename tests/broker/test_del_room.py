#!/usr/bin/env python
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
"""Module for testing the del room command."""

if __name__ == "__main__":
    import utils
    utils.import_depends()

import unittest2 as unittest
from brokertest import TestBrokerCommand


class TestDelRoom(TestBrokerCommand):

    def testdelutroom1(self):
        command = "del room --room utroom1"
        self.noouttest(command.split(" "))

    def testverifydelutroom1(self):
        command = "show room --room utroom1"
        out = self.notfoundtest(command.split(" "))
        self.matchoutput(out, "Room utroom1 not found.", command)

    def testdelroomnotexist(self):
        command = "del room --room room-does-not-exist"
        out = self.notfoundtest(command.split(" "))
        self.matchoutput(out, "Room room-does-not-exist not found.", command)

    def testdelroomnetwork(self):
        test_room = "utroom1"

        self.net.allocate_network(self, "utroom1_net", 24, "unknown",
                                  "room", test_room,
                                  comments="Made-up network")

        # try delete room
        command = "del room --room %s" % test_room
        err = self.badrequesttest(command.split(" "))
        self.matchoutput(err,
                         "Bad Request: Could not delete room %s, networks "
                         "were found using this location." % test_room,
                         command)

        self.net.dispose_network(self, "utroom1_net")


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDelRoom)
    unittest.TextTestRunner(verbosity=2).run(suite)
