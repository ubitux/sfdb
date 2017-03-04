#!/usr/bin/env python
#
# Copyright 2017 Clément Bœsch <u@pkh.me>
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

import socket
import getpass
import urllib.parse
import urllib.request

__version__ = '0.1'

class SimpleFreeDB:

    URL = 'http://freedb.freedb.org/~cddb/cddb.cgi'
    PROTO = 6

    def __init__(self):
        user = getpass.getuser()
        host = socket.gethostname()
        client = 'sfdb'
        hello = '%s %s %s %s' % (user, host, client, __version__)
        self._hello = urllib.parse.quote_plus(hello)

    def _cddb_cmd(self, cmd):
        cmd_arg = urllib.parse.quote_plus('cddb ' + cmd)
        url = '%s?cmd=%s&hello=%s&proto=%d' % (self.URL, cmd_arg, self._hello, self.PROTO)
        req = urllib.request.urlopen(url)
        return req.read().decode('utf-8')

    def _get_code(self, line):
        return int(line.split(maxsplit=1)[0])

    def query(self, discid, ntrks, offsets, nsecs):
        cmd = 'query %x %d %s %d' % (discid, ntrks, ' '.join(str(x) for x in offsets), nsecs)
        data = self._cddb_cmd(cmd)
        lines = data.splitlines()
        code = self._get_code(lines[0])
        matches = []
        if code == 200:
            line = lines[0]
            _, categ, discid_str, dtitle = line.split(maxsplit=3)
            matches.append((categ, int(discid_str, 16), dtitle))
        elif code in (210, 211):
            for line in lines[1:]:
                if line == '.':
                    break
                categ, discid_str, dtitle = line.split(maxsplit=2)
                matches.append((categ, int(discid_str, 16), dtitle))
        return matches

    def read(self, categ, discid):
        cmd = 'read %s %x' % (categ, discid)
        data = self._cddb_cmd(cmd)
        lines = data.splitlines()
        code = self._get_code(lines[0])
        if code != 210:
            return None

        data = {}
        trackn = 0

        for line in lines[1:]:
            if line == '.':
                break
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', maxsplit=1)
            if key == 'DTITLE':
                data['title'] = value # TODO: split?
            elif key == 'DYEAR':
                data['year'] = int(value)
            elif key == 'DGENRE':
                data['genre'] = value
            elif key.startswith('TTITLE'):
                n = int(key[6:])
                if n != trackn:
                    raise Exception('Tracks titles are not monotically incrementing')
                trackn += 1
                if not n:
                    data['tracks'] = []
                data['tracks'].append(value)

        return data

def main():
    test_queries = (
        # 200, 1 match
        (0xfd0ce112, 18, (150, 16732, 27750, 43075, 58800, 71690, 86442, 101030, 111812, 128367, 136967, 152115, 164812, 180337, 194072, 201690, 211652, 230517), 3299),
        # 211, inexact but 1 match
        (0xb70e170e, 14, (150, 20828, 36008, 53518, 71937, 90777, 109374, 128353, 150255, 172861, 192062, 216672, 235357, 253890), 3609),
    )
    import pprint
    fdb = SimpleFreeDB()
    for i, query in enumerate(test_queries):
        for match in fdb.query(*query):
            pprint.pprint(fdb.read(match[0], match[1]))

if __name__ == '__main__':
    main()
