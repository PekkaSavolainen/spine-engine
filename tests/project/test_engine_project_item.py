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
import logging
import unittest
from hashlib import sha1
from threading import Lock

from spine_engine import ItemExecutionFinishState
from spine_engine.project.engine_project_item import EngineProjectItem, FilteredExecutionLogger
from spine_engine.project.project_item import ProjectItem
from spine_engine.utils.helpers import AppSettings, ExecutionDirection


class TestEngineProjectItem(unittest.TestCase):
    class _ProjectItem(ProjectItem):
        @staticmethod
        def item_type():
            return "real project item"

    def _make_logger(self):
        logger = logging.getLogger(EngineProjectItem.logger_name())
        log_handler = _ListHandler()
        logger.addHandler(log_handler)
        logger.setLevel(logging.INFO)
        return logger, log_handler

    def setUp(self):
        self._item = self._ProjectItem("my project item", "Item for testing purposes.")

    def test_none_as_group_id_uses_item_name(self):
        item = EngineProjectItem(self._item, None)
        self.assertEqual(item.group_id, "my project item")

    def test_set_group_id_on_init(self):
        item = EngineProjectItem(self._item, "my execution group")
        self.assertEqual(item.group_id, "my execution group")

    def test_set_filter_id_updates_items_logger(self):
        item = EngineProjectItem(self._item, None)
        logger, log_handler = self._make_logger()
        item.finish_execution(ItemExecutionFinishState.SUCCESS)
        self.assertEqual(len(log_handler.records), 1)
        record = log_handler.records[0]
        self.assertEqual(record.msg, "Finished")
        self.assertEqual(record.item_name, "my project item")
        self.assertEqual(record.item_type, "real project item")
        self.assertEqual(record.filter_id, "")
        item.filter_id = "and we have a filter"
        item.finish_execution(ItemExecutionFinishState.SUCCESS)
        self.assertEqual(len(log_handler.records), 2)
        record = log_handler.records[1]
        self.assertEqual(record.msg, "Finished")
        self.assertEqual(record.item_name, "my project item")
        self.assertEqual(record.item_type, "real project item")
        self.assertEqual(record.filter_id, "and we have a filter")

    def test_hash_filter_id(self):
        item = EngineProjectItem(self._item, None)
        item.filter_id = "execution filter"
        self.assertEqual(item.hash_filter_id(), sha1(b"execution filter").hexdigest())

    def test_ready_to_execute_returns_true(self):
        item = EngineProjectItem(self._item, None)
        settings = AppSettings({})
        self.assertTrue(item.ready_to_execute(settings))

    def test_update_returns_true(self):
        item = EngineProjectItem(self._item, None)
        self.assertTrue(item.update([], []))

    def test_execute_returns_true(self):
        item = EngineProjectItem(self._item, None)
        logger, log_handler = self._make_logger()
        lock = Lock()
        self.assertTrue(item.execute([], [], lock))
        self.assertEqual(len(log_handler.records), 1)
        record = log_handler.records[0]
        self.assertEqual(record.msg, "Executing...")

    def test_finish_execution_logs_state(self):
        item = EngineProjectItem(self._item, None)
        logger, log_handler = self._make_logger()
        self.assertEqual(len(ItemExecutionFinishState), 6)  # Update this test if states change!
        item.finish_execution(ItemExecutionFinishState.SUCCESS)
        self.assertEqual(log_handler.records[-1].msg, "Finished")
        item.finish_execution(ItemExecutionFinishState.FAILURE)
        self.assertEqual(log_handler.records[-1].msg, "Failed")
        item.finish_execution(ItemExecutionFinishState.SKIPPED)
        self.assertEqual(log_handler.records[-1].msg, "Skipped")
        item.finish_execution(ItemExecutionFinishState.STOPPED)
        self.assertEqual(log_handler.records[-1].msg, "Stopped")
        item.finish_execution(ItemExecutionFinishState.EXCLUDED)
        self.assertEqual(log_handler.records[-1].msg, "Finished execution in an unknown state")
        item.finish_execution(ItemExecutionFinishState.NEVER_FINISHED)
        self.assertEqual(log_handler.records[-1].msg, "Finished execution in an unknown state")

    def test_is_filter_terminus_returns_false(self):
        item = EngineProjectItem(self._item, None)
        self.assertFalse(item.is_filter_terminus())

    def test_output_resources_in_forward_direction(self):
        item = EngineProjectItem(self._item, None)
        self.assertEqual(item.output_resources(ExecutionDirection.FORWARD), [])

    def test_output_resources_in_backward_direction(self):
        item = EngineProjectItem(self._item, None)
        self.assertEqual(item.output_resources(ExecutionDirection.BACKWARD), [])

    def test_stop_execution_logs_stopping_message(self):
        item = EngineProjectItem(self._item, None)
        logger, log_handler = self._make_logger()
        item.stop_execution()
        self.assertEqual(len(log_handler.records), 1)
        self.assertEqual(log_handler.records[0].msg, "Stopping...")


class TestFilteredExecutionLogger(unittest.TestCase):
    def setUp(self):
        base_logger = logging.getLogger(__name__)
        base_logger.setLevel(logging.INFO)
        self._log_handler = _ListHandler()
        base_logger.addHandler(self._log_handler)
        self._logger = FilteredExecutionLogger(base_logger, "my item", "test_item_type", "test filter id")

    def test_initialization(self):
        self._logger.info("Heed this message interloper.")
        self.assertEqual(len(self._log_handler.records), 1)
        record = self._log_handler.records[0]
        self.assertEqual(record.msg, "Heed this message interloper.")
        self.assertEqual(record.item_name, "my item")
        self.assertEqual(record.item_type, "test_item_type")
        self.assertEqual(record.filter_id, "test filter id")

    def test_set_filter_id(self):
        self._logger.set_filter_id("new filter id")
        self._logger.info("Heed this message interloper.")
        self.assertEqual(len(self._log_handler.records), 1)
        record = self._log_handler.records[0]
        self.assertEqual(record.msg, "Heed this message interloper.")
        self.assertEqual(record.item_name, "my item")
        self.assertEqual(record.item_type, "test_item_type")
        self.assertEqual(record.filter_id, "new filter id")


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


if __name__ == '__main__':
    unittest.main()
