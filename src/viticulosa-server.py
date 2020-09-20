#!/usr/bin/python3

#
#   Copyright (C) 2020 P.L. Lucas
#
#
# LICENSE: BSD
# You may use this file under the terms of the BSD license as follows:
#
# "Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in
#     the documentation and/or other materials provided with the
#     distribution.
#   * Neither the name of developers or companies in the above copyright, Digia Plc and its
#     Subsidiary(-ies) nor the names of its contributors may be used to
#     endorse or promote products derived from this software without
#     specific prior written permission.
#
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."

import tempfile
import os
import subprocess, shlex

import socket
import sys
import os


class Parser:
    def __init__(self):
        self.line = bytearray()
        self.archivo = False
        self.camara = None
        self.ffmpeg = None
        self.quit = False
        self.responder = False

    def feed(self, data):
        if not self.archivo:
            for ch in data:
                #print(ch)
                if ch == 10: # ch == '\n'
                    print('Procesando línea:')
                    self.linea()
                    self.line = bytearray()
                else:
                    self.line.append(ch)
                    #print(self.line)

    def linea(self):
        line = self.line.strip()
        if line.startswith(b'camara:'):
            command_line = b'gst-launch-1.0 ' + line[len(b'camara:'):].strip()
            if self.camara != None:
                self.camara.terminate()
                self.camara.wait()
                self.camara = None
            args = shlex.split(command_line.decode())
            self.camara = subprocess.Popen(args)
        elif line.startswith(b'ffmpeg:'):
            command_line = b'ffmpeg ' + line[len(b'camara:'):].strip()
            if self.ffmpeg != None:
                self.ffmpeg.terminate()
                self.ffmpeg.wait()
                self.ffmpeg = None
            args = shlex.split(command_line.decode())
            self.ffmpeg = subprocess.Popen(args)
        elif line.startswith(b'stop ffmpeg:'):
            if self.ffmpeg != None:
                self.ffmpeg.terminate()
                self.ffmpeg.wait()
                self.ffmpeg = None
                self.responder = True
        elif line.startswith(b'stop camara:'):
            print("Parando la cámara")
            if self.camara != None:
                self.camara.terminate()
                self.camara.wait()
                self.camara = None
        elif line.startswith(b'quit:'):
            if self.camara != None:
                self.camara.terminate()
                self.camara.wait()
                self.camara = None
            if self.ffmpeg != None:
                self.ffmpeg.terminate()
                self.ffmpeg.wait()
                self.ffmpeg = None
            self.quit =True
        else:
            print("Mensaje no conocido:")
            print(self.line)
            print()



server_address = './uds_socket'

# Make sure the socket does not already exist
try:
    os.unlink(server_address)
except OSError:
    if os.path.exists(server_address):
        raise

# Create a UDS socket
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Bind the socket to the address
print('starting up on {}'.format(server_address))
sock.bind(server_address)

# Listen for incoming connections
sock.listen()

while True:
    # Wait for a connection
    print('waiting for a connection')
    connection, client_address = sock.accept()
    try:
        print('connection from', client_address)

        parser = Parser()
        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(100000)
            if not data:
                print('no data from', client_address)
                break
            print('received {!r}'.format(data))
            parser.feed(data)
            if parser.quit:
                connection.close()
            elif parser.responder:
                connection.sendall(b'1')
                parser.responder = False

            #if data:
            #    print('sending data back to the client')
            #    connection.sendall(data)

    finally:
        # Clean up the connection
        connection.close()
