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
import pathlib
from tempfile import TemporaryDirectory
import unittest

from spine_engine.project.connection import Connection, FilterSettings
from spine_engine.project_item.project_item_resource import database_resource, file_resource
from spine_engine.utils.helpers import PartCount
from spinedb_api.filters.scenario_filter import SCENARIO_FILTER_TYPE


class TestConnection(unittest.TestCase):
    def test_option_defaults(self):
        connection = Connection()
        self.assertFalse(connection.use_datapackage)
        self.assertFalse(connection.use_memory_db)
        self.assertFalse(connection.purge_before_writing)
        self.assertIsNone(connection.purge_settings)
        self.assertEqual(connection.write_index, 1)
        self.assertFalse(connection.require_filter_online(SCENARIO_FILTER_TYPE))

    def test_notifications(self):
        connection = Connection()
        self.assertEqual(connection.notifications(), [])

    def test_serialization_with_options(self):
        options = {
            "use_datapackage": True,
            "use_memory_db": True,
            "purge_before_writing": True,
            "purge_settings": {"entities": True},
            "write_index": 23,
            "require_" + SCENARIO_FILTER_TYPE: True,
        }
        connection = Connection(options)
        connection_dict = connection.to_dict()
        restored = Connection.from_dict(connection_dict)
        self.assertTrue(restored.use_datapackage)
        self.assertTrue(restored.use_memory_db)
        self.assertTrue(restored.purge_before_writing)
        self.assertEqual(restored.purge_settings, {"entities": True})
        self.assertEqual(restored.write_index, 23)
        self.assertTrue(restored.require_filter_online(SCENARIO_FILTER_TYPE))

    def test_serialization_with_filters(self):
        filter_settings = FilterSettings({"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": True}}})
        connection = Connection(None, filter_settings)
        connection_dict = connection.to_dict()
        restored = Connection.from_dict(connection_dict)
        self.assertTrue(restored.has_filters_online())
        self.assertEqual(
            restored._filter_settings.known_filters,
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": True}}},
        )

    def test_deserialize_legacy_filter_settings(self):
        connection_dict = {
            "from": "start",
            "to": "end",
            "disabled_filters": {"database@Data Store": {SCENARIO_FILTER_TYPE: ["MyScenario"]}},
        }
        connection = Connection.from_dict(connection_dict)
        self.assertEqual(
            connection._filter_settings.known_filters,
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"MyScenario": False}}},
        )

    def test_no_notifications_when_filter_settings_ok(self):
        filter_settings = FilterSettings({"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": True}}})
        connection = Connection({"require_" + SCENARIO_FILTER_TYPE: True}, filter_settings)
        self.assertEqual(connection.notifications(), [])

    def test_no_notifications_when_filters_on_auto_online(self):
        filter_settings = FilterSettings({})
        connection = Connection({"require_" + SCENARIO_FILTER_TYPE: True}, filter_settings)
        self.assertEqual(connection.notifications(), [])

    def test_notification_when_required_filters_are_offline(self):
        filter_settings = FilterSettings(
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": False}}}, auto_online=False
        )
        connection = Connection({"require_" + SCENARIO_FILTER_TYPE: True}, filter_settings)
        self.assertEqual(connection.notifications(), ["At least one scenario filter must be active."])

    def test_convert_backward_resources_applies_write_index(self):
        connection = Connection({"write_index": 23}, None)
        sibling_1 = Connection({"write_index": 5}, None)
        sibling_2 = Connection({"write_index": 99}, None)
        siblings = {("source_a", "destination"): sibling_1, ("source_b", "destination"): sibling_2}
        resources = [
            database_resource("destination", "mysql://example.com/db", "database@destination", filterable=True),
        ]
        converted = connection.convert_backward_resources(resources, ("source", "destination"), siblings)
        self.assertEqual(len(converted), 1)
        self.assertEqual(converted[0].metadata["current"], ("source", "destination"))
        self.assertEqual(converted[0].metadata["precursors"], {("source_a", "destination")})
        self.assertIsInstance(converted[0].metadata["part_count"], PartCount)

    def test_convert_backward_resources_applies_memory_database(self):
        connection = Connection({"use_memory_db": True}, None)
        siblings = {}
        resources = [
            database_resource("destination", "mysql://example.com/db", "database@destination", filterable=True),
        ]
        converted = connection.convert_backward_resources(resources, ("source", "destination"), siblings)
        self.assertEqual(len(converted), 1)
        self.assertTrue(converted[0].metadata["memory"])

    def test_convert_forward_resources_applies_datapackage(self):
        connection = Connection({"use_datapackage": True}, None)
        with TemporaryDirectory() as temp_dir:
            base_dir = pathlib.Path(temp_dir) / "data"
            base_dir.mkdir()
            csv_path_1 = base_dir / "data1.csv"
            csv_path_1.touch()
            csv_path_2 = base_dir / "data2.csv"
            csv_path_2.touch()
            resources = [file_resource("source", str(csv_path_1)), file_resource("source", str(csv_path_2))]
            converted = connection.convert_forward_resources(resources)
            datapackage_path = base_dir.parent / "datapackage.json"
            self.assertTrue(datapackage_path.exists())
            self.assertEqual(len(converted), 1)
            datapackage_resource = file_resource("source", str(datapackage_path), "datapackage@source")
            self.assertEqual(converted[0], datapackage_resource)
            datapackage_path = pathlib.Path(temp_dir) / "datapackage.json"
            self.assertTrue(datapackage_path.exists())

    def test_convert_forward_resources_applies_memory_database(self):
        connection = Connection({"use_memory_db": True}, None)
        resources = [
            database_resource("source", "mysql://example.com/db", "database@source", filterable=True),
        ]
        converted = connection.convert_forward_resources(resources)
        self.assertEqual(len(converted), 1)
        self.assertTrue(converted[0].metadata["memory"])


