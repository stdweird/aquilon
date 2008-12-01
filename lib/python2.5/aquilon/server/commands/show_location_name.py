# ex: set expandtab softtabstop=4 shiftwidth=4: -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# Copyright (C) 2008 Morgan Stanley
#
# This module is part of Aquilon
"""Contains the logic for `aq show location --type --name`."""


from aquilon.server.broker import (add_transaction, az_check, format_results,
                                   BrokerCommand)
from aquilon.server.commands.show_location_type import CommandShowLocationType


class CommandShowLocationName(CommandShowLocationType):
    """The superclass can already handle this case."""

    required_parameters = ["type", "name"]


