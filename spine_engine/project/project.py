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
"""This module contains Spine Toolbox project."""
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
import networkx as nx

from ..exception import (
    InvalidConnection,
    InvalidJump,
    ProjectComponentNotFound,
    NameContainsInvalidCharacters,
    DuplicateName,
    DuplicateShortName,
)
from .connection import Connection
from .jump import Jump
from .project_dir import ProjectDir
from .project_item import SpecificationSupportingProjectItem
from .project_settings import ProjectSettings
from ..exception import InstanceIsMemoryOnly
from ..utils.helpers import AppSettings, fails_if_memory_only, root_package_name, shorten
from ..utils.serialization import deserialize_path, serialize_path

LATEST_PROJECT_VERSION = 12
PROJECT_FILENAME = "project.json"
PROJECT_LOCAL_DATA_DIR_NAME = "local"
PROJECT_LOCAL_DATA_FILENAME = "project_local_data.json"
SPECIFICATION_LOCAL_DATA_FILENAME = "specification_local_data.json"
PROJECT_ZIP_FILENAME = "project_package"  # ZIP-file name for remote execution
# Invalid characters for directory names
# NOTE: "." is actually valid in a directory name but this is
# to prevent the user from creating directories like /..../
INVALID_CHARS = ["<", ">", ":", "\"", "/", "\\", "|", "?", "*", "."]


class Key:
    APP_SETTINGS = "app_settings"
    DESCRIPTION = "description"
    JUMPS = "jumps"
    NAME = "name"
    PROJECT_DIR = "project_dir"
    SETTINGS = "settings"
    SPECIFICATIONS = "specifications"


class NodeKey:
    ITEM = "item"


class EdgeKey:
    CONNECTION = "connection"


class AppSettingsKey:
    DELETE_REMOVED_ITEM_DATA = "deleteData"


