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
"""This module contains methods to wrap a Spine Toolbox project for Spine Engine."""
from .project_item_wrapper import EngineProjectItem


class EngineProject:
    def __init__(self, project, engine_item_classes):
        """
        Args:
            project (Project): project to wrap
            engine_item_classes (dict): mapping from project item type to engine item class
        """
        if project.is_memory_only:
            raise ValueError("Cannot wrap virtual project.")
        self._items = [engine_item_classes()]