class TestFilterSettings(unittest.TestCase):
    def test_has_filters_returns_false_when_no_filters_exist(self):
        settings = FilterSettings()
        self.assertFalse(settings.has_filters())

    def test_has_filters_returns_true_when_filters_exist(self):
        settings = FilterSettings({"database@Data Store": {SCENARIO_FILTER_TYPE: {"tool_1": True}}})
        self.assertTrue(settings.has_filters())

    def test_has_filters_online_returns_false_when_no_filters_exist(self):
        settings = FilterSettings()
        self.assertFalse(settings.has_filter_online(SCENARIO_FILTER_TYPE))

    def test_has_filters_online_returns_false_when_filters_are_offline(self):
        settings = FilterSettings(
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": False, "scenario_2": False}}}
        )
        self.assertFalse(settings.has_filter_online(SCENARIO_FILTER_TYPE))

    def test_has_filters_online_returns_true_when_filters_are_online(self):
        settings = FilterSettings(
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": False, "scenario_2": True}}}
        )
        self.assertTrue(settings.has_filter_online(SCENARIO_FILTER_TYPE))

    def test_has_filter_online_works_when_there_are_no_known_filters(self):
        settings = FilterSettings()
        self.assertFalse(settings.has_filter_online(SCENARIO_FILTER_TYPE))

    def test_has_any_filter_online_returns_true_when_filters_are_online(self):
        settings = FilterSettings(
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": False, "scenario_2": True}}}
        )
        self.assertTrue(settings.has_any_filter_online())

    def test_has_any_filter_online_returns_false_when_all_filters_are_offline(self):
        settings = FilterSettings(
            {"database@Data Store": {SCENARIO_FILTER_TYPE: {"scenario_1": False, "scenario_2": False}}}
        )
        self.assertFalse(settings.has_any_filter_online())


if __name__ == "__main__":
    unittest.main()
