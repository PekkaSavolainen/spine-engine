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
"""This module contains unit tests for the project_settings module."""
import unittest

from spine_engine.project.project_settings import ProjectSettings


class TestProjectSettings(unittest.TestCase):
    def test_serialization(self):
        settings = ProjectSettings()
        settings_dict = settings.to_dict()
        deserialized = ProjectSettings.from_dict(settings_dict)
        self.assertEqual(deserialized.enable_execute_all, settings.enable_execute_all)


if __name__ == '__main__':
    unittest.main()
