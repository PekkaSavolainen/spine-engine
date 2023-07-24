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
"""Contains functions that upgrade and convert project dicts from earlier versions to the latest version."""
import logging
import os
import json
import copy
from spine_engine.utils.serialization import serialize_path, deserialize_path
from .project import LATEST_PROJECT_VERSION
from .exception import ProjectVersionTooHigh, ProjectUpgradeFailed

_logger = logging.getLogger(__name__)


def upgrade(project_dict, project_dir, items_module):
    """Upgrades the project described in given project dictionary to the latest version.

    Args:
        project_dict (dict): Project configuration dictionary
        project_dir (str): Path to current project directory
        items_module (module): project items module

    Returns:
        tuple: Latest version of the project info dictionary, dict's previous version and the latest version
    """
    v = project_dict["project"]["version"]
    if v > LATEST_PROJECT_VERSION:
        raise ProjectVersionTooHigh()
    if v < LATEST_PROJECT_VERSION:
        upgraded_dict = _upgrade_to_latest(project_dict, project_dir, v, items_module)
        return upgraded_dict, v, LATEST_PROJECT_VERSION
    return project_dict, v, v


def _upgrade_to_latest(project_dict, project_dir, old_version, items_module):
    """Upgrades the given project dictionary to the latest version.

    Args:
        project_dict (dict): Project dictionary (JSON) to be upgraded
        project_dir (str): Path to current project directory
        old_version (int): Original version of the project dictionary
        items_module (module): project items module

    Returns:
        dict: Upgraded project dictionary
    """
    while old_version < LATEST_PROJECT_VERSION:
        if old_version == 1:
            project_dict = upgrade_v1_to_v2(project_dict, items_module.PROJECT_ITEM_CLASSES)
        elif old_version == 2:
            project_dict = upgrade_v2_to_v3(project_dict, project_dir, items_module.PROJECT_ITEM_CLASSES)
        elif old_version == 3:
            project_dict = upgrade_v3_to_v4(project_dict)
        elif old_version == 4:
            project_dict = upgrade_v4_to_v5(project_dict)
        elif old_version == 5:
            project_dict = upgrade_v5_to_v6(project_dict, project_dir)
        elif old_version == 6:
            project_dict = upgrade_v6_to_v7(project_dict)
        elif old_version == 7:
            project_dict = upgrade_v7_to_v8(project_dict)
        elif old_version == 8:
            project_dict = upgrade_v8_to_v9(project_dict)
        elif old_version == 9:
            project_dict = upgrade_v9_to_v10(project_dict)
        elif old_version == 10:
            project_dict = upgrade_v10_to_v11(project_dict, items_module)
        old_version += 1
    return project_dict


def upgrade_v1_to_v2(old, spine_items_classes):
    """Upgrades version 1 project dictionary to version 2.

    Changes:
        objects -> items, tool_specifications -> specifications
        store project item dicts under ["items"][<project item name>] instead of using their categories as keys
        specifications must be a dict instead of a list
        Add specifications["Tool"] that must be a dict
        Remove "short name" from all project items

    Args:
        old (dict): Version 1 project dictionary
        spine_items_classes (dict): Mapping from item type to project item class from spine_items

    Returns:
        dict: Version 2 project dictionary
    """
    new = dict()
    new["version"] = 2
    new["name"] = old["project"]["name"]
    new["description"] = old["project"]["description"]
    new["specifications"] = dict()
    new["specifications"]["Tool"] = old["project"]["tool_specifications"]
    new["connections"] = old["project"]["connections"]
    # Change 'objects' to 'items' and remove all 'short name' entries
    # Also stores item_dict under their name and not under category
    items = dict()
    for category in old["objects"].keys():
        for item_name in old["objects"][category].keys():
            old["objects"][category][item_name].pop("short name", "")  # Remove 'short name'
            # Add type to old item_dict if not there
            if "type" not in old["objects"][category][item_name]:
                old["objects"][category][item_name]["type"] = category[:-1]  # Hackish, but should do the trick
            # Upgrade item_dict to version 2 if needed
            v1_item_dict = old["objects"][category][item_name]
            item_type = old["objects"][category][item_name]["type"]
            v2_item_dict = spine_items_classes[item_type].upgrade_v1_to_v2(item_name, v1_item_dict)
            items[item_name] = v2_item_dict  # Store items using their name as key
    return dict(project=new, items=items)


