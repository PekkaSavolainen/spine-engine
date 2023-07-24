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
"""This module contains project item specification related stuff."""
import json
from pathlib import Path
from spine_engine.utils.helpers import dump_json_beautifully, gather_leaf_data, shorten
from .named_object import NamedObject
from ..exception import InstanceIsMemoryOnly


class ProjectItemSpecification(NamedObject):
    """Specification for project items that use them."""

    def __init__(self, name, description):
        """
        Args:
            name (str): name of specification
            description (str): description of specification
        """
        super().__init__(name, description)
        self._file_path = None
        self._plugin = None

    @property
    def is_part_of_plugin(self) -> bool:
        return self._plugin is not None

    def get_plugin_name(self):
        """Returns the name of the plugin the specification is part of.

        Returns:
            str: name of plugin or None if specification is not part of any.
        """
        return self._plugin

    def set_plugin_name(self, name):
        """Connects specification to a plugin.

        Args:
            name (str): name of plugin
        """
        self._plugin = name

    @property
    def is_memory_only(self) -> bool:
        return self._file_path is None

    def tie_to_disk(self, specifications_dir):
        """Connecting specification with a file on disk.

        Does not do anything if specification has been connected already.

        Args:
            specifications_dir (Path or str): path to specification directory
        """
        if not self.is_memory_only:
            return
        self._file_path = Path(specifications_dir) / (shorten(self.name) + ".json")
        self.save_on_disk(None)

    @staticmethod
    def item_type():
        """Returns the type of project item the specification is compatible with.

        Returns:
            str: compatible project item type
        """
        raise NotImplementedError()

    def get_file_path(self):
        """Returns path to specification file.

        Returns:
            Path: path to specification file or None if specification is memory-only
        """
        return self._file_path

    def set_file_path(self, path):
        """Sets specification's file.

        Args:
            path (Path or str): file path
        """
        self._file_path = Path(path)

    def local_data(self):
        """Makes a dict out of specification's local data.

        Returns:
            dict: local data
        """
        return gather_leaf_data(self.to_dict(), self._dict_local_entries())

    def may_have_local_data(self):
        """Tests if specification could have project specific local data.

        Returns:
            bool: True if specification may have local data, False otherwise
        """
        return bool(self._dict_local_entries())

    def to_dict(self):
        """Serialized specification into a dictionary.

        Returns:
            dict: serialized specification
        """
        return {
            "name": self.name,
            "description": self.description,
        }

    @staticmethod
    def _dict_local_entries():
        """Returns entries or 'paths' in specification dict that should be stored in project's local data directory.

        Returns:
            list of tuple of str: local data item dict entries
        """
        return []

    @classmethod
    def from_dict(cls, specification_dict):
        """Deserializes specification from a dictionary.

        Args:
            specification_dict (dict): serialized object

        Returns:
            ProjectItemSpecification: deserialized object instance
        """
        return cls(**cls._init_args_from_dict(specification_dict))

    @staticmethod
    def _init_args_from_dict(specification_dict):
        """Returns keyword arguments needed to initialize a specification.

        Args:
            specification_dict (dict): serialized specification

        Returns:
            dict: keyword arguments for __init__()
        """
        return dict(specification_dict)

    def save_on_disk(self, file_path):
        """Saves the specification on disk.

        Args:
            file_path (Path or str, optional): target file path
        """
        if file_path is not None:
            self._file_path = Path(file_path)
        if self._file_path is None:
            raise InstanceIsMemoryOnly()
        with open(self._file_path, "w") as specification_file:
            dump_json_beautifully(self.to_dict(), specification_file)

    @classmethod
    def load_from_disk(cls, file_path):
        """Loads specification from disk.

        Args:
            file_path (Path or str): path to file containing serialized specification

        Returns:
            ProjectItemSpecification: loaded specification
        """
        file_path = Path(file_path)
        with open(file_path) as specification_file:
            specification_dict = json.load(specification_file)
        specification = cls.from_dict(specification_dict)
        specification.set_file_path(file_path)
        return specification

    def is_equivalent(self, other):
        """
        Returns True if two specifications are essentially the same.

        Args:
            other (DataTransformerSpecification): specification to compare to

        Returns:
            bool: True if the specifications are equivalent, False otherwise
        """
        return False

    def pop_local_entries(self, specification_dict):
        """Pops local entries from specification dict.

        Args:
            specification_dict (dict): serialized specification

        Returns:
            dict: local entries
        """
        local_entries = self._dict_local_entries()
        popped = gather_leaf_data(specification_dict, local_entries, pop=True)
        return popped
