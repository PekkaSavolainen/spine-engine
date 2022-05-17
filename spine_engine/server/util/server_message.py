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
Contains a helper class for JSON-based messages exchanged between server and clients.
:authors: P. Pääkkönen (VTT), P. Savolainen (VTT)
:date:   23.08.2021
"""


class ServerMessage:
    def __init__(self, command, msg_id, data, files):
        """
        Args:
            command (str): command to be executed at the server
            msg_id (str): identifier associated with the command
            data (str): events+data (list of tuples) converted into a JSON str or an error msg (must be a JSON str)
            files (list[str], None): List of file names to be associated with the message (optional)
        """
        if not command or not msg_id:
            print("Error in ServerMessage")
            raise ValueError("invalid input to ServerMessage")
        self._command = command
        self._id = msg_id
        self._data = data
        self._files = files  # Name for the file where zip-file is saved to. Does not need to be the same as original.

    def getCommand(self):
        return self._command

    def getId(self):
        return self._id

    def getData(self):
        return self._data

    def getFileNames(self):
        return self._files

    def toJSON(self):
        """
        Returns:
            the class as a JSON string
        """
        jsonFileNames = self._getJSONFileNames()
        # print("ServerMessage.toJSON(): %s"%jsonFileNames)
        retStr = ""
        retStr += "{\n"
        retStr += "   \"command\": \"" + self._command + "\",\n"
        retStr += "   \"id\":\"" + self._id + "\",\n"

        if len(self._data) == 0:
            retStr += "   \"data\":\"\",\n"
        else:
            retStr += "   \"data\":" + self._data + ",\n"
        retStr += "   \"files\": " + jsonFileNames
        retStr += "}"
        return retStr

    def _getJSONFileNames(self):
        fileNameCount = len(self._files)
        if fileNameCount == 0:
            return "{}\n"
        retStr = '{\n'
        i = 0
        for fName in self._files:
            if i + 1 < fileNameCount:
                retStr = retStr + "    \"name-" + str(i) + "\": \"" + fName + "\",\n"
            else:
                retStr = retStr + "    \"name-" + str(i) + "\": \"" + fName + "\"\n"
            i += 1
        retStr = retStr + "    }\n"
        return retStr