def upgrade_v2_to_v3(old, project_dir, spine_items_classes):
    """Upgrades version 2 project dictionary to version 3.

    Changes:
        1. Move "specifications" from "project" -> "Tool" to just "project"
        2. The "mappings" from importer items are used to build Importer specifications

    Args:
        old (dict): Version 2 project dictionary
        project_dir (str): Path to current project directory
        spine_items_classes (dict): Mapping from item type to project item class from spine_items

    Returns:
        dict: Version 3 project dictionary
    """
    new = copy.deepcopy(old)
    project = new["project"]
    project["version"] = 3
    # Put DT specs in their own subkey
    project["specifications"]["Data Transformer"] = dt_specs = []
    tool_specs = project["specifications"].get("Tool", [])
    for i, spec in reversed(list(enumerate(tool_specs))):
        spec_path = deserialize_path(spec, project_dir)
        if not os.path.exists(spec_path):
            _logger.warning(f"Upgrading Tool spec failed. <b>%s</b> does not exist.", spec_path)
            continue
        with open(spec_path, "r") as fp:
            try:
                spec = json.load(fp)
            except ValueError:
                continue
            if spec.get("item_type") == "Data Transformer":
                dt_specs.append(tool_specs.pop(i))
    project["specifications"]["Importer"] = importer_specs = []
    for item_name, old_item_dict in old["items"].items():
        item_type = old_item_dict["type"]
        try:
            new["items"][item_name] = (
                spine_items_classes[item_type].upgrade_v2_to_v3(item_name, old_item_dict, _make_unique_importer_specification_name)
            )
        except KeyError:
            # This happens when an unknown item type is encountered.
            # spine_items does not contain 'Combiner' anymore
            if item_type == "Combiner":
                new["items"][item_name] = old_item_dict
        if item_type == "Importer":
            mappings = old_item_dict.get("mappings")
            # Sanitize old mappings, as we use to do in Importer.from_dict
            if mappings is None:
                mappings = list()
            # Convert table_types and table_row_types keys to int since json always has strings as keys.
            for _, mapping in mappings:
                table_types = mapping.get("table_types", {})
                mapping["table_types"] = {
                    table_name: {int(col): t for col, t in col_types.items()}
                    for table_name, col_types in table_types.items()
                }
                table_row_types = mapping.get("table_row_types", {})
                mapping["table_row_types"] = {
                    table_name: {int(row): t for row, t in row_types.items()}
                    for table_name, row_types in table_row_types.items()
                }
            # Convert serialized paths to absolute in mappings
            _fix_1d_array_to_array(mappings)
            # Make item specs from sanitized mappings
            for k, (label, mapping) in enumerate(mappings):
                spec_name = _make_unique_importer_specification_name(item_name, label, k)
                spec = dict(name=spec_name, item_type="Importer", mapping=mapping)
                spec_path = os.path.join(project_dir, spec_name + ".json")
                with open(spec_path, "w") as fp:
                    json.dump(spec, fp, indent=4)
                importer_specs.append(serialize_path(spec_path, project_dir))
    return new


def upgrade_v3_to_v4(old):
    """Upgrades version 3 project dictionary to version 4.

    Changes:
        1. Rename "Exporter" item type to "GdxExporter"

    Args:
        old (dict): Version 3 project dictionary

    Returns:
        dict: Version 4 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 4
    for item_dict in new["items"].values():
        if item_dict["type"] == "Exporter":
            item_dict["type"] = "GdxExporter"
    return new


def upgrade_v4_to_v5(old):
    """Upgrades version 4 project dictionary to version 5.

    Changes:
        1. Get rid of "Combiner" items.

    Args:
        old (dict): Version 4 project dictionary

    Returns:
        dict: Version 5 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 5
    combiners = []
    for name, item_dict in new["items"].items():
        if item_dict["type"] == "Combiner":
            combiners.append(name)
    for combiner in combiners:
        del new["items"][combiner]
    conns_to_item = {}
    conns_from_item = {}
    for conn in new["project"]["connections"]:
        from_name, _ = conn["from"]
        to_name, _ = conn["to"]
        conns_to_item.setdefault(to_name, []).append(conn)
        conns_from_item.setdefault(from_name, []).append(conn)
    conns_to_remove = []
    conns_to_add = []
    combiners_copy = combiners.copy()
    while combiners:
        combiner = combiners.pop()
        conns_to = conns_to_item.get(combiner, [])
        conns_from = conns_from_item.get(combiner, [])
        for conn_to in conns_to:
            conns_to_remove.append(conn_to)
            from_name, from_anchor = conn_to["from"]
            resource_filters = conn_to.get("resource_filters", {})
            for conn_from in conns_from:
                conns_to_remove.append(conn_from)
                to_name, to_anchor = conn_from["to"]
                more_resource_filters = conn_from.get("resource_filters", {})
                new_conn = {"from": [from_name, from_anchor], "to": [to_name, to_anchor]}
                for resource, filters in more_resource_filters.items():
                    for filter_type, values in filters.items():
                        existing_values = resource_filters.setdefault(resource, {}).setdefault(filter_type, [])
                        for value in values:
                            if value not in existing_values:
                                existing_values.append(value)
                if resource_filters:
                    new_conn["resource_filters"] = resource_filters
                if not {from_name, to_name}.intersection(combiners_copy):
                    conns_to_add.append(new_conn)
                conns_to_item.setdefault(to_name, []).append(new_conn)
                conns_from_item.setdefault(from_name, []).append(new_conn)
    new["project"]["connections"] += conns_to_add
    for conn in conns_to_remove:
        try:
            new["project"]["connections"].remove(conn)
        except ValueError:
            pass
    return new


