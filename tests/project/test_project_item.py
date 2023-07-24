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
"""This module contains unit tests for the project_item module."""
import pathlib
import tempfile
import unittest

from spine_engine.project.project import Project
from spine_engine.project.project_item import LOGS_DIR_NAME, ProjectItem, SpecificationSupportingProjectItem
from spine_engine.project.project_item_specification import ProjectItemSpecification
from spine_engine.utils.helpers import shorten
from tests.helpers import import_test_items_module


class TestProjectItem(unittest.TestCase):

    def test_item_type(self):
        self.assertEqual(ProjectItem.item_type(), "ProjectItem")

    def test_is_memory_only(self):
        item = ProjectItem("Initially in-memory item")
        self.assertTrue(item.is_memory_only)
        with tempfile.TemporaryDirectory() as items_dir:
            item.tie_to_disk("item's name", items_dir)
            self.assertFalse(item.is_memory_only)

    def test_set_project_in_memory_for_item_in_memory(self):
        item = ProjectItem("")
        self.assertIsNone(item.project)
        project = Project()
        item.set_project(project)
        self.assertIs(item.project, project)
        self.assertTrue(item.is_memory_only)

    def test_set_project_on_disk_for_item_in_memory(self):
        item = ProjectItem("")
        self.assertIsNone(item.project)
        project = Project()
        with tempfile.TemporaryDirectory() as temp_dir:
            project.tie_to_disk(temp_dir)
            self.assertFalse(project.is_memory_only)
            item.set_project(project)
            self.assertIs(item.project, project)
            self.assertFalse(item.is_memory_only)
            expected_data_dir = Path(temp_dir) / ".spinetoolbox" / "items" / ""
            self.assertEqual(item.data_dir, )

    def test_tie_to_disk(self):
        item = ProjectItem("Soon to be physical")
        with tempfile.TemporaryDirectory() as items_dir:
            name = "My lovely test item"
            item.tie_to_disk(name, items_dir)
            self.assertFalse(item.is_memory_only)
            data_dir = pathlib.Path(items_dir) / shorten(name)
            self.assertTrue(data_dir.exists())
            logs_dir = data_dir / LOGS_DIR_NAME
            self.assertTrue(logs_dir.exists())

    def test_serialization_without_project_dir(self):
        with import_test_items_module() as items_module:
            item_classes = items_module.PROJECT_ITEM_CLASSES
        item = item_classes["Test Project Item"]("For testing purposes only.")
        item_dict = item.to_dict()
        deserialized = item_classes["Test Project Item"].from_dict(item_dict, None, [])
        self.assertEqual(deserialized.description, item.description)


class TestSpecificationSupportingProjectItem(unittest.TestCase):

    def test_set_get_specification(self):
        specification = ProjectItemSpecification("my specification", "Test specification.")
        item = SpecificationSupportingProjectItem("For testing purposes.", specification)
        item.set_specification(specification)
        self.assertEqual(item.get_specification(), specification)

    def test_serialization(self):
        with import_test_items_module() as items_module:
            item_classes = items_module.PROJECT_ITEM_CLASSES
        specification = ProjectItemSpecification("Bestest Specification", "But its for testing only.")
        item = item_classes["Test Project Item with Specification"]("For testing purposes only.", specification)
        item.set_specification(specification)
        item_dict = item.to_dict()
        deserialized = item_classes["Test Project Item with Specification"].from_dict(item_dict, None, [specification])
        self.assertEqual(deserialized.description, item.description)
        self.assertIs(deserialized.get_specification(), specification)


if __name__ == '__main__':
    unittest.main()
