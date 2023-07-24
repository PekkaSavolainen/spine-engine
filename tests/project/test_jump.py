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
from spine_engine.project.jump import Jump
from spine_engine.project_item.project_item_resource import make_cmd_line_arg


class TestJump(unittest.TestCase):
    def test_serialization_with_condition(self):
        jump = Jump("source", "destination", {"type": "python-script", "script": "exit(23)"})
        jump_dict = jump.to_dict()
        new_jump = Jump.from_dict(jump_dict)
        self.assertEqual(new_jump.source, jump.source)
        self.assertEqual(new_jump.destination, jump.destination)
        self.assertEqual(new_jump.condition, jump.condition)

    def test_serialization_with_command_line_arguments(self):
        command_line_args = [make_cmd_line_arg("--foo")]
        jump = Jump("source", "destination", None, command_line_args)
        jump_dict = jump.to_dict()
        new_jump = Jump.from_dict(jump_dict)
        self.assertEqual(new_jump.source, jump.source)
        self.assertEqual(new_jump.destination, jump.destination)
        self.assertEqual(new_jump.condition, jump.condition)


if __name__ == '__main__':
    unittest.main()
