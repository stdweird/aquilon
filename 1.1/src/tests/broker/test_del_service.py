#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# $Header$
# $Change$
# $DateTime$
# $Author$
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Module for testing the del service command."""

import os
import sys
import unittest

if __name__ == "__main__":
    BINDIR = os.path.dirname(os.path.realpath(sys.argv[0]))
    SRCDIR = os.path.join(BINDIR, "..", "..")
    sys.path.append(os.path.join(SRCDIR, "lib", "python2.5"))

from brokertest import TestBrokerCommand


class TestDelService(TestBrokerCommand):

    def testdelafsinstance(self):
        command = "del service --service afs --instance q.ny.ms.com"
        self.noouttest(command.split(" "))

    def testverifydelafsinstance(self):
        command = "show service --service afs"
        out = self.commandtest(command.split(" "))
        # Note: For now, the .ms.com is not present in this output...
        self.assert_(out.find("Service: afs Instance: q.ny") < 0)

    def testdelbootserverinstance(self):
        command = "del service --service bootserver --instance np.test"
        self.noouttest(command.split(" "))

    def testverifydelbootserverinstance(self):
        command = "show service --service bootserver"
        out = self.commandtest(command.split(" "))
        self.assert_(out.find("Service: bootserver Instance: np.test") < 0)

    def testdeldnsinstance(self):
        command = "del service --service dns --instance nyinfratest"
        self.noouttest(command.split(" "))

    def testverifydeldnsinstance(self):
        command = "show service --service dns"
        out = self.commandtest(command.split(" "))
        self.assert_(out.find("Service: dns Instance: nyinfratest") < 0)

    def testdelntpinstance(self):
        command = "del service --service ntp --instance pa.ny.na"
        self.noouttest(command.split(" "))

    def testverifydelntpinstance(self):
        command = "show service --service ntp"
        out = self.commandtest(command.split(" "))
        self.assert_(out.find("Service: ntp Instance: pa.ny.na") < 0)


if __name__=='__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDelService)
    unittest.TextTestRunner(verbosity=2).run(suite)
