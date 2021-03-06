#!/usr/bin/env python2.6
# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2012,2013  Contributor
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

import sys
import os
# bin/twistd.py, we'll start it after the patch is done
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "..", "..", "..", "bin"))
# lib/python2.6/config.py
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "..", "..", "..", "lib", "python2.6"))

from aquilon.config import Config
from socket import gaierror
import socket
import re

# dwim options parser
for i in range(0, len(sys.argv)):
    if sys.argv[i] == "--config":
        configpath = sys.argv[i + 1]
        break

config = Config(configfile=configpath)


# do the patches


def fake_gethostbyname(hostname):
    try:
        host_ip = None

        # for templates/index.py
        if hostname == config.get("broker", "bind_address"):
            host_ip = gethostbyname_orig(hostname)
        else:
            # faking hostip
            fake_hosts = config.get('unittest', 'fake_hosts_location')
            hostfilename = fake_hosts + hostname

            # strip domain part
            if not os.path.exists(hostfilename) and hostname.find(".") > -1:
                hostfilename = fake_hosts + hostname[:hostname.find(".")]

            hostfile = open(hostfilename).readlines()
            primary_name = hostfile[0].split()[2]
            ip_re = re.compile(r'^\s*([a-z0-9]+)\s+[a-z0-9]+\s+([0-9\.]+)')
            for line in hostfile:
                m = ip_re.search(line)
                if m and primary_name == m.group(1):
                    host_ip = m.group(2)
                    break

        if host_ip == None:
            raise gaierror(-2, "Name or service not known")

        return host_ip

    except IOError, e:
        # To have the cause in aqd.log
        raise gaierror(-2, "Name or service not known %s" % e)

gethostbyname_orig = socket.gethostbyname
socket.gethostbyname = fake_gethostbyname

# worker/resources.py depends on it.
sys.argv[0] = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "..", "..", "..", "bin", "twistd.py")

# start the broker
import twistd
