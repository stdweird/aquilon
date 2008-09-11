#!/ms/dist/python/PROJ/core/2.5.0/bin/python
# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Module for testing the del auxiliary command."""

import os
import sys
import unittest

if __name__ == "__main__":
    BINDIR = os.path.dirname(os.path.realpath(sys.argv[0]))
    SRCDIR = os.path.join(BINDIR, "..", "..")
    sys.path.append(os.path.join(SRCDIR, "lib", "python2.5"))

from brokertest import TestBrokerCommand


class TestDelAuxiliary(TestBrokerCommand):

    def testdelunittest00e1(self):
        command = "del auxiliary --auxiliary unittest00-e1.one-nyp.ms.com"
        self.noouttest(command.split(" "))

    def testverifydelunittest00e1(self):
        command = "show auxiliary --auxiliary unittest00-e1.one-nyp.ms.com"
        self.notfoundtest(command.split(" "))


if __name__=='__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDelAuxiliary)
    unittest.TextTestRunner(verbosity=2).run(suite)

