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
"""This module contains stuff for named objects."""


class NamedObject:
    """A thing that has a name and description."""

    def __init__(self, name, description):
        """
        Args:
            name (str): name of object
            description (str): description of object
        """
        self._name = name
        self._description = description

    @property
    def name(self):
        """Object's name."""
        return self._name

    @property
    def description(self):
        """Object's description."""
        return self._description
