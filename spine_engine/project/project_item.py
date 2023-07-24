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
"""This module contains project item related stuff."""
from __future__ import annotations
from pathlib import Path
import shutil
from typing import Optional
from ..exception import ProjectComponentNotFound, UnrecognizedNodeType
from .project_item_specification import ProjectItemSpecification
from ..utils.helpers import shorten


class ProjectItem:
    """Project's node."""

    def __init__(self, description):
        """
        Args:
            description (str): item description
        """
        self.description = description
        self._project = None

    @classmethod
    def item_type(cls):
        """Returns item's type string.

        Returns:
            str: type of item
        """
        return cls.__name__

    @property
    def project(self) -> Optional[Project]:
        """Project the item is part of or None."""
        return self._project

    def set_project(self, project):
        """Makes item part of a project or removes item from project.

        If project replaces another one, moves item's on-disk data to new project.

        Args:
            project (Project, optional): project; removes item from project if None
        """
        if project is self._project:
            return
        if self._project is None:
            self._project = project
            self._project.project_dir.add_project_item(project.name_for_item(self), project.items_dir)
            return
        if project is None:
            if not self._project.item_should_preserve_old_data_directory():
                shutil.rmtree(self._data_dir)
            self._data_dir = None
        else:
            self.set_items_dir()
        self._project = project

    def rename_data_dir(self, new_name):
        """Renames item's data directory.

        Args:
            new_name (str): new name
        """
        new_data_dir = self._data_dir.parent / shorten(new_name)
        shutil.move(self._data_dir, new_data_dir)
        self._data_dir = new_data_dir

    def set_items_dir(self, items_dir):
        """Moves item's data directory to another project directory.

        Args
            items_dir (Path): new items directory
        """
        new_data_dir = items_dir / shorten(self._project.name_for_item())
        if self._project is not None and self._project.item_should_preserve_old_data_directory:
            shutil.copy(self._data_dir, new_data_dir)
        else:
            shutil.move(self._data_dir, new_data_dir)
        self._data_dir = new_data_dir

    def to_dict(self):
        """Serializes item into dictionary.

        Returns:
            dict: serialized node
        """
        item_dict = {
            "type": self.item_type(),
            "description": self.description,
        }
        return item_dict

    @staticmethod
    def item_dict_local_entries():
        """Returns entries or 'paths' in item dict that should be stored in project's local data directory.

        Returns:
            list of tuple of str: local data item dict entries
        """
        return []

    @classmethod
    def from_dict(cls, item_dict, project_dir, specifications):
        """Deserializes item from dictionary.

        Args:
            item_dict (dict): serialized item
            project_dir (Path): path to project directory
            specifications (list of ProjectItemSpecification): list of specifications available for node

        Returns:
            ProjectItem: deserialized item

        Raises:
            UnrecognizedProjectItemType: raised when item dictionary contains unrecognized item type
        """
        item_type = item_dict["type"]
        if item_type != cls.item_type():
            raise UnrecognizedNodeType(item_type)
        description = item_dict["description"]
        return cls(description, **cls._init_args_from_dict(item_dict, project_dir, specifications))

    @staticmethod
    def _init_args_from_dict(item_dict, project_dir, specifications):
        """Returns keyword arguments needed to initialize an item.

        Args:
            item_dict (dict): serialized item
            specifications (list of ProjectItemSpecification): list of specifications available for item
            project_dir (Path): path to project directory

        Returns:
            dict: keyword arguments for as_node()
        """
        return {}

    def upgrade_v1_to_v2(self, item_name, item_dict):
        """
        Upgrades item's dictionary from v1 to v2.

        Subclasses should reimplement this method if there are changes between version 1 and version 2.

        Args:
            item_name (str): item's name
            item_dict (dict): Version 1 item dictionary

        Returns:
            dict: Version 2 item dictionary
        """
        return item_dict

    def upgrade_v2_to_v3(self, item_name, item_dict, make_unique_importer_specification_name):
        """
        Upgrades item's dictionary from v2 to v3.

        Subclasses should reimplement this method if there are changes between version 2 and version 3.

        Args:
            item_name (str): item's name
            item_dict (dict): Version 2 item dictionary
            make_unique_importer_specification_name (Callable): a function that returns an Importer specification name

        Returns:
            dict: Version 3 item dictionary
        """
        return item_dict


class SpecificationSupportingProjectItem(ProjectItem):
    """Project item that supports specifications."""

    def __init__(self, description, specification):
        """
        Args:
            description (str): item description
            specification (ProjectItemSpecification, optional): specification
        """
        super().__init__(description)
        self._specification = specification

    @staticmethod
    def make_specification(name, description):
        """Constructs a new specification.

        Args:
            name (str): name of specification
            description (str): specification description

        Returns:
            ProjectItemSpecification: specification or None if item does not support specifications
        """
        raise NotImplementedError()

    @staticmethod
    def load_specification_from_disk(file_path):
        """Loads specification from given path.

        Args:
            file_path (Path or str): path to specification file

        Returns:
            ProjectItemSpecification: specification
        """
        raise NotImplementedError()

    def set_specification(self, specification):
        """Sets specification for item.

        Args:
            specification (ProjectItemSpecification, optional): specification
        """
        self._specification = specification

    def get_specification(self):
        """Returns item's specification or None if none is set.

        Returns:
            ProjectItemSpecification: specification or None if specification is not set
        """
        return self._specification

    def to_dict(self):
        """See base class."""
        item_dict = super().to_dict()
        if self._specification is not None:
            item_dict["specification"] = self._specification.name
        return item_dict

    @staticmethod
    def _init_args_from_dict(item_dict, project_dir, specifications):
        """See base class."""
        init_args = ProjectItem._init_args_from_dict(item_dict, project_dir, specifications)
        specification_name = item_dict.get("specification")
        if specification_name is not None:
            for specification in specifications:
                if specification.name == specification_name:
                    init_args["specification"] = specification
                    break
            else:
                raise ProjectComponentNotFound(specification_name)
        else:
            init_args["specification"] = None
        return init_args
