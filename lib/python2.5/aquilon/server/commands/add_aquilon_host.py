# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Contains a wrapper for `aq add aquilon host`."""


from aquilon.server.broker import BrokerCommand
from aquilon.server.commands.add_host import CommandAddHost


class CommandAddAquilonHost(CommandAddHost):

    required_parameters = ["hostname", "machine", "domain"]

    def render(self, *args, **kwargs):
        # The superclass already contains the logic to handle this case.
        kwargs['archetype'] = 'aquilon'
        return CommandAddHost.render(self, *args, **kwargs)
