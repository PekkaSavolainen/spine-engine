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
"""This module contains connection related stuff."""
from dataclasses import asdict, dataclass, field
import os.path

from datapackage import Package

from ..project_item.project_item_resource import file_resource
from ..utils.helpers import PartCount
from spinedb_api.filters.scenario_filter import SCENARIO_FILTER_TYPE


class Keys:
    FILTER_SETTINGS = "filter_settings"
    OPTIONS = "options"


class Connection:
    """Base class for connections between two project items."""

    def __init__(self, options=None, filter_settings=None):
        """
        Args:
            options (dict, optional): connection options
            filter_settings (FilterSettings, optional): filter settings
        """
        self.options = options if options is not None else {}
        self._filter_settings = filter_settings if filter_settings is not None else FilterSettings()

    def __eq__(self, other):
        if not isinstance(other, Connection):
            return NotImplemented
        return self.options == other.options and self._filter_settings == other._filter_settings

    @property
    def use_datapackage(self):
        """True if file resources are packaged into datapackage."""
        return self.options.get("use_datapackage", False)

    @property
    def use_memory_db(self):
        """True if database resources are converted to use in-memory database."""
        return self.options.get("use_memory_db", False)

    @property
    def purge_before_writing(self):
        """True if downstream database is purged before writing."""
        return self.options.get("purge_before_writing", False)

    @property
    def purge_settings(self):
        """Purge settings for connection.

        Purge settings is a dictionary mapping DB item types to a boolean value
        indicating whether to wipe them or not,
        or None if the entire DB should suffer.
        """
        return self.options.get("purge_settings")

    @property
    def write_index(self):
        """Write index for connection.

        Write index is the priority a connection has in concurrent writing.
        Defaults to 1, lower writes earlier.
        If two or more connections have the same, then no order is enforced among them.

        """
        return self.options.get("write_index", 1)

    @property
    def is_filter_online_by_default(self):
        """True if a filter should be online by default."""
        return self._filter_settings.auto_online

    def has_filters_online(self):
        """Tests if connection has any online filters.

        Returns:
            bool: True if there are online filters, False otherwise
        """
        return self._filter_settings.has_any_filter_online()

    def require_filter_online(self, filter_type):
        """Tests if online filters of given type are required for execution.

        Args:
            filter_type (str): filter type

        Returns:
            bool: True if online filters are required, False otherwise
        """
        return self.options.get("require_" + filter_type, False)

    def notifications(self):
        """Returns connection validation messages.

        Returns:
            list of str: notifications
        """
        notifications = []
        for filter_type in (SCENARIO_FILTER_TYPE,):
            if self.require_filter_online(filter_type) and (
                not self._filter_settings.has_filter_online(filter_type)
                if self._filter_settings.has_filters()
                else not self._filter_settings.auto_online
            ):
                filter_name = {SCENARIO_FILTER_TYPE: "scenario"}[filter_type]
                notifications.append(f"At least one {filter_name} filter must be active.")
        return notifications

    def receive_resources_from_source(self, resources):
        """
        Receives resources from source item.

        Args:
            resources (Iterable of ProjectItemResource): source item's forward resources
        """

    def receive_resources_from_destination(self, resources):
        """
        Receives resources from destination item.

        Args:
            resources (Iterable of ProjectItemResource): destination item's backward resources
        """

    def convert_backward_resources(self, resources, node_names, sibling_connections):
        """Called when advertising resources through this connection *in the BACKWARD direction*.
        Takes the initial list of resources advertised by the destination item and returns a new list,
        which is the one finally advertised.

        Args:
            resources (list of ProjectItemResource): Resources to convert
            node_names (tuple of str): names of source and destination nodes
            sibling_connections (dict): mapping from source and destination names to edge dict

        Returns:
            list of ProjectItemResource: converted resources
        """
        return self._apply_use_memory_db(self._apply_write_index(resources, node_names, sibling_connections))

    def convert_forward_resources(self, resources):
        """Called when advertising resources through this connection *in the FORWARD direction*.
        Takes the initial list of resources advertised by the source item and returns a new list,
        which is the one finally advertised.

        Args:
            resources (list of ProjectItemResource): Resources to convert

        Returns:
            list of ProjectItemResource: converted_resources
        """
        return self._apply_use_memory_db(self._apply_use_datapackage(resources))

    def _apply_use_memory_db(self, resources):
        """Conditionally converts database resources to use in-memory database.

        Args:
            edge (dict): connection edge
            resources (list of ProjectItemResource): Resources to convert

        Returns:
            list of ProjectItemResource: converted resources
        """
        if not self.use_memory_db:
            return resources
        final_resources = []
        for r in resources:
            if r.type_ == "database":
                r = r.clone(additional_metadata={"memory": True})
            final_resources.append(r)
        return final_resources

    def _apply_write_index(self, resources, node_names, sibling_connections):
        """Adds write index information to database resources

        Args:
            resources (list of ProjectItemResource): Resources to convert
            node_names (tuple of str): names of source and destination items
            sibling_connections (dict): mapping from source and destination names to sibling connection

        Returns:
            list of ProjectItemResource: converted resources
        """
        final_resources = []
        precursors = {
            node_names for node_names, sibling in sibling_connections.items() if sibling.write_index < self.write_index
        }
        for r in resources:
            if r.type_ == "database":
                r = r.clone(
                    additional_metadata={
                        "current": node_names,
                        "precursors": precursors,
                        "part_count": PartCount(),
                    }
                )
            final_resources.append(r)
        return final_resources

    def _apply_use_datapackage(self, resources):
        """Conditionally converts resources to use datapackage.

        Args:
            resources (list of ProjectItemResource): Resources to convert

        Returns:
            list of ProjectItemResource: converted resources
        """
        if not self.use_datapackage:
            return resources
        # Split CSVs from the rest of resources
        final_resources = []
        csv_filepaths = []
        for r in resources:
            if r.hasfilepath and os.path.splitext(r.path)[1].lower() == ".csv":
                csv_filepaths.append(r.path)
                continue
            final_resources.append(r)
        if not csv_filepaths:
            return final_resources
        # Build Package from CSVs and add it to the resources
        base_path = os.path.dirname(os.path.commonpath(csv_filepaths))
        package = Package(base_path=base_path)
        for path in csv_filepaths:
            package.add_resource({"path": os.path.relpath(path, base_path)})
        package_path = os.path.join(base_path, "datapackage.json")
        package.save(package_path)
        provider = resources[0].provider_name
        package_resource = file_resource(provider, package_path, label=f"datapackage@{provider}")
        package_resource.metadata = resources[0].metadata
        final_resources.append(package_resource)
        return final_resources

    def to_dict(self):
        """Serialized connection to dictionary.

        Returns:
            dict: serialized connection
        """
        connection_dict = {}
        if self.options:
            connection_dict["options"] = self.options.copy()
        if self._filter_settings.has_filters():
            connection_dict["filter_settings"] = self._filter_settings.to_dict()
        return connection_dict

    @classmethod
    def from_dict(cls, connection_dict):
        """Deserializes connection from dictionary.

        Args:
            connection_dict (dict): serialized connection

        Returns:
            ConnectionBase: deserialized connection
        """
        options = connection_dict.get("options", {})
        filter_settings = connection_dict.get("filter_settings")
        if filter_settings is not None:
            filter_settings = FilterSettings.from_dict(filter_settings)
        else:
            disabled_names = connection_dict.get("disabled_filters")
            if disabled_names is not None:
                known_filters = _restore_legacy_disabled_filters(disabled_names)
                filter_settings = FilterSettings(known_filters)
        return cls(options, filter_settings, **cls._init_args_from_dict(connection_dict))

    @classmethod
    def _init_args_from_dict(cls, connection_dict):
        """Returns keyword arguments needed to initialize a connection.

        Args:
            connection_dict (dict): serialized named object

        Returns:
            dict: keyword arguments for __init__()
        """
        return {}


