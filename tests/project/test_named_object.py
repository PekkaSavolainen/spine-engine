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
import unittest
from spine_engine.project.named_object import NamedObject


class TestNamedObject(unittest.TestCase):
    def test_name_and_description_are_initialized_correctly(self):
        named_object = NamedObject("object's name", "Just a test object.")
        self.assertEqual(named_object.name, "object's name")
        self.assertEqual(named_object.description, "Just a test object.")

    def test_name_and_description_are_serialized_correctly(self):
        named_object = NamedObject("object's name", "Just a test object.")
        serialized = named_object.to_dict()
        self.assertEqual(serialized, {"name": "object's name", "description": "Just a test object."})


if __name__ == '__main__':
    unittest.main()
