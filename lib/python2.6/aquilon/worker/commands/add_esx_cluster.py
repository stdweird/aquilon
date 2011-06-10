# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
#
# Copyright (C) 2009,2010,2011  Contributor
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


from aquilon.worker.broker import BrokerCommand, validate_basic
from aquilon.aqdb.model import (Cluster, EsxCluster, MetaCluster,
                                ClusterLifecycle, Switch,
                                MetaClusterMember, Personality)
from aquilon.exceptions_ import ArgumentError
from aquilon.worker.dbwrappers.branch import get_branch_and_author
from aquilon.worker.dbwrappers.location import get_location
from aquilon.worker.templates.cluster import PlenaryCluster
from aquilon.utils import force_ratio


class CommandAddESXCluster(BrokerCommand):

    required_parameters = ["cluster", "metacluster", "down_hosts_threshold"]

    def render(self, session, logger, cluster, metacluster, archetype,
               personality, max_members, vm_to_host_ratio, domain, sandbox,
               tor_switch, switch, down_hosts_threshold, buildstatus, comments,
               **arguments):
        validate_basic("cluster", cluster)

        if not buildstatus:
            buildstatus = "build"
        dbstatus = ClusterLifecycle.get_unique(session, buildstatus,
                                               compel=True)

        (dbbranch, dbauthor) = get_branch_and_author(session, logger,
                                                     domain=domain,
                                                     sandbox=sandbox,
                                                     compel=True)

        dblocation = get_location(session, **arguments)
        if not dblocation:
            raise ArgumentError("Adding a cluster requires a location "
                                "constraint.")
        if not dblocation.campus:
            raise ArgumentError("{0} is not within a campus.".format(dblocation))

        Cluster.get_unique(session, cluster, preclude=True)

        dbmetacluster = MetaCluster.get_unique(session, metacluster,
                                               compel=True)
        dbpersonality = Personality.get_unique(session, name=personality,
                                               archetype=archetype, compel=True)

        if max_members is None:
            max_members = self.config.getint("broker",
                                             "esx_cluster_max_members_default")

        if vm_to_host_ratio is None:
            vm_to_host_ratio = self.config.get("broker",
                                               "esx_cluster_vm_to_host_ratio")
        (vm_count, host_count) = force_ratio("vm_to_host_ratio",
                                             vm_to_host_ratio)

        if tor_switch:
            self.deprecated_option("tor_switch", "Please use --switch instead.",
                                   logger=logger, **arguments)
            switch = tor_switch
        if switch:
            dbswitch = Switch.get_unique(session, switch, compel=True)
        else:
            dbswitch = None

        dbcluster = EsxCluster(name=cluster,
                               location_constraint=dblocation,
                               personality=dbpersonality,
                               max_hosts=max_members,
                               vm_count=vm_count, host_count=host_count,
                               branch=dbbranch, sandbox_author=dbauthor,
                               switch=dbswitch,
                               down_hosts_threshold=down_hosts_threshold,
                               status=dbstatus,
                               comments=comments)
        session.add(dbcluster)
        dbmetacluster.members.append(dbcluster)

        session.flush()

        plenary = PlenaryCluster(dbcluster, logger=logger)
        plenary.write()

        return