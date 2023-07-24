######################################################################################################################
# Copyright (C) 2017-2022 Spine project consortium
# This file is part of Spine Engine.
# Spine Engine is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################
"""
Contains Engine's exceptions.

"""


class EngineInitFailed(Exception):
    """Raised when :class:`SpineEngine` initialization fails."""


class RemoteEngineInitFailed(Exception):
    """Raised when initializing the remote server connection fails."""


class InstanceIsMemoryOnly(Exception):
    """Raised when project or project component is memory-only."""


class UnrecognizedNodeType(Exception):
    """Raised when node dict contains an unrecognized node type."""


class ProjectComponentNotFound(Exception):
    """Raised when node, edge, jump or specification is not found."""


class NameContainsInvalidCharacters(Exception):
    """Raised when a name contains invalid characters."""


class DuplicateName(Exception):
    """Raised when a duplicate name exists."""


class DuplicateShortName(Exception):
    """Raised when a duplicate short name exists."""


class ProjectVersionTooHigh(Exception):
    """Raised when project version is higher than the currently supported one."""


class ProjectUpgradeFailed(Exception):
    """Raised when project upgrade failed."""


class ItemsVersionTooHigh(Exception):
    """Raised when items version is higher than the currently installed items package."""


class InvalidConnection(Exception):
    """Raised when adding a connection would result in broken DAG."""


class InvalidJump(Exception):
    """Raised when jump is not valid."""
