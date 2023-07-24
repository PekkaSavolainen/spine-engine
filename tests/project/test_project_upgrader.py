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
"""Unit tests for ProjectUpgrader class."""

import importlib
import pathlib
import sys
from tempfile import TemporaryDirectory
import unittest
from spine_engine.project.project_upgrader import upgrade
from spine_engine.project.project import LATEST_PROJECT_VERSION
from spine_engine.project.exception import ProjectVersionTooHigh


class TestUpgrade(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "mock_project_items"))
        self._items_module = importlib.import_module("items_module")

    def tearDown(self):
        sys.path.pop(0)

    def test_upgrade_with_too_recent_project_version(self):
        """Tests that projects with too recent versions are not opened."""
        project_dict = {
            "project": {"version": LATEST_PROJECT_VERSION + 1},
        }
        self.assertRaises(ProjectVersionTooHigh, upgrade, project_dict, "", self._items_module)

    def test_upgrade_v10_to_v11(self):
        project_dict_v10 = {
            "project": {
                "version": 10,
                "specifications": {},
            },
            "items": {},
        }
        with TemporaryDirectory() as project_dir:
            project_dict_v11, old_version, new_version = upgrade(project_dict_v10, project_dir, self._items_module)
        self.assertEqual(old_version, 10)
        self.assertEqual(new_version, 11)
        self.assertEqual(project_dict_v11, {"items": {"items_module": {}},
 "project": {"project_item_packages": {"items_module": {"version": 1}},
             "specifications": {"items_module": {}},
             "version": 11}})
