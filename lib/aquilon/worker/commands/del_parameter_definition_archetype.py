# -*- cpy-indent-level: 4; indent-tabs-mode: nil -*-
# ex: set expandtab softtabstop=4 shiftwidth=4:
#
# Copyright (C) 2009,2010,2011,2012,2013,2014,2015  Contributor
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

from sqlalchemy.orm import contains_eager

from aquilon.exceptions_ import ArgumentError
from aquilon.aqdb.model import (ParamDefinition, Archetype, PersonalityStage,
                                Personality)
from aquilon.worker.broker import BrokerCommand
from aquilon.worker.dbwrappers.parameter import search_path_in_personas
from aquilon.worker.templates import PlenaryCollection
from aquilon.worker.templates.personality import (ParameterTemplate,
                                                  PlenaryPersonalityParameter)


class CommandDelParameterDefintionArchetype(BrokerCommand):

    required_parameters = ["path", "archetype"]

    def render(self, session, logger, archetype, path, **kwargs):
        dbarchetype = Archetype.get_unique(session, archetype, compel=True)
        path = ParamDefinition.normalize_path(path)

        for holder in dbarchetype.param_def_holders.values():
            db_paramdef = ParamDefinition.get_unique(session, path=path,
                                                     holder=holder)
            if db_paramdef:
                break
        else:
            raise ArgumentError("Parameter definition %s not found." % path)

        # validate if this path is being used
        holder = search_path_in_personas(session, path, db_paramdef.holder)
        if holder:
            raise ArgumentError("Parameter with path {0} used by following and cannot be deleted : ".format(path) +
                                ", ".join("{0.holder_object:l}".format(h) for h in holder))

        plenaries = PlenaryCollection(logger=logger)

        param_def_holder = db_paramdef.holder
        param_def_holder.param_definitions.remove(db_paramdef)
        if not param_def_holder.param_definitions:
            # This was the last definition for the given template - need to
            # clean up
            q = session.query(PersonalityStage)
            q = q.join(Personality)
            q = q.options(contains_eager('personality'))
            q = q.filter_by(archetype=dbarchetype)
            for dbstage in q:
                ptmpl = ParameterTemplate(dbstage, param_def_holder)
                plenaries.append(PlenaryPersonalityParameter.get_plenary(ptmpl))

            dbarchetype.param_def_holders.remove(param_def_holder)

        session.flush()

        plenaries.write()

        return
