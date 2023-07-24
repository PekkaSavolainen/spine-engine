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
"""Unit tests for project_item_specification module."""
import pathlib
import unittest

from spine_engine.project.project_item_specification import ProjectItemSpecification


class _SpecificationWithLocalData(ProjectItemSpecification):
    def to_dict(self):
        specification_dict = super().to_dict()
        specification_dict["local data"] = 23
        return specification_dict

    def _dict_local_entries(self):
        return super()._dict_local_entries() + [("local data",)]


class TestProjectItemSpecification(unittest.TestCase):
    def test_new_specification_is_not_plugin(self):
        specification = ProjectItemSpecification("Test specification", "For testing purposes.")
        self.assertFalse(specification.is_plugin())

    def test_is_virtual(self):
        specification = ProjectItemSpecification("Test specification", "For testing purposes.")
        self.assertTrue(specification.is_memory_only)
        specification.tie_to_disk("/path/to/specification.json")
        self.assertFalse(specification.is_memory_only)

    def test_make_physical(self):
        specification = ProjectItemSpecification("Test specification", "For testing purposes.")
        specification.tie_to_disk("/path/to/specification.json")
        self.assertFalse(specification.is_memory_only)
        self.assertEqual(specification.get_file_path(), pathlib.Path("/path/to/specification.json"))

    def test_serialization(self):
        specification = ProjectItemSpecification("Test specification", "For testing purposes.")
        specification_dict = specification.to_dict()
        deserialized = ProjectItemSpecification.from_dict(specification_dict)
        self.assertEqual(deserialized.name, specification.name)
        self.assertEqual(deserialized.description, specification.description)

    def test_local_data(self):
        specification = _SpecificationWithLocalData("Test specification", "For testing purposes.")
        loca_data = specification.local_data()
        self.assertEqual(loca_data, {"local data": 23})

    def test_may_have_local_data(self):
        self.assertFalse(ProjectItemSpecification("Test specification", "For testing purposes.").may_have_local_data())
        self.assertTrue(
            _SpecificationWithLocalData("Test specification", "For testing purposes.").may_have_local_data()
        )

    def test_pop_local_entries(self):
        specification = _SpecificationWithLocalData("Test specification", "For testing purposes.")
        specification_dict = specification.to_dict()
        local_data = specification.pop_local_entries(specification_dict)
        self.assertEqual(specification_dict, {"name": "Test specification", "description": "For testing purposes."})
        self.assertEqual(local_data, {"local data": 23})


if __name__ == '__main__':
    unittest.main()
