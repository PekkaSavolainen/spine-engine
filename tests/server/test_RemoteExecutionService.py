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
Unit tests for RemoteExecutionService class.
:author: P. Pääkkönen (VTT), P. Savolainen (VTT)
:date:   24.8.2021
"""

import unittest
import json
import os
import random
from pathlib import Path
from unittest import mock
from tempfile import TemporaryDirectory
import zmq
from spine_engine.server.engine_server import EngineServer, ServerSecurityModel
from spine_engine.server.util.server_message import ServerMessage
from spine_engine.server.util.event_data_converter import EventDataConverter


class TestRemoteExecutionService(unittest.TestCase):
    def setUp(self):
        self._temp_dir = TemporaryDirectory()
        self.service = EngineServer("tcp", 5559, ServerSecurityModel.NONE, "")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.identity = "Worker1".encode("ascii")
        self.socket.connect("tcp://localhost:5559")
        self.sub_socket = self.context.socket(zmq.SUB)

    def tearDown(self):
        self.service.close()
        if not self.socket.closed:
            self.socket.close()
        if not self.sub_socket.closed:
            self.sub_socket.close()
        if not self.context.closed:
            self.context.term()
        try:
            self._temp_dir.cleanup()
        except RecursionError:
            print("RecursionError due to a PermissionError on Windows")

    @mock.patch("spine_engine.server.project_extractor_service.ProjectExtractorService.INTERNAL_PROJECT_DIR", new_callable=mock.PropertyMock)
    def test_remote_execution1(self, mock_proj_dir):
        """Tests executing a DC -> Python Tool DAG."""
        mock_proj_dir.return_value = self._temp_dir.name
        with open(os.path.join(str(Path(__file__).parent), "test_zipfile.zip"), "rb") as f:
            file_data = f.read()
        prepare_msg = ServerMessage("prepare_execution", "1", json.dumps("test project1"), ["test_zipfile.zip"])
        self.socket.send_multipart([prepare_msg.to_bytes(), file_data])
        prepare_response = self.socket.recv()
        prepare_response_msg = ServerMessage.parse(prepare_response)
        job_id = prepare_response_msg.getId()
        self.assertEqual("prepare_execution", prepare_response_msg.getCommand())
        self.assertTrue(len(job_id) == 32)
        self.assertEqual("", prepare_response_msg.getData())
        # Send start_execution request
        engine_data = self.make_engine_data_for_test_zipfile_project()
        engine_data_json = json.dumps(engine_data)
        start_msg = ServerMessage("start_execution", job_id, engine_data_json, None)
        self.socket.send_multipart([start_msg.to_bytes()])
        start_response = self.socket.recv()
        start_response_msg = ServerMessage.parse(start_response)
        start_response_msg_data = start_response_msg.getData()
        self.assertEqual("remote_execution_started", start_response_msg_data[0])
        self.assertTrue(self.receive_events(start_response_msg_data[1]))

    @mock.patch("spine_engine.server.project_extractor_service.ProjectExtractorService.INTERNAL_PROJECT_DIR", new_callable=mock.PropertyMock)
    def test_remote_execution2(self, mock_project_dir):
        """Tests executing a project with 3 items (1 Dc + 2 Tools)."""
        mock_project_dir.return_value = self._temp_dir.name
        with open(os.path.join(str(Path(__file__).parent), "project_package.zip"), "rb") as f:
            file_data = f.read()
        prepare_msg = ServerMessage("prepare_execution", "1", json.dumps("test project2"), ["project_package.zip"])
        self.socket.send_multipart([prepare_msg.to_bytes(), file_data])
        prepare_response = self.socket.recv()
        prepare_response_msg = ServerMessage.parse(prepare_response)
        job_id = prepare_response_msg.getId()
        self.assertEqual("prepare_execution", prepare_response_msg.getCommand())
        self.assertTrue(len(job_id) == 32)
        self.assertEqual("", prepare_response_msg.getData())
        # Send start_execution request
        engine_data = self.make_engine_data_for_project_package_project()
        engine_data_json = json.dumps(engine_data)
        start_msg = ServerMessage("start_execution", job_id, engine_data_json, None)
        self.socket.send_multipart([start_msg.to_bytes()])
        start_response = self.socket.recv()
        start_response_msg = ServerMessage.parse(start_response)
        start_response_msg_data = start_response_msg.getData()
        self.assertEqual("remote_execution_started", start_response_msg_data[0])
        self.assertTrue(self.receive_events(start_response_msg_data[1]))

    @mock.patch("spine_engine.server.project_extractor_service.ProjectExtractorService.INTERNAL_PROJECT_DIR", new_callable=mock.PropertyMock)
    def test_loop_calls(self, mock_proj_dir):
        """Tests executing a project with 3 items (1 DC + 2 Tools) five times in a row."""
        mock_proj_dir.return_value = self._temp_dir.name
        engine_data = self.make_engine_data_for_project_package_project()
        engine_data_json = json.dumps(engine_data)
        with open(os.path.join(str(Path(__file__).parent), "project_package.zip"), "rb") as f:
            file_data = f.read()
        for i in range(5):
            # Switch project folder on each iteration
            project_name = "loop_test_project_" + str(i)
            prepare_msg = ServerMessage("prepare_execution", "1", json.dumps(project_name), ["project_package.zip"])
            self.socket.send_multipart([prepare_msg.to_bytes(), file_data])
            prepare_response = self.socket.recv()
            prepare_response_msg = ServerMessage.parse(prepare_response)
            job_id = prepare_response_msg.getId()
            self.assertEqual("prepare_execution", prepare_response_msg.getCommand())
            # Send start_execution request
            start_msg = ServerMessage("start_execution", job_id, engine_data_json, None)
            self.socket.send_multipart([start_msg.to_bytes()])
            start_response = self.socket.recv()
            start_response_msg = ServerMessage.parse(start_response)
            start_response_msg_data = start_response_msg.getData()
            self.assertEqual("remote_execution_started", start_response_msg_data[0])
            self.assertTrue(self.receive_events(start_response_msg_data[1]))

    def receive_events(self, publish_port):
        """Receives events from server until DAG execution has finished.

        Args:
            publish_port (str): Publish socket port

        Returns:
            bool: True if execution succeeds, False otherwise.
        """
        self.sub_socket.connect("tcp://localhost:" + publish_port)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, b"EVENTS")
        retval = False
        while True:
            rcv = self.sub_socket.recv_multipart()
            event_deconverted = EventDataConverter.deconvert(rcv[1])
            if event_deconverted[0] == "dag_exec_finished":
                if event_deconverted[1] == "COMPLETED":
                    retval = True
                break
        return retval

    def assert_error_response(self, expected_event_type, expected_start_of_error_msg):
        """Waits for a response from server and checks that the error msg is as expected."""
        response = self.socket.recv()
        server_msg = ServerMessage.parse(response)
        msg_data = server_msg.getData()
        self.assertEqual(expected_event_type, msg_data[0])
        self.assertTrue(msg_data[1].startswith(expected_start_of_error_msg))

    def make_default_item_dict(self, item_type):
        """Keep up-to-date with spinetoolbox.project_item.project_item.item_dict()."""
        return {
            "type": item_type,
            "description": "",
            "x": random.uniform(0, 100),
            "y": random.uniform(0, 100),
        }

    def make_dc_item_dict(self, file_ref=None):
        """Make a Data Connection item_dict.
        Keep up-to-date with spine_items.data_connection.data_connection.item_dict()."""
        d = self.make_default_item_dict("Data Connection")
        d["file_references"] = file_ref if file_ref is not None else list()
        d["db_references"] = []
        d["db_credentials"] = []
        return d

    def make_tool_item_dict(self, spec_name, exec_in_work, options=None, group_id=None):
        """Make a Tool item_dict.
        Keep up-to-date with spine_items.tool.tool.item_dict()."""
        d = self.make_default_item_dict("Tool")
        d["specification"] = spec_name
        d["execute_in_work"] = exec_in_work
        d["cmd_line_args"] = []
        if options is not None:
            d["options"] = options
        if group_id is not None:
            d["group_id"] = group_id
        return d

    @staticmethod
    def make_python_tool_spec_dict(
            name,
            script_path,
            input_file,
            exec_in_work,
            includes_main_path,
            def_file_path,
            exec_settings=None):
        return {
            "name": name,
            "tooltype": "python",
            "includes": script_path,
            "description": "",
            "inputfiles": input_file,
            "inputfiles_opt": [],
            "outputfiles": [],
            "cmdline_args": [],
            "execute_in_work": exec_in_work,
            "includes_main_path": includes_main_path,
            "execution_settings": exec_settings if exec_settings is not None else dict(),
            "definition_file_path": def_file_path,
        }

    def make_engine_data_for_test_zipfile_project(self):
        """Returns an engine data dictionary for SpineEngine() for the project in file test_zipfile.zip.

        engine_data dict must be the same as what is passed to SpineEngineWorker() in
        spinetoolbox.project.create_engine_worker()
        """
        tool_item_dict = self.make_tool_item_dict("helloworld2", False)
        dc_item_dict = self.make_dc_item_dict(file_ref=[{"type": "path", "relative": True, "path": "input2.txt"}])
        spec_dict = self.make_python_tool_spec_dict("helloworld2", ["helloworld.py"], ["input2.txt"], True, "../../..",
                                                    "./helloworld/.spinetoolbox/specifications/Tool/helloworld2.json")
        item_dicts = dict()
        item_dicts["helloworld"] = tool_item_dict
        item_dicts["Data Connection 1"] = dc_item_dict
        specification_dicts = dict()
        specification_dicts["Tool"] = [spec_dict]
        engine_data = {
            "items": item_dicts,
            "specifications": specification_dicts,
            "connections": [{"from": ["Data Connection 1", "left"], "to": ["helloworld", "right"]}],
            "jumps": [],
            "execution_permits": {"Data Connection 1": True, "helloworld": True},
            "items_module_name": "spine_items",
            "settings": {},
            "project_dir": "./helloworld",
        }
        return engine_data

    def make_engine_data_for_project_package_project(self):
        """Returns an engine data dictionary for SpineEngine() for the project in file project_package.zip.

        engine_data dict must be the same as what is passed to SpineEngineWorker() in
        spinetoolbox.project.create_engine_worker()
        """
        t1_item_dict = self.make_tool_item_dict("a", False)
        t2_item_dict = self.make_tool_item_dict("b", True,)
        dc1_item_dict = self.make_dc_item_dict()
        exec_settings_a = {
            "env": "",
            "kernel_spec_name": "python38",
            "use_jupyter_console": False,
            "executable": "",
            "fail_on_stderror": False
        }
        spec_dict_a = self.make_python_tool_spec_dict(
            "a",
            ["a.py"],
            [],
            True,
            ".",
            "C:/Users/ttepsa/OneDrive - Teknologian Tutkimuskeskus VTT/Documents/SpineToolboxProjects/remote test 3 items/.spinetoolbox/specifications/Tool/a.json",
            exec_settings_a
        )
        exec_settings_b = {
            "env": "",
            "kernel_spec_name": "python38",
            "use_jupyter_console": False,
            "executable": "",
            "fail_on_stderror": True
        }
        spec_dict_b = self.make_python_tool_spec_dict(
            "b",
            ["b.py"],
            [],
            True,
            "../../..",
            "C:/Users/ttepsa/OneDrive - Teknologian Tutkimuskeskus VTT/Documents/SpineToolboxProjects/remote test 3 items/.spinetoolbox/specifications/Tool/b.json",
            exec_settings_b
        )
        item_dicts = dict()
        item_dicts["T1"] = t1_item_dict
        item_dicts["T2"] = t2_item_dict
        item_dicts["DC1"] = dc1_item_dict
        specification_dicts = dict()
        specification_dicts["Tool"] = [spec_dict_a, spec_dict_b]
        engine_data = {
            "items": item_dicts,
            "specifications": specification_dicts,
            "connections": [{"from": ["DC1", "right"], "to": ["T1", "left"]},
                            {"from": ["T1", "right"], "to": ["T2", "left"]}],
            "jumps": [],
            "execution_permits": {"DC1": True, "T1": True, "T2": True},
            "items_module_name": "spine_items",
            "settings": {},
            "project_dir": "C:/Users/ttepsa/OneDrive - Teknologian Tutkimuskeskus VTT/Documents/SpineToolboxProjects/remote test 3 items",
        }
        return engine_data


if __name__ == "__main__":
    unittest.main()