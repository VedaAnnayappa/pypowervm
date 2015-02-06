# Copyright 2014, 2015 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

import pypowervm.adapter as adp

EOL = "\n"

COMMENT = "#"
INFO = "INFO{"
HEADERS = "HEADERS{"
BODY = "BODY{"
END_OF_SECTION = "END OF SECTION}"


class PVMFile(object):
    def __init__(self, file_name=None):
        self.comment = None
        self.host = None
        self.user = None
        self.pw = None
        self.path = None
        self.reason = None
        self.status = None
        self.headers = None
        self.body = None

        if file_name is not None:
            self.load_file(file_name)

    def load_file(self, file_name):
        """First try to load the name as passed in."""
        dirname = os.path.dirname(file_name)
        if dirname is None or dirname == '':
            dirname = os.path.dirname(os.path.dirname(__file__))
            file_name = os.path.join(dirname, "data", file_name)

        resp_file = open(file_name, "r")

        if resp_file is None:
            raise Exception("Could not load %s" % file_name)

        while True:
            line = resp_file.readline()
            if line is None or len(line) == 0:
                break

            if len(line.strip()) == 0:
                continue

            if line.startswith(COMMENT):
                continue

            if line.startswith(INFO):
                section = INFO
            elif line.startswith(HEADERS):
                section = HEADERS
            elif line.startswith(BODY):
                section = BODY
            else:
                resp_file.close()
                raise Exception("Unknown line in file %s: %s" %
                                (file_name, line))

            buf = _read_section(section, file_name, resp_file)

            if line.startswith(INFO):
                info = eval(buf)
                self.comment = info['comment']
                self.host = info['host']
                self.user = info['user']
                self.pw = info['pw']
                self.path = info['path']
                self.reason = info['reason']
                self.status = info['status']
            elif line.startswith(HEADERS):
                self.headers = eval(buf)
            elif line.startswith(BODY):
                self.body = buf

        resp_file.close()


class PVMResp(PVMFile):

    """Class to encapsulate the text serialization of a response."""

    def __init__(self, file_name=None, pvmfile=None):
        """Initialize this PVMResp by loading a file or pulling a PVMFile.

        :param file_name: Name of a file to load.
        :param pvmfile: An existing PVMFile instance.  This PVMResp will use
                        its attributes.  If both file_name and pvmfile are
                        specified, the file will be reloaded into the passed-in
                        PVMFile.  This is probably not what you intended.
        """
        super(PVMResp, self).__init__()
        # Legacy no-arg constructor - allow caller to set fields manually
        if pvmfile is None and file_name is None:
            return
        if pvmfile is None:
            self.load_file(file_name)
        else:
            # Use pvmfile
            if file_name is not None:
                pvmfile.load_file(file_name)
            # Copy in attrs from pvmfile
            self.comment = pvmfile.comment
            self.host = pvmfile.host
            self.user = pvmfile.user
            self.pw = pvmfile.pw
            self.path = pvmfile.path
            self.reason = pvmfile.reason
            self.status = pvmfile.status
            self.headers = pvmfile.headers
            self.body = pvmfile.body

        self.response = adp.Response(reqmethod=None, reqpath=None,
                                     status=self.status, reason=self.reason,
                                     headers=self.headers, body=self.body)
        self.response._unmarshal_atom()

    def get_response(self):
        return self.response

    def refresh(self):
        """Do the query and get the response."""

        print("Connecting to " + self.host)
        conn = adp.Session(self.host, self.user, self.pw, certpath=None)
        if conn is None:
            print("Could not get connection to " + self.host)
            return False

        oper = adp.Adapter(conn)
        if oper is None:
            print("Could not create a Adapter")
            return False

        print("Reading path:  " + self.path)
        self.response = oper.read(self.path)

        print("Received " + self.response)

    def save(self, file_name):

        everything = {
            'comment': self.comment,
            'host': self.host,
            'user': self.user,
            'pw': self.pw,
            'path': self.path,
            'reason': self.response.reason,
            'status': self.response.status,
        }

        disk_file = file(file_name, 'wb')
        disk_file.write("####################################################")
        disk_file.write(EOL)
        disk_file.write("# THIS IS AN AUTOMATICALLY GENERATED FILE")
        disk_file.write(EOL)
        disk_file.write("# DO NOT EDIT. ANY EDITS WILL BE LOST ON NEXT UPDATE")
        disk_file.write(EOL)
        disk_file.write("#")
        disk_file.write(EOL)
        disk_file.write("# To update file, run: create_httpresp.py -refresh ")
        disk_file.write(os.path.basename(file_name))
        disk_file.write(EOL)
        disk_file.write("#")
        disk_file.write(EOL)
        disk_file.write("####################################################")
        disk_file.write(EOL)

        disk_file.write(INFO + EOL)
        disk_file.write(str(everything))
        disk_file.write(EOL)
        disk_file.write(END_OF_SECTION)
        disk_file.write(EOL)
        disk_file.write(HEADERS + EOL)
        disk_file.write(str(self.response.headers))
        disk_file.write(EOL)
        disk_file.write(END_OF_SECTION)
        disk_file.write(EOL)
        disk_file.write(BODY + EOL)
        disk_file.write(self.response.body)
        disk_file.write(EOL)
        disk_file.write(END_OF_SECTION)
        disk_file.write(EOL)
        disk_file.close()


def load_pvm_resp(file_name):
    return PVMResp(file_name)


def _read_section(section, file_name, resp_file):

    buf = ""
    while True:
        line = resp_file.readline()
        if line is None or len(line) == 0:
            raise Exception("Could not find end of section %s of file %s" %
                            (section, file_name))

        if line.startswith(END_OF_SECTION):
            return buf

        buf += EOL + line
