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
The function of this class can be used for generation of keys for enabling security 
of the remote spine_server. The code has been copied based on an example at (by Chris Laws):
https://github.com/zeromq/pyzmq/blob/main/examples/security/generate_certificates.py

:authors: P. Pääkkönen (VTT)
:date:   15.09.2021
"""

import os 
import shutil
import zmq.auth

class certificate_creator:

    @staticmethod
    def generate_certificates(base_dir):
        """
        Generates client,server keys for enabling security.
        Args:
            base_dir: folder where the files are created.
        """
        keys_dir = os.path.join(base_dir, 'certificates')
        public_keys_dir = os.path.join(base_dir, 'public_keys')
        secret_keys_dir = os.path.join(base_dir, 'private_keys')

        # Create directories for certificates, remove old content if necessary
        for d in [keys_dir, public_keys_dir, secret_keys_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.mkdir(d)

        # create new keys in certificates dir
        server_public_file, server_secret_file = zmq.auth.create_certificates(
            keys_dir, "server"
        )
        client_public_file, client_secret_file = zmq.auth.create_certificates(
            keys_dir, "client"
        )

        # move public keys to appropriate directory
        for key_file in os.listdir(keys_dir):
            if key_file.endswith(".key"):
                shutil.move(
                    os.path.join(keys_dir, key_file), os.path.join(public_keys_dir, '.')
                )

        # move secret keys to appropriate directory
        for key_file in os.listdir(keys_dir):
            if key_file.endswith(".key_secret"):
                shutil.move(
                    os.path.join(keys_dir, key_file), os.path.join(secret_keys_dir, '.')
                )


certificate_creator.generate_certificates("/home/ubuntu/sw/spine/dev/github/spine-engine/tests/server/connectivity/secfolder")
