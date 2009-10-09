#!/usr/bin/env python2.5
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
"""Module for testing constraints involving the bind client command."""

import os
import sys
import unittest

if __name__ == "__main__":
    BINDIR = os.path.dirname(os.path.realpath(sys.argv[0]))
    SRCDIR = os.path.join(BINDIR, "..", "..")
    sys.path.append(os.path.join(SRCDIR, "lib", "python2.5"))

from brokertest import TestBrokerCommand


class TestBindClientConstraints(TestBrokerCommand):

    def testrebindfails(self):
        command = ["bind", "client",
                   "--hostname", "unittest02.one-nyp.ms.com",
                   "--service", "utsvc", "--instance", "utsi1"]
        out = self.badrequesttest(command)
        self.matchoutput(out, "is already bound", command)

    def testfailbindclusteralignedservice(self):
        # Figure out which service the cluster is bound to and attempt change.
        command = ["show_esx_cluster", "--cluster=utecl1"]
        out = self.commandtest(command)
        m = self.searchoutput(out,
                              r'Member Alignment: Service esx_management '
                              r'Instance (\S+)',
                              command)
        instance = m.group(1)
        # Grab a host from the cluster
        command = ["search_host", "--cluster=utecl1"]
        out = self.commandtest(command)
        m = self.searchoutput(out, r'(\S+)', command)
        host = m.group(1)
        # Sanity check that the host is currently aligned.
        command = ["search_host", "--host=%s" % host,
                   "--service=esx_management", "--instance=%s" % instance]
        out = self.commandtest(command)
        self.matchoutput(out, host, command)
        # Now try to swap.
        next = instance == 'ut.a' and 'ut.b' or 'ut.a'
        command = ["bind_client", "--hostname=%s" % host,
                   "--service=esx_management", "--instance=%s" % next]
        out = self.badrequesttest(command)
        self.matchoutput(out,
                         "The esx cluster utecl1 is set to use "
                         "service esx_management instance %s" % instance,
                         command)


if __name__=='__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(
        TestBindClientConstraints)
    unittest.TextTestRunner(verbosity=2).run(suite)