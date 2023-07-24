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
"""This module contains unit tests for the project module."""
import pathlib
import tempfile
import unittest

from spine_engine.project.connection import Connection
from spine_engine.project.project import Project
from spine_engine.project.project_item import ProjectItem, SpecificationSupportingProjectItem
from spine_engine.exception import (
    DuplicateName,
    DuplicateShortName,
    InvalidConnection,
    InvalidJump,
    NameContainsInvalidCharacters,
    ProjectComponentNotFound,
)
from spine_engine.project.project_item_specification import ProjectItemSpecification
from spine_engine.project.project_settings import ProjectSettings
from spine_engine.utils.helpers import shorten

from tests.helpers import import_test_items_module


class TestProject(unittest.TestCase):
    def test_is_virtual(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertTrue(project.is_memory_only)
        with tempfile.TemporaryDirectory() as base_dir:
            project.tie_to_disk(base_dir)
            self.assertFalse(project.is_memory_only)

    def test_make_physical(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as base_dir:
            project.tie_to_disk(base_dir)
            project_dir = pathlib.Path(base_dir) / shorten(project.name)
            self.assertEqual(project.project_dir, project_dir)
            self.assertTrue(project_dir.exists())
            items_dir = project_dir / ".spinetoolbox" / "items"
            self.assertTrue(items_dir.exists())

    def test_add_node_raises_when_duplicate_names(self):
        project = Project("Test project", "For testing purposes.", None)
        project.add_node("Node", item=ProjectItem(""))
        self.assertRaises(DuplicateName, project.add_node, "Node")

    def test_add_node_raises_when_duplicate_short_names(self):
        project = Project("Test project", "For testing purposes.", None)
        project.add_node("node", item=ProjectItem(""))
        self.assertRaises(DuplicateShortName, project.add_node, "Node")

    def test_add_node_raises_when_name_contains_invalid_characters(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(NameContainsInvalidCharacters, project.add_node, "Test\\item")

    def test_rename_node(self):
        project = Project("Test project", "For testing purposes.", None)
        with import_test_items_module() as items_package:
            item = items_package.PROJECT_ITEM_CLASSES["Test Project Item"]("Test project item.")
        project.add_node("Node", item=item)
        project.rename_node("Node", "Brave new name")
        self.assertEqual(list(project.nodes), ["Brave new name"])
        self.assertIs(project.nodes["Brave new name"]["item"], item)

    def test_rename_node_fails_if_name_is_not_found(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(ProjectComponentNotFound, project.rename_node, "nonsense", "Brave new name")

    def test_rename_node_fails_if_new_name_exists(self):
        project = Project("Test project", "For testing purposes.", None)
        project.add_node("Node to rename", item=ProjectItem(""))
        project.add_node("Clashing name", item=ProjectItem(""))
        self.assertRaises(DuplicateName, project.rename_node, "Node to rename", "Clashing name")

    def test_rename_node_fails_if_short_new_name_exists(self):
        project = Project("Test project", "For testing purposes.", None)
        project.add_node("Node to rename", item=ProjectItem(""))
        project.add_node("clashing name", item=ProjectItem(""))
        self.assertRaises(DuplicateShortName, project.rename_node, "Node to rename", "Clashing name")

    def test_rename_node_updates_connections_as_well(self):
        project = Project("Test project", "", None)
        flow_start = ProjectItem("First node in the DAG.")
        project.add_node("Flow start", item=flow_start)
        item_to_rename = ProjectItem("Second node in the DAG.")
        project.add_node("Item to rename", item=item_to_rename)
        flow_end = ProjectItem("Last node in the DAG.")
        project.add_node("Flow end", item=flow_end)
        connection1 = Connection({"use_datapackage": True})
        project.add_edge("Flow start", "Item to rename", connection=connection1)
        connection2 = Connection({"use_memory_db": True})
        project.add_edge("Item to rename", "Flow end", connection=connection2)
        project.rename_node("Item to rename", "Renamed")
        self.assertIs(project.nodes["Renamed"]["item"], item_to_rename)
        self.assertIs(project.edges["Flow start", "Renamed"]["connection"], connection1)
        self.assertIs(project.edges["Renamed", "Flow end"]["connection"], connection2)

    def test_rename_node_updates_jump_destination_as_well(self):
        project = Project("Test project", "", None)
        item_to_rename = ProjectItem("")
        project.add_node("Flow start", item=item_to_rename)
        flow_end = ProjectItem("")
        project.add_node("Flow end", item=flow_end)
        connection = Connection({})
        project.add_edge("Flow start", "Flow end", connection=connection)
        jump = project.make_jump("Flow end", "Flow start")
        project.rename_node("Flow start", "Renamed")
        self.assertIs(project.get_jump("Flow end", "Renamed"), jump)
        self.assertEqual(jump.destination, "Renamed")

    def test_rename_node_updates_jump_source_as_well(self):
        project = Project("Test project", "", None)
        flow_start = ProjectItem("First node in the DAG.")
        project.add_node("Flow start", item=flow_start)
        item_to_rename = ProjectItem("Last node in the DAG.")
        project.add_node("Flow end", item=item_to_rename)
        project.add_edge("Flow start", "Flow end")
        jump = project.make_jump("Flow end", "Flow start")
        project.rename_node("Flow end", "Renamed")
        self.assertIs(project.get_jump("Renamed", "Flow start"), jump)
        self.assertEqual(jump.source, "Renamed")

    def test_rename_node_updates_self_jumps_source_and_destination(self):
        project = Project("Test project", "", None)
        item_to_rename = ProjectItem("A sole node in the DAG.")
        project.add_node("Flow start and end", item=item_to_rename)
        jump = project.make_jump("Flow start and end", "Flow start and end")
        project.rename_node("Flow start and end", "Renamed")
        self.assertIs(project.get_jump("Renamed", "Renamed"), jump)
        self.assertEqual(jump.source, "Renamed")

    def test_remove_node_raises_when_node_is_not_found(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(ProjectComponentNotFound, project.remove_node, "non-existent")

    def test_removing_node_removes_jump_originating_from_it(self):
        project = Project("Test project", "For testing purposes.", None)
        start_item = ProjectItem("")
        project.add_node("Flow start", item=start_item)
        end_item = ProjectItem("A thing that should not be.")
        project.add_node("Item to remove", item=end_item)
        connection = Connection(None, None)
        project.add_edge("Flow start", "Item to remove", connection=connection)
        jump = project.make_jump("Item to remove", "Flow start")
        self.assertIs(project.get_jump("Item to remove", "Flow start"), jump)
        project.remove_node("Item to remove")
        self.assertRaises(ProjectComponentNotFound, project.get_jump, "Item to remove", "Flow start")

    def test_removing_node_removes_jump_targeting_it(self):
        project = Project("Test project", "For testing purposes.", None)
        start_item = ProjectItem("")
        project.add_node("Item to remove", item=start_item)
        end_item = ProjectItem("")
        project.add_node("Flow end", item=end_item)
        project.add_edge("Item to remove", "Flow end")
        jump = project.make_jump("Flow end", "Item to remove")
        self.assertIs(
            project.get_jump(
                "Flow end",
                "Item to remove",
            ),
            jump,
        )
        project.remove_node("Item to remove")
        self.assertRaises(ProjectComponentNotFound, project.get_jump, "Flow end", "Item to remove")

    def test_add_edge_fails_if_source_or_destination_dont_exist(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(ProjectComponentNotFound, project.add_edge, "nonexistent", "another one")
        project.add_node("Node", item=ProjectItem(""))
        self.assertRaises(ProjectComponentNotFound, project.add_edge, "Node", "nonexistent")

    def test_adding_edge_back_to_same_item_fails(self):
        project = Project("Test project", "For testing purposes.", None)
        item = ProjectItem("")
        project.add_node("Source and destination", item=item)
        self.assertRaises(InvalidConnection, project.add_edge, "Source and destination", "Source and destination")

    def test_add_edge_fails_if_it_would_invalidate_dag(self):
        project = Project("Test project", "For testing purposes.", None)
        start_item = ProjectItem("")
        project.add_node("Flow start", item=start_item)
        end_item = ProjectItem("")
        project.add_node("Flow end", item=end_item)
        project.add_edge("Flow start", "Flow end")
        self.assertRaises(InvalidConnection, project.add_edge, "Flow end", "Flow start")

    def test_remove_edge(self):
        project = Project("Test project", "For testing purposes.", None)
        source_item = ProjectItem("Just a test item.")
        project.add_node("Source", item=source_item)
        destination_item = ProjectItem("Just a test item.")
        project.add_node("Destination", item=destination_item)
        project.add_edge("Source", "Destination")
        project.remove_edge("Source", "Destination")
        self.assertNotIn(("Source", "Destination"), project.edges)

    def test_remove_edge_fails_when_connection_is_not_found(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(ProjectComponentNotFound, project.remove_edge, "Source", "Destination")

    def test_remove_edge_fails_when_it_invalidates_jump(self):
        project = Project("Test project", "For testing purposes.", None)
        source_item = ProjectItem("Just a test item.")
        project.add_node("Source", item=source_item)
        destination_item = ProjectItem("Just a test item.")
        project.add_node("Destination", item=destination_item)
        connection = Connection({"write_index": 23})
        project.add_edge("Source", "Destination", connection=connection)
        project.make_jump("Destination", "Source")
        self.assertRaises(InvalidJump, project.remove_edge, "Source", "Destination")
        self.assertIs(project.edges["Source", "Destination"]["connection"], connection)

    def test_jump(self):
        project = Project("Test project", "For testing purposes.", None)
        item = ProjectItem("")
        project.add_node("Test item", item=item)
        jump = project.make_jump("Test item", "Test item")
        self.assertIs(jump, project.get_jump("Test item", "Test item"))

    def test_jump_fails_if_it_is_invalid(self):
        project = Project("Test project", "For testing purposes.", None)
        start_item = ProjectItem("")
        project.add_node("Flow start", item=start_item)
        end_item = ProjectItem("")
        project.add_node("Flow end", item=end_item)
        project.add_edge("Flow start", "Flow end")
        self.assertRaises(InvalidJump, project.make_jump, "Flow start", "Flow end")

    def test_get_jump(self):
        project = Project("Test project", "For testing purposes.", None)
        item = ProjectItem("")
        project.add_node("Test item", item=item)
        jump = project.make_jump("Test item", "Test item")
        self.assertIs(jump, project.get_jump("Test item", "Test item"))

    def test_get_jump_fails_if_jump_does_not_exist(self):
        project = Project("Test project", "For testing purposes.", None)
        item = ProjectItem("")
        project.add_node("Test item", item=item)
        project.make_jump("Test item", "Test item")
        self.assertRaises(ProjectComponentNotFound, project.get_jump, "Test item", "nonsense")
        self.assertRaises(ProjectComponentNotFound, project.get_jump, "nonsense", "Test item")

    def test_add_specification(self):
        project = Project("Test project", "For testing purposes.", None)
        with import_test_items_module() as items_module:
            specification = items_module.PROJECT_ITEM_CLASSES[
                "Test Project Item with Specification"
            ].make_specification("Test Specification", "For testing purposes.")
        project.add_specification(specification)
        self.assertIs(project.get_specification("Test Specification"), specification)

    def test_add_specification_fails_in_case_of_duplicate_specification_name(self):
        project = Project("Test project", "For testing purposes.", None)
        with import_test_items_module() as items_module:
            specification1 = items_module.PROJECT_ITEM_CLASSES[
                "Test Project Item with Specification"
            ].make_specification("Test Specification", "For testing purposes.")
            specification2 = items_module.PROJECT_ITEM_CLASSES[
                "Test Project Item with Specification"
            ].make_specification("Test Specification", "For testing purposes.")
        project.add_specification(specification1)
        self.assertRaises(DuplicateName, project.add_specification, specification2)

    def test_get_specification_fails_when_specification_cannot_be_found(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(ProjectComponentNotFound, project.get_specification, "Non-existing")

    def test_get_specifications(self):
        project = Project("Test project", "For testing purposes.", None)
        specification = ProjectItemSpecification("Test Specification", "For testing purposes.")
        project.add_specification(specification)
        self.assertEqual(list(project.specifications()), [specification])

    def test_remove_specification(self):
        project = Project("Test project", "For testing purposes.", None)
        specification = ProjectItemSpecification("Test Specification", "For testing purposes.")
        project.add_specification(specification)
        project.remove_specification("Test Specification")
        self.assertEqual(list(project.specifications()), [])

    def test_remove_specification_removes_it_from_item_too(self):
        project = Project("Test project", "For testing purposes.", None)
        specification = ProjectItemSpecification("Test Specification", "For testing purposes.")
        project.add_specification(specification)
        item = SpecificationSupportingProjectItem("", specification)
        project.add_node("Test item", item=item)
        project.remove_specification("Test Specification")
        self.assertEqual(list(project.specifications()), [])
        self.assertIsNone(project.nodes["Test item"]["item"].get_specification())

    def test_remove_specification_fails_when_specification_does_not_exist(self):
        project = Project("Test project", "For testing purposes.", None)
        self.assertRaises(ProjectComponentNotFound, project.remove_specification, "nonsense")

    def test_serialization_with_empty_project(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir:
            project.tie_to_disk(temp_dir)
            project_dict = project.to_dict({})
            deserialized = Project.from_dict(project_dict, project.project_dir, {}, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)

    def test_serialization_with_settings(self):
        settings = ProjectSettings(enable_execute_all=False)
        project = Project("Test project", "For testing purposes.", settings)
        with tempfile.TemporaryDirectory() as temp_dir:
            project.tie_to_disk(temp_dir)
            project_dict = project.to_dict({})
            deserialized = Project.from_dict(project_dict, project.project_dir, {}, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)

    def test_serialization_with_project_item(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir, import_test_items_module() as items_module:
            item = items_module.test_item.project_item.TestProjectItem("For testing purposes.")
            project.add_node("Named item", item=item)
            item_packages = {items_module.__name__: items_module}
            project.tie_to_disk(temp_dir)
            project_dict = project.to_dict(item_packages)
            deserialized = Project.from_dict(project_dict, project.project_dir, item_packages, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)
            deserialized_names = list(deserialized.nodes)
            deserialized_items = list(deserialized.nodes.values())
            self.assertEqual(len(deserialized_items), 1)
            self.assertEqual(deserialized_names[0], "Named item")
            self.assertEqual(deserialized_items[0]["item"].description, "For testing purposes.")

    def test_serialization_with_specification(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir, import_test_items_module() as items_module:
            specification = items_module.PROJECT_ITEM_CLASSES[
                "Test Project Item with Specification"
            ].make_specification("Test Specification", "For testing purposes.")
            project.add_specification(specification)
            project.tie_to_disk(temp_dir)
            item_packages = {items_module.__name__: items_module}
            project_dict = project.to_dict(item_packages)
            deserialized = Project.from_dict(project_dict, project.project_dir, item_packages, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)
            deserialized_specifications = list(deserialized.specifications())
            self.assertEqual(len(deserialized_specifications), 1)
            self.assertEqual(deserialized_specifications[0].name, specification.name)
            self.assertEqual(deserialized_specifications[0].description, specification.description)
            expected_specification_file = (
                pathlib.Path(temp_dir)
                / shorten(deserialized.name)
                / ".spinetoolbox"
                / "specifications"
                / "test_specification.json"
            )
            self.assertEqual(deserialized_specifications[0].get_file_path(), expected_specification_file)

    def test_deserialization_links_project_item_with_specification(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir, import_test_items_module() as items_module:
            specification = items_module.PROJECT_ITEM_CLASSES[
                "Test Project Item with Specification"
            ].make_specification("Test Specification", "For testing purposes.")
            project.add_specification(specification)
            item = items_module.test_item_with_specification.project_item.TestSpecificationProjectItem(
                "For testing purposes.", specification
            )
            project.add_node("Named item", item=item)
            project.tie_to_disk(temp_dir)
            item_packages = {items_module.__name__: items_module}
            project_dict = project.to_dict(item_packages)
            deserialized = Project.from_dict(project_dict, project.project_dir, item_packages, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)
            deserialized_specifications = list(deserialized.specifications())
            self.assertEqual(len(deserialized_specifications), 1)
            self.assertEqual(deserialized_specifications[0].name, specification.name)
            self.assertEqual(deserialized_specifications[0].description, specification.description)
            expected_specification_file = (
                pathlib.Path(temp_dir)
                / shorten(deserialized.name)
                / ".spinetoolbox"
                / "specifications"
                / "test_specification.json"
            )
            self.assertEqual(deserialized_specifications[0].get_file_path(), expected_specification_file)
            deserialized_names = list(deserialized.nodes)
            deserialized_items = list(deserialized.nodes.values())
            self.assertEqual(len(deserialized_names), 1)
            self.assertEqual(deserialized_names[0], "Named item")
            self.assertEqual(len(deserialized_items), 1)
            self.assertEqual(deserialized_items[0]["item"].description, "For testing purposes.")
            self.assertIs(deserialized_items[0]["item"].get_specification(), deserialized_specifications[0])

    def test_serialization_with_item_that_uses_plugin_specification(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir, import_test_items_module() as items_module:
            specification = items_module.PROJECT_ITEM_CLASSES[
                "Test Project Item with Specification"
            ].make_specification("Plugin specification", "For testing purposes.")
            specification.set_plugin_name("Test plugin")
            plugin_dir = pathlib.Path(temp_dir) / "plugins"
            plugin_dir.mkdir()
            plugin_file = plugin_dir / "plugin_specification.json"
            specification.save_on_disk(plugin_file)
            plugins = [specification]
            project.add_specification(specification)
            item = items_module.test_item_with_specification.project_item.TestSpecificationProjectItem(
                "For testing purposes.", specification=specification
            )
            project.add_node("Named item", item=item)
            project.tie_to_disk(temp_dir)
            item_packages = {items_module.__name__: items_module}
            project_dict = project.to_dict(item_packages)
            self.assertEqual(project_dict["specifications"], {})
            deserialized = Project.from_dict(project_dict, project.project_dir, item_packages, plugins)
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)
            deserialized_specifications = list(deserialized.specifications())
            self.assertEqual(len(deserialized_specifications), 1)
            self.assertEqual(deserialized_specifications[0].name, specification.name)
            self.assertEqual(deserialized_specifications[0].description, specification.description)
            self.assertEqual(deserialized_specifications[0].get_plugin_name(), "Test plugin")
            expected_specification_file = pathlib.Path(temp_dir) / "plugins" / "plugin_specification.json"
            self.assertEqual(deserialized_specifications[0].get_file_path(), expected_specification_file)
            item_names = list(deserialized.nodes)
            deserialized_items = list(deserialized.nodes.values())
            self.assertEqual(len(deserialized_items), 1)
            self.assertEqual(item_names[0], "Named item")
            self.assertEqual(deserialized_items[0]["item"].description, "For testing purposes.")
            self.assertIs(deserialized_items[0]["item"].get_specification(), deserialized_specifications[0])

    def test_serialization_with_connection(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir, import_test_items_module() as items_module:
            source_item = items_module.test_item.project_item.TestProjectItem("Source.")
            project.add_node("Source item", item=source_item)
            destination_item = items_module.test_item.project_item.TestProjectItem("Sink.")
            project.add_node("Destination item", item=destination_item)
            connection = Connection({"purge_settings": {"entity_scenario": True}})
            project.add_edge("Source item", "Destination item", connection=connection)
            project.tie_to_disk(temp_dir)
            item_packages = {items_module.__name__: items_module}
            project_dict = project.to_dict(item_packages)
            deserialized = Project.from_dict(project_dict, project.project_dir, item_packages, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)
            self.assertEqual(len(deserialized.nodes), 2)
            self.assertEqual(deserialized.nodes["Source item"]["item"].description, "Source.")
            self.assertEqual(deserialized.nodes["Destination item"]["item"].description, "Sink.")
            deserialized_connection = deserialized.edges["Source item", "Destination item"]["connection"]
            self.assertEqual(deserialized_connection, connection)

    def test_serialization_with_jump(self):
        project = Project("Test project", "For testing purposes.", None)
        with tempfile.TemporaryDirectory() as temp_dir, import_test_items_module() as items_module:
            source_item = items_module.test_item.project_item.TestProjectItem("Source.")
            project.add_node("Source item", item=source_item)
            destination_item = items_module.test_item.project_item.TestProjectItem("Sink.")
            project.add_node("Destination item", item=destination_item)
            connection = Connection(None, None)
            project.add_edge("Source item", "Destination item", connection=connection)
            jump = project.make_jump("Destination item", "Source item")
            project.tie_to_disk(temp_dir)
            item_packages = {items_module.__name__: items_module}
            project_dict = project.to_dict(item_packages)
            deserialized = Project.from_dict(project_dict, project.project_dir, item_packages, [])
            self.assertEqual(deserialized.name, project.name)
            self.assertEqual(deserialized.description, project.description)
            self.assertEqual(deserialized.settings, project.settings)
            self.assertEqual(len(deserialized.nodes), 2)
            self.assertEqual(deserialized.nodes["Source item"]["item"].description, "Source.")
            self.assertEqual(deserialized.nodes["Destination item"]["item"].description, "Sink.")
            self.assertEqual(deserialized.edges["Source item", "Destination item"]["connection"], connection)
            deserialized_jump = deserialized.get_jump("Destination item", "Source item")
            self.assertEqual(deserialized_jump.source, jump.source)
            self.assertEqual(deserialized_jump.destination, jump.destination)


if __name__ == '__main__':
    unittest.main()