def upgrade_v5_to_v6(old, project_dir):
    """Upgrades version 5 project dictionary to version 6.

    Changes:
        1. Data store URL labels do not have '{' and '}' anymore
        2. Importer stores resource labels instead of serialized paths in "file_selection".
        3. Gimlet's "selections" is now called "file_selection"
        4. Gimlet stores resource labels instead of serialized paths in "file_selection".
        5. Gimlet and Tool store command line arguments as serialized CmdLineArg objects, not serialized paths

    Args:
        old (dict): Version 5 project dictionary
        project_dir (str): Path to current project directory

    Returns:
        dict: Version 6 project dictionary
    """

    def fix_file_selection(item_dict):
        old_selection = item_dict.get("file_selection", list())
        new_selection = list()
        for path, selected in old_selection:
            deserialized = deserialize_path(path, project_dir)
            if deserialized.startswith("{") and deserialized.endswith("}"):
                # Fix old-style data store resource labels '{db_url@item name}'.
                deserialized = deserialized[1:-1]
            new_selection.append([deserialized, selected])
        item_dict["file_selection"] = new_selection

    def fix_cmd_line_args(item_dict):
        old_args = item_dict.get("cmd_line_args", list())
        new_args = list()
        for arg in old_args:
            deserialized = deserialize_path(arg, project_dir)
            if deserialized.startswith("{") and deserialized.endswith("}"):
                # Fix old-style data store resource labels '{db_url@item name}'.
                deserialized = deserialized[1:-1]
            # We assume all args are resource labels. This may not always be true, though, and needs to be
            # fixed manually once the project has been loaded.
            new_args.append({"type": "resource", "arg": deserialized})
        item_dict["cmd_line_args"] = new_args

    new = copy.deepcopy(old)
    new["project"]["version"] = 6
    importer_dicts = [item_dict for item_dict in new["items"].values() if item_dict["type"] == "Importer"]
    for import_dict in importer_dicts:
        fix_file_selection(import_dict)
    gimlet_dicts = [item_dict for item_dict in new["items"].values() if item_dict["type"] == "Gimlet"]
    for gimlet_dict in gimlet_dicts:
        gimlet_dict["file_selection"] = gimlet_dict.pop("selections", list())
        fix_file_selection(gimlet_dict)
        fix_cmd_line_args(gimlet_dict)
    tool_dicts = [item_dict for item_dict in new["items"].values() if item_dict["type"] == "Tool"]
    for tool_dict in tool_dicts:
        fix_cmd_line_args(tool_dict)
    return new