class Project(nx.DiGraph):
    """Spine Toolbox project."""

    def __init__(
        self,
        name,
        description,
        project_dir,
        settings=None,
        app_settings=None,
    ):
        """
        Args:
            name (str): name of project
            description (str): description of project
            project_dir (ProjectDir or Path or str): project directory
            settings (ProjectSettings, optional): project settings; if None, uses default settings
            app_settings (AppSettings or QSettings): application settings
        """
        kwargs = {
            Key.NAME: name,
            Key.DESCRIPTION: description,
            Key.SETTINGS: settings if settings is not None else ProjectSettings(),
            Key.APP_SETTINGS: app_settings if app_settings is not None else AppSettings({}),
            Key.SPECIFICATIONS: [],
            Key.JUMPS: [],
            Key.PROJECT_DIR: project_dir if isinstance(project_dir, ProjectDir) else ProjectDir(project_dir)
        }
        super().__init__(**kwargs)

    @property
    def name(self) -> str:
        """Name of project."""
        return self.graph[Key.NAME]

    @property
    def description(self) -> str:
        """Project description."""
        return self.graph[Key.DESCRIPTION]

    @property
    def settings(self) -> ProjectSettings:
        """Project settings."""
        return self.graph[Key.SETTINGS]

    @property
    def project_dir(self) -> ProjectDir:
        """Project directory."""
        return self.graph[Key.PROJECT_DIR]

    def name_for_item(self, item):
        """Finds the node name that contains given project item.

        Args:
            item (ProjectItem): item to look for

        Returns:
            str: name of node

        Raises:
            ProjectComponentNotFound: raised when item is not in project
        """
        for name, node in self.nodes.items():
            if node[NodeKey.ITEM] is item:
                return name
        raise ProjectComponentNotFound()

    def item_should_preserve_old_data_directory(self):
        """Checks if item should preserve its old data directory from app settings.

        Returns:
            bool: True if old data directory should be preserved, False otherwise
        """
        value = int(self.graph[Key.APP_SETTINGS].value(AppSettings.APP_ROOT_KEY + "/" + AppSettingsKey.DELETE_REMOVED_ITEM_DATA, "0"))
        return value != 2

    def add_node(self, name, **attr):
        """Adds a project item node to project.

        Args:
            name (str): name of node
            attr: node attributes
        """
        self._validate_project_item_name(name)
        super().add_node(name, **attr)
        attr[NodeKey.ITEM].set_project(self)

    def rename_node(self, name, new_name):
        """Renames a project item node.

        Args:
            name (str): name of node
            new_name (str): new name to give to the node

        Raises:
            ProjectComponentNotFound: raised when name is not in project
            DuplicateName: raised when new name is reserved
            DuplicateShortName: raised when new name would clash with existing short name
        """
        try:
            node = self.nodes[name]
        except KeyError:
            raise ProjectComponentNotFound()
        if new_name in self.nodes:
            raise DuplicateName()
        if shorten(new_name) in {shorten(node) for node in self.nodes}:
            raise DuplicateShortName()
        incoming_edges = {source: edge for (source, destination), edge in self.edges.items() if destination == name}
        outgoing_edges = {destination: edge for (source, destination), edge in self.edges.items() if source == name}
        super().remove_node(name)
        super().add_node(new_name, **node)
        with suppress(InstanceIsMemoryOnly):
            node[NodeKey.ITEM].rename_data_dir(new_name)
        for source, edge in incoming_edges.items():
            super().add_edge(source, new_name, **edge)
        for destination, edge in outgoing_edges.items():
            super().add_edge(new_name, destination, **edge)
        for jump in self.graph[Key.JUMPS]:
            if jump.source == name:
                jump.source = new_name
            if jump.destination == name:
                jump.destination = new_name

    def remove_node(self, name):
        """Removes a node, its edges and all jumps that become invalid.

        Args:
            name (str): name of node
        """
        try:
            item = self.nodes[name][NodeKey.ITEM]
        except KeyError:
            raise ProjectComponentNotFound()
        super().remove_node(name)
        item.set_project(None)
        jumps = self.graph[Key.JUMPS]
        if jumps:
            jumps_to_keep = [jump for jump in jumps if jump.source != name and jump.destination != name]
            if jumps_to_keep:
                valid_jumps = []
                items_by_jump = self._get_nodes_by_jump()
                for i, jump in enumerate(jumps):
                    try:
                        self._validate_jump(jump, items_by_jump)
                    except InvalidJump:
                        continue
                    else:
                        valid_jumps.append(jump)
                jumps_to_keep = valid_jumps
            self.graph[Key.JUMPS] = jumps_to_keep

    def add_edge(self, source, destination, **attr):
        """Connects two nodes.

        Args:
            source (str): name of source item
            destination (str): name of destination item
            attr: edge attributes

        Raises:
            ProjectComponentNotFound: raised if source or destination don't exist
            InvalidConnection: raised if the edge would not be valid
        """
        if source not in self.nodes or destination not in self.nodes:
            raise ProjectComponentNotFound()
        if source == destination:
            raise InvalidConnection("cannot connect item back to itself")
        super().add_edge(source, destination, **attr)
        if not nx.is_directed_acyclic_graph(self):
            super().remove_edge(source, destination)
            raise InvalidConnection("cannot create loops")

    def remove_edge(self, source, destination):
        """Removes an edge.

        Args:
            source (str): name of source node
            destination (str): name of destination node

        Raises:
            ProjectComponentNotFound: raised if edge was not found
            InvalidJump: raised if removing the edge would invalidate a jump
        """
        jumps = self.graph[Key.JUMPS]
        if not jumps:
            try:
                super().remove_edge(source, destination)
            except nx.exception.NetworkXError:
                raise ProjectComponentNotFound()
        else:
            try:
                edge = self.edges[source, destination]
            except KeyError:
                raise ProjectComponentNotFound()
            super().remove_edge(source, destination)
            items_by_jump = self._get_nodes_by_jump()
            for jump in jumps:
                try:
                    self._validate_jump(jump, items_by_jump)
                except InvalidJump as error:
                    super().add_edge(source, destination, **edge)
                    raise error

    def make_jump(self, source, destination):
        """Creates a jump between two nodes.

        Args:
            source (str): name of source node
            destination (str): name of destination node

        Returns:
            Jump: jump from source to destination

        Raises:
            InvalidJump: raised if jump is not valid
            ProjectComponentNotFound: raised if source or destination does not exist
        """
        if source not in self.nodes or destination not in self.nodes:
            raise ProjectComponentNotFound()
        with suppress(ProjectComponentNotFound):
            return self.get_jump(source, destination)
        jump = Jump(source, destination)
        self.graph[Key.JUMPS].append(jump)
        items_by_jump = self._get_nodes_by_jump()
        try:
            self._validate_jump(jump, items_by_jump)
        except InvalidJump as error:
            del self.graph[Key.JUMPS][-1]
            raise error
        return jump

    def get_jump(self, source, destination):
        """Returns a jump between two items.

        Args:
            source (str): name of source item
            destination (str): name of destination item

        Returns:
            Jump: jump from source to destination

        Raises:
            ProjectComponentNotFound: raised if jump was not found
        """
        for jump in self.graph[Key.JUMPS]:
            if jump.source == source and jump.destination == destination:
                return jump
        raise ProjectComponentNotFound()

    def add_specification(self, specification):
        """Adds a specification to the project.

        Args:
            specification (ProjectItemSpecification): specification to add

        Raises:
            DuplicateName: raised when a specification with the same name already exists in project
        """
        if any(specification.name == other.name for other in self.graph[Key.SPECIFICATIONS]):
            raise DuplicateName()
        self.graph[Key.SPECIFICATIONS].append(specification)

    def get_specification(self, name):
        """Returns a project item specification.

        Args:
            name (str): name of specification

        Returns:
            ProjectItemSpecification: specification

        Raises:
            ProjectComponentNotFound: raised if specification was not found
        """
        for specification in self.graph[Key.SPECIFICATIONS]:
            if specification.name == name:
                return specification
        raise ProjectComponentNotFound()

    def specifications(self):
        """Returns iterator over all specifications.

        Yields:
            ProjectItemSpecification: specifications in project
        """
        yield from self.graph[Key.SPECIFICATIONS]

    def remove_specification(self, name):
        """Removes a project item specification from project.

        Args:
            name (str): name of specification

        Raises:
            ProjectComponentNotFound: raised if specification was not found
        """
        for i, specification in enumerate(self.graph[Key.SPECIFICATIONS]):
            if specification.name == name:
                del self.graph[Key.SPECIFICATIONS][i]
                for node in self.nodes.values():
                    item = node[NodeKey.ITEM]
                    if isinstance(item, SpecificationSupportingProjectItem) and item.get_specification().name == name:
                        item.set_specification(None)
                return
        raise ProjectComponentNotFound()

    def to_dict(self, items_packages):
        """Serializes the project to a dictionary.

        Args:
            items_packages (dict): mapping from package name to items package

        Returns:
            dict: serialized project
        """
        project_dict = {
            "version": LATEST_PROJECT_VERSION,
            "name": self.name,
            "description": self.description,
            "settings": self.graph[Key.SETTINGS].to_dict(),
            "project_item_packages": self._project_item_packages_dict(items_packages),
            "specifications": self._specification_paths_to_dicts(),
            "connections": self._edges_to_dicts(),
            "jumps": self._jumps_to_dicts(),
            "items": self._item_dicts(),
        }
        return project_dict

    def _specification_paths_to_dicts(self):
        """Collects specification file paths for serialization.

        If project is physical, path inside project dir will be serialized as relative paths.

        Returns:
            dict: mapping from specification type to list of specification paths
        """
        paths_dict = defaultdict(lambda: defaultdict(list))
        for specification in self.graph[Key.SPECIFICATIONS]:
            if not specification.is_part_of_plugin:
                if specification.is_memory_only:
                    raise RuntimeError("no specification file for memory-only specification")
                paths_dict[root_package_name(specification)][specification.item_type()].append(
                    serialize_path(specification.get_file_path(), self.project_dir.path)
                )
        return paths_dict

    def _edges_to_dicts(self):
        """Serializes edges.

        Returns:
            list of dict: serialized edge
        """
        dicts = []
        for (source, destination), edge in self.edges.items():
            connection_dict = edge[EdgeKey.CONNECTION].to_dict()
            connection_dict["from"] = source
            connection_dict["to"] = destination
            dicts.append(connection_dict)
        return dicts

    def _jumps_to_dicts(self):
        """Serializes jumps.

        Returns:
            list of dict: serialized jumps
        """
        return [jump.to_dict() for jump in self.graph[Key.JUMPS]]

    @staticmethod
    def _project_item_packages_dict(items_packages):
        """Creates dict that contains project item package information.

        Args:
            items_packages (dict): mapping from package name to items package

        Returns:
            dict: project item package information
        """
        packages_dict = {}
        for name, package in items_packages.items():
            packages_dict[name] = {"version": package.LATEST_PROJECT_DICT_ITEMS_VERSION}
        return packages_dict

    def _item_dicts(self):
        """Serializes project items.

        Returns:
            dict: mapping from project item name to item dict
        """
        item_dicts = defaultdict(dict)
        for name, node in self.nodes.items():
            item = node[NodeKey.ITEM]
            item_dicts[root_package_name(item)][name] = item.to_dict()
        return item_dicts

    @staticmethod
    def from_dict(project_dict, project_dir, items_packages, plugins):
        """Deserializes project from dictionary.

        Loads specifications from disk as needed.

        Args:
            project_dict (dict): project dictionary
            project_dir (ProjectDir or Path or str): project directory
            items_packages (dict): mapping from project item package name to item module
            plugins (list of ProjectItemSpecification): specifications that are part of plugins

        Returns:
            Project: deserialized project
        """
        name = project_dict["name"]
        description = project_dict["description"]
        settings = ProjectSettings.from_dict(project_dict["settings"])
        project_item_packages = project_dict["project_item_packages"]
        items_dict = project_dict["items"]
        specifications = defaultdict(list)
        for plugin in plugins:
            specifications[plugin.item_type()].append(plugin)
        items = {}
        for package_name, package_info in project_item_packages.items():
            items_version = package_info["version"]
            item_package = items_packages[package_name]
            items_dict[package_name] = item_package.upgrade_items_to_latest(items_dict[package_name], items_version)
            for item_type, serialized_paths in project_dict["specifications"][package_name].items():
                for path in serialized_paths:
                    specification_file_path = deserialize_path(path, project_dir)
                    specification = item_package.PROJECT_ITEM_CLASSES[item_type].load_specification_from_disk(
                        specification_file_path
                    )
                    specifications[specification.item_type()].append(specification)
            item_constructors = {
                Item.item_type(): Item.from_dict for Item in item_package.PROJECT_ITEM_CLASSES.values()
            }
            for item_name, item_dict in items_dict[package_name].items():
                item_type = item_dict["type"]
                item = item_constructors[item_dict["type"]](item_dict, project_dir, specifications[item_type])
                items[item_name] = item
        project = Project(name, description, project_dir, settings)
        for name, item in items.items():
            project.add_node(name, item=item)
        project.graph[Key.SPECIFICATIONS] = sum(specifications.values(), [])
        for connection_dict in project_dict["connections"]:
            connection = Connection.from_dict(connection_dict)
            source = connection_dict["from"]
            destination = connection_dict["to"]
            project.add_edge(source, destination, connection=connection)
        jumps = [Jump.from_dict(jump_dict) for jump_dict in project_dict["jumps"]]
        project.graph[Key.JUMPS] = jumps
        return project

    def _validate_project_item_name(self, name):
        """Raises an exception when the name of a project item is not valid.

        Args:
            name (str): name of item
        """
        if any(x in INVALID_CHARS for x in name):
            raise NameContainsInvalidCharacters()
        for existing_name in self.nodes:
            if name == existing_name:
                raise DuplicateName()
            if shorten(name) == shorten(existing_name):
                raise DuplicateShortName()

    def _validate_jump(self, jump, items_by_jump):
        """Raises an exception in case jump is not valid.

        Args:
            jump (Jump): the jump to check
            items_by_jump (dict): mapping from jump source and destination to set of project items

        Raises:
            InvalidJump: raised if jump is not valid
        """
        for other in self.graph[Key.JUMPS]:
            if other is jump:
                continue
            if other.source == jump.source:
                raise InvalidJump("two jumps cannot start from the same item")
            jump_items = items_by_jump[(jump.source, jump.destination)]
            other_items = items_by_jump[(other.source, other.destination)]
            intersection = jump_items & other_items
            if intersection not in (set(), jump_items, other_items):
                raise InvalidJump("jump cannot partially overlap another")
        if not self.has_node(jump.destination):
            raise InvalidJump(f"Loop destination '{jump.destination}' not found in DAG")
        if not self.has_node(jump.source):
            raise InvalidJump(f"Loop source '{jump.source}' not found in DAG")
        if jump.source == jump.destination:
            return
        if nx.has_path(self, jump.source, jump.destination):
            raise InvalidJump("Cannot loop in forward direction.")
        if not nx.has_path(nx.reverse_view(self), jump.source, jump.destination):
            raise InvalidJump("Cannot loop between DAG branches.")

    def _get_nodes_by_jump(self):
        """Returns a dict mapping jumps to a set of nodes between destination and source.

        Returns:
            dict: mapping from jump source and destination to set of item nodes
        """
        nodes_by_jump = {}
        for jump in self.graph[Key.JUMPS]:
            try:
                nodes_by_jump[jump.source, jump.destination] = {
                    item_name for path in nx.all_simple_paths(self, jump.destination, jump.source) for item_name in path
                }
            except nx.NodeNotFound:
                nodes_by_jump[jump.source, jump.destination] = set()
        return nodes_by_jump
