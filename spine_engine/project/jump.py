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
"""This module contains jump related stuff."""
from spine_engine.project_item.project_item_resource import make_cmd_line_arg


class Jump:
    """Represents a conditional jump between two project items.

    Attributes:
        source (str): name of source node
        destination (str): name of destination node
        condition (dict or NoneType): condition settings
    """

    def __init__(self, source, destination, condition=None, cmd_line_args=()):
        """
        Args:
            source (str): source project item's name
            destination (str): destination project item's name
            condition (dict, optional): jump condition
            cmd_line_args (Iterable of CmdLineArg): command line arguments
        """
        self.source = source
        self.destination = destination
        self.condition = condition if condition is not None else {"type": "python-script", "script": "exit(1)"}
        self._cmd_line_args = list(cmd_line_args)

    def set_cmd_line_args(self, cmd_line_args):
        """Sets new command line arguments.

        Args:
            cmd_line_args (list of CmdLineArg): command line arguments
        """
        self._cmd_line_args = cmd_line_args

    def to_dict(self):
        """Serializes jump into dictionary.

        Returns:
            dict: serialized jump
        """
        return {
            "from": self.source,
            "to": self.destination,
            "condition": self.condition,
            "cmd_line_args": [arg.to_dict() for arg in self._cmd_line_args],
        }

    @staticmethod
    def from_dict(jump_dict):
        """Deserializes jump from dict.

        Args:
            jump_dict (dict): serialized jump

        Returns:
            Jump: deserialized jump
        """
        source = jump_dict["from"]
        destination = jump_dict["to"]
        condition = jump_dict["condition"]
        cmd_line_args = [make_cmd_line_arg(arg) for arg in jump_dict.get("cmd_line_args", [])]
        return Jump(source, destination, condition, cmd_line_args)