def upgrade_v6_to_v7(old):
    """Upgrades version 6 project dictionary to version 7.

    Changes:
        1. Introduces Mergers in between DS -> DS links.

    Args:
        old (dict): Version 6 project dictionary

    Returns:
        dict: Version 7 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 7
    data_stores = []
    for name, item_dict in new["items"].items():
        if item_dict["type"] == "Data Store":
            data_stores.append(name)
    ds_ds_connections = {}
    to_remove = []
    for conn in new["project"]["connections"]:
        from_name, _ = conn["from"]
        to_name, _ = conn["to"]
        if from_name in data_stores and to_name in data_stores:
            ds_ds_connections.setdefault(tuple(conn["to"]), []).append(conn["from"])
            to_remove.append(conn)
    for to_conn, from_conns in ds_ds_connections.items():
        to_name, to_pos = to_conn
        from_names, from_positions = zip(*from_conns)
        from_pos = max(set(from_positions), key=from_positions.count)
        names = from_names + (to_name,)
        items = [new["items"][name] for name in names]
        x = sum(item["x"] for item in items) / len(items)
        y = sum(item["y"] for item in items) / len(items)
        merger_name = f"{to_name} merger"
        new["items"][merger_name] = {
            "type": "Merger",
            "description": f"Merges data into {to_name}",
            "x": x,
            "y": y,
            "cancel_on_error": new["items"][to_name].pop("cancel_on_error", False),
        }
        for from_name in from_names:
            new["project"]["connections"].append({"from": [from_name, from_pos], "to": [merger_name, to_pos]})
        new["project"]["connections"].append({"from": [merger_name, "right"], "to": list(to_conn)})
    for conn in to_remove:
        new["project"]["connections"].remove(conn)
    return new


def upgrade_v7_to_v8(old):
    """Upgrades version 7 project dictionary to version 8.

    Changes:
        1. Move purge settings from items to their outgoing connections.

    Args:
        old (dict): Version 7 project dictionary

    Returns:
        dict: Version 8 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 8
    purge_options_by_name = {}
    for name, item_dict in new["items"].items():
        if item_dict.get("purge_before_writing", False):
            purge_options_by_name[name] = {
                "purge_before_writing": True,
                "purge_settings": item_dict.get("purge_settings"),
            }
    for conn in new["project"]["connections"]:
        from_name, _ = conn["from"]
        purge_options = purge_options_by_name.get(from_name)
        if purge_options is not None:
            conn.setdefault("options", {}).update(purge_options)
    return new


def upgrade_v8_to_v9(old):
    """Upgrades version 8 project dictionary to version 9.

    Changes:
        1. Remove ["project"]["name"] key

    Args:
        old (dict): Version 8 project dictionary

    Returns:
        dict: Version 9 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 9
    try:
        new["project"].pop("name")
    except KeyError:
        pass
    return new


def upgrade_v9_to_v10(old):
    """Upgrades version 9 project dictionary to version 10.

    Changes:
        1. Remove connections from Gimlets and GdxExporters
        2. Remove Gimlet and GdxExporter items

    Args:
        old (dict): Version 9 project dictionary

    Returns:
        dict: Version 10 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 10
    names_to_remove = list()  # Gimlet and GdxExporter item names
    # Get Gimlet and GdxExporter names and remove connections
    for name, item_dict in new["items"].items():
        if item_dict["type"] in ["Gimlet", "GdxExporter"]:
            names_to_remove.append(name)
    # Get list of connections to remove
    connections_to_remove = list()
    for conn in new["project"]["connections"]:
        for name_to_remove in names_to_remove:
            if name_to_remove in conn["from"] or name_to_remove in conn["to"]:
                connections_to_remove.append(conn)
    for conn_to_remove in connections_to_remove:
        new["project"]["connections"].remove(conn_to_remove)
    # Remove Gimlet and GdxExporter item dictionaries
    for name in names_to_remove:
        new["items"].pop(name)
    return new


def upgrade_v10_to_v11(old, items_module):
    """Upgrades version 10 project dictionary to version 11.

    Changes:
        1. Add project item package info field
        2. Move specifications and project items under package names

    Args:
        old (dict): Version 9 project dictionary
        items_module (module): project items module

    Returns:
        dict: Version 10 project dictionary
    """
    new = copy.deepcopy(old)
    new["project"]["version"] = 11
    new["project"]["project_item_packages"] = {items_module.__name__: {"version": items_module.LATEST_PROJECT_DICT_ITEMS_VERSION}}
    new["project"]["specifications"] = {items_module.__name__: new["project"].pop("specifications")}
    new["items"] = {items_module.__name__: new["items"]}
    return new


def _make_unique_importer_specification_name(importer_name, label, k):
    return f"{importer_name} - {os.path.basename(label['path'])} - {k}"


def is_valid(project_dict, version):
    """Checks given project dict if it is valid for given version.

    Args:
        project_dict (dict): Project dictionary
        version (int): Version
    """
    if version == 1:
        _is_valid_v1(project_dict)
    elif 2 <= version <= 8:
        _is_valid_v2_to_v8(project_dict, version)
    elif 9 <= version <= 10:
        _is_valid_v9_to_v10(project_dict)
    else:
        raise NotImplementedError(f"No validity check available for version {version}")


