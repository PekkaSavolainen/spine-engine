######################################################################################################################
# Copyright (C) 2017-2022 Spine project consortium
# This file is part of Spine Engine.
# Spine Engine is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser
# General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################
"""This module contains wrappers for Engine-side connections."""
from spinedb_api.filters.scenario_filter import SCENARIO_FILTER_TYPE
from .connection import Connection, Jump


class EngineConnection(Connection):
    """Engine-side connection."""

    def ready_to_execute(self):
        """See base class."""
        for filter_type in (SCENARIO_FILTER_TYPE,):
            if self.require_filter_online(filter_type) and not self._filter_settings.has_filter_online(filter_type):
                return False
        return True


class EngineJump:
    """Engine-side jump."""