@dataclass
class FilterSettings:
    """Filter settings for resource converting connections."""

    known_filters: dict = field(default_factory=dict)
    """mapping from resource labels and filter types to filter online statuses"""
    auto_online: bool = True
    """if True, set unknown filters automatically online"""

    def has_filters(self):
        """Tests if there are filters.

        Returns:
            bool: True if filters of any type exists, False otherwise
        """
        for filters_by_type in self.known_filters.values():
            for filters in filters_by_type.values():
                if filters:
                    return True
        return False

    def has_any_filter_online(self):
        """Tests in any filter is online.

        Returns:
            bool: True if any filter is online, False otherwise
        """
        for filters_by_type in self.known_filters.values():
            for filters in filters_by_type.values():
                if any(filters.values()):
                    return True
        return False

    def has_filter_online(self, filter_type):
        """Tests if any filter of given type is online.

        Args:
            filter_type (str): filter type to test

        Returns:
            bool: True if any filter of filter_type is online, False otherwise
        """
        for filters_by_type in self.known_filters.values():
            if any(filters_by_type.get(filter_type, {}).values()):
                return True
        return False

    def to_dict(self):
        """Stores the settings to a dict.

        Returns:
            dict: serialized settings
        """
        return asdict(self)

    @staticmethod
    def from_dict(settings_dict):
        """Restores the settings from a dict.

        Args:
            settings_dict (dict): serialized settings

        Returns:
            FilterSettings: restored settings
        """
        return FilterSettings(**settings_dict)


def _restore_legacy_disabled_filters(disabled_filter_names):
    """Converts legacy serialized disabled filter names to known filters dict.

    Args:
        disabled_filter_names (dict): disabled filter names with names stored as lists

    Returns:
        dict: known filters
    """
    converted = {}
    for label, names_by_type in disabled_filter_names.items():
        converted_names_by_type = converted.setdefault(label, {})
        for filter_type, names in names_by_type.items():
            converted_names_by_type[filter_type] = {name: False for name in names}
    return converted
