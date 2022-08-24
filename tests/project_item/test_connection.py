######################################################################################################################
# Copyright (C) 2017-2021 Spine project consortium
# This file is part of Spine Engine.
# Spine Engine is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################
"""
Uni tests for the ``connection`` module.

:authors: A. Soininen (VTT)
:date:    18.2.2021
"""
import os.path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock
from spinedb_api import DatabaseMapping, import_scenarios, import_tools
from spine_engine.project_item.connection import Connection, Jump
from spine_engine.project_item.project_item_resource import database_resource


class TestConnection(unittest.TestCase):
    def test_serialization_without_filters(self):
        connection = Connection("source", "bottom", "destination", "top", {"option": 23})
        connection_dict = connection.to_dict()
        restored = Connection.from_dict(connection_dict)
        self.assertEqual(restored.source, "source")
        self.assertEqual(restored.source_position, "bottom")
        self.assertEqual(restored.destination, "destination")
        self.assertEqual(restored.destination_position, "top")
        self.assertEqual(restored.options, {"option": 23})


class TestConnectionWithDatabase(unittest.TestCase):
    def setUp(self):
        self._temp_dir = TemporaryDirectory()
        self._url = "sqlite:///" + os.path.join(self._temp_dir.name, "db.sqlite")
        self._db_map = DatabaseMapping(self._url, create=True)

    def tearDown(self):
        self._db_map.connection.close()
        self._temp_dir.cleanup()

    def test_serialization_with_filters(self):
        import_scenarios(self._db_map, ("my_scenario",))
        self._db_map.commit_session("Add test data.")
        disabled_filters = {"my_database": {"scenario_filter": ["my_scenario"]}}
        connection = Connection("source", "bottom", "destination", "top", disabled_filter_names=disabled_filters)
        connection.receive_resources_from_source([database_resource("unit_test", self._url, "my_database")])
        connection_dict = connection.to_dict()
        restored = Connection.from_dict(connection_dict)
        self.assertEqual(restored.source, "source")
        self.assertEqual(restored.source_position, "bottom")
        self.assertEqual(restored.destination, "destination")
        self.assertEqual(restored.destination_position, "top")
        self.assertEqual(restored.options, {})
        self.assertEqual(restored._disabled_filter_names, {"my_database": {"scenario_filter": {"my_scenario"}}})

    def test_enabled_scenarios(self):
        import_scenarios(self._db_map, ("scenario_1", "scenario_2"))
        self._db_map.commit_session("Add test data.")
        disabled_filters = {"my_database": {"scenario_filter": {"scenario_1"}}}
        connection = Connection("source", "bottom", "destination", "top", disabled_filter_names=disabled_filters)
        resources = [database_resource("unit_test", self._url, "my_database")]
        connection.receive_resources_from_source(resources)
        self.assertEqual(connection.enabled_filters("my_database"), {"scenario_filter": ["scenario_2"]})

    def test_enabled_tools(self):
        import_tools(self._db_map, ("tool_1", "tool_2"))
        self._db_map.commit_session("Add test data.")
        disabled_filters = {"my_database": {"tool_filter": {"tool_1"}}}
        connection = Connection("source", "bottom", "destination", "top", disabled_filter_names=disabled_filters)
        resources = [database_resource("unit_test", self._url, "my_database")]
        connection.receive_resources_from_source(resources)
        self.assertEqual(connection.enabled_filters("my_database"), {"tool_filter": ["tool_2"]})


class TestJump(unittest.TestCase):
    def test_default_condition_prevents_jump(self):
        jump = Jump("source", "bottom", "destination", "top")
        self.assertFalse(jump.is_condition_true(1))

    def test_empty_condition_prevents_jump(self):
        jump = Jump("source", "bottom", "destination", "top", "")
        self.assertFalse(jump.is_condition_true(1))

    def test_counter_passed_to_condition(self):
        condition = "\n".join(("import sys", "counter = int(sys.argv[1])", "exit(0 if counter == 23 else 1)"))
        jump = Jump("source", "bottom", "destination", "top", condition)
        jump.make_logger(Mock())
        self.assertTrue(jump.is_condition_true(23))

    def test_dictionary(self):
        jump = Jump("source", "bottom", "destination", "top", "exit(23)")
        jump_dict = jump.to_dict()
        new_jump = Jump.from_dict(jump_dict)
        self.assertEqual(new_jump.source, jump.source)
        self.assertEqual(new_jump.destination, jump.destination)
        self.assertEqual(new_jump.source_position, jump.source_position)
        self.assertEqual(new_jump.destination_position, jump.destination_position)
        self.assertEqual(new_jump.condition, jump.condition)


if __name__ == "__main__":
    unittest.main()