def _is_valid_v1(project_dict):
    """Checks that the given project JSON dictionary contains a valid version 1 Spine Toolbox project.

    Valid meaning, that it contains all required keys and values are of the correct type.

    Args:
        project_dict (dict): Project dictionary
    """
    if "project" not in project_dict.keys():
        raise ProjectUpgradeFailed("Invalid project.json file. Key 'project' not found.")
    if "objects" not in project_dict.keys():
        raise ProjectUpgradeFailed("Invalid project.json file. Key 'objects' not found.")
    required_project_keys = ["version", "name", "description", "tool_specifications", "connections"]
    project = project_dict["project"]
    objects = project_dict["objects"]
    if not isinstance(project, dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'project' must be a dict.")
    if not isinstance(objects, dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'objects' must be a dict.")
    for req_key in required_project_keys:
        if req_key not in project:
            raise ProjectUpgradeFailed("Invalid project.json file. Key {0} not found.".format(req_key))
    if not project["version"] == 1:
        raise ProjectUpgradeFailed("Invalid project version")
    if not isinstance(project["name"], str) or not isinstance(project["description"], str):
        raise ProjectUpgradeFailed("Invalid project.json file. 'name' and 'description' must be strings.")
    if not isinstance(project["tool_specifications"], list):
        raise ProjectUpgradeFailed("Invalid project.json file. 'tool_specifications' must be a list.")
    if not isinstance(project["connections"], list):
        raise ProjectUpgradeFailed("Invalid project.json file. 'connections' must be a list.")


def _is_valid_v2_to_v8(project_dict, version):
    """Checks that the given project JSON dictionary contains a valid version 2 to 8 Spine Toolbox project.

    Valid meaning, that it contains all required keys and values are of the correct type.

    Args:
        project_dict (dict): Project dictionary
        version (int): Version
    """
    if "project" not in project_dict.keys():
        raise ProjectUpgradeFailed("Invalid project.json file. Key 'project' not found.")
    if "items" not in project_dict.keys():
        raise ProjectUpgradeFailed("Invalid project.json file. Key 'items' not found.")
    required_project_keys = ["version", "name", "description", "specifications", "connections"]
    project = project_dict["project"]
    items = project_dict["items"]
    if not isinstance(project, dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'project' must be a dict.")
    if not isinstance(items, dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'items' must be a dict.")
    for req_key in required_project_keys:
        if req_key not in project:
            raise ProjectUpgradeFailed("Invalid project.json file. Key {0} not found.".format(req_key))
    if not project["version"] == version:
        raise ProjectUpgradeFailed("Invalid project version:'{0}'".format(project["version"]))
    if not isinstance(project["name"], str) or not isinstance(project["description"], str):
        raise ProjectUpgradeFailed("Invalid project.json file. 'name' and 'description' must be strings.")
    if not isinstance(project["specifications"], dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'specifications' must be a dictionary.")
    if not isinstance(project["connections"], list):
        raise ProjectUpgradeFailed("Invalid project.json file. 'connections' must be a list.")


def _is_valid_v9_to_v10(project_dict):
    """Checks that the given project JSON dictionary contains a valid version 9 or 10 Spine Toolbox project.
     
    Valid meaning, that it contains all required keys and values are of the correct type.

    Args:
        project_dict (dict): Project dictionary
    """
    if "project" not in project_dict.keys():
        raise ProjectUpgradeFailed("Invalid project.json file. Key 'project' not found.")
    if "items" not in project_dict.keys():
        raise ProjectUpgradeFailed("Invalid project.json file. Key 'items' not found.")
    required_project_keys = ["version", "description", "specifications", "connections"]
    project = project_dict["project"]
    items = project_dict["items"]
    if not isinstance(project, dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'project' must be a dict.")
    if not isinstance(items, dict):
        raise ProjectUpgradeFailed("Invalid project.json file. 'items' must be a dict.")
    for req_key in required_project_keys:
        if req_key not in project:
            raise ProjectUpgradeFailed("Invalid project.json file. Key {0} not found.".format(req_key))


def _fix_1d_array_to_array(mappings):
    """
    Replaces '1d array' with 'array' for parameter type in Importer mappings.

    With spinedb_api >= 0.3, '1d array' parameter type was replaced by 'array'.
    Other settings in a mapping are backwards compatible except the name.

    Args:
        mappings (dict): import mapping dictionary
    """
    for more_mappings in mappings:
        for settings in more_mappings:
            table_mappings = settings.get("table_mappings")
            if table_mappings is None:
                continue
            for sheet_settings in table_mappings.values():
                for setting in sheet_settings:
                    parameter_setting = setting.get("parameters")
                    if parameter_setting is None:
                        continue
                    parameter_type = parameter_setting.get("parameter_type")
                    if parameter_type == "1d array":
                        parameter_setting["parameter_type"] = "array"
