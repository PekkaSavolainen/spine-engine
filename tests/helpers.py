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
"""This module contains unit test helpers."""
from contextlib import contextmanager
import importlib
import pathlib
import sys


@contextmanager
def import_test_items_module():
    sys.path.insert(0, str(pathlib.Path(__file__).parent / "mock_project_items"))
    items_module = importlib.import_module("items_module")
    try:
        yield items_module
    finally:
        sys.path.pop(0)
