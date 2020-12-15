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

# Requiere la biblioteca:
# https://github.com/owncloud/pyocclient


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


######################################################################################
### Parte del servidor

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
            command_line = b'ffplay ' + line[len(b'camara:'):].strip()
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
        elif line.startswith(b'comprimir:'):
            print("Comprimiendo vídeo")
            ruta_archivo = line[len(b'comprimir:'):].strip().decode("utf-8")
            self.compresion_video(ruta_archivo)
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


    def compresion_video(self, uploaded_file_path):
        # Se obtiene el tamaño del vídeo
        comando = 'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of default=nw=1 "{0}.mp4"'.format(uploaded_file_path)
        sys.stderr.write('\n{0}\n'.format(comando))
        height = -1
        width = -1
        fin = os.popen(comando, 'r')
        for linea in fin:
            sys.stderr.write('\n{0}\n'.format(linea))
            try:
                if linea.strip().startswith("height"):
                    height = int(linea.strip()[len('height='):].strip())
                elif linea.strip().startswith("width"):
                    width = int(linea.strip()[len('width='):].strip())
                    sys.stderr.write('\n{0}\n'.format(width))
            except Exception as err:
                sys.stderr.write('\n{0}\n'.format(err))
        fin.close()
        calidad = ''
        ratio = width/height
        sys.stderr.write('\n\nwidth480={0}\n\n'.format(int(ratio * 480 + 0.5)))
        sys.stderr.write('width720={0}\n'.format(int(ratio * 720 + 0.5)))
        sys.stderr.write('width1080={0}\n\n'.format(int(ratio * 1080 + 0.5)))
        if height > 480 and int(ratio * 480 + 0.5) % 2 == 0:
            calidad = '-vf scale=-1:480'
        elif height > 720 and int(ratio * 720 + 0.5) % 2 == 0:
            calidad = '-vf scale=-1:720'
        elif height > 1080 and int(ratio * 1080 + 0.5) % 2 == 0:
            calidad = '-vf scale=-1:1080'
        sys.stderr.write('\n{0}x{1}\n'.format(width, height))
        # Se comprime el vídeo
        #filename = os.path.basename(uploaded_file_path)
        comprimido_file_path = '{0}_comprimido.mp4'.format(uploaded_file_path)
        comando = 'ffmpeg -i "{0}.mp4" {1} -vcodec libx264 -strict -2 -crf 30 "{2}" > /dev/stderr &'.format(uploaded_file_path, calidad, comprimido_file_path)
        os.system(comando)
        sys.stderr.write('\n{0}\n'.format(comando))


def servidor():
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




######################################################################################

#import shlex, subprocess
import socket
import os, sys
import datetime
import os.path
import threading
import time
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject

class Handler:
    def __init__(self, builder):
        self.builder = builder
        self.rotacion = "none"
        self.espejo = "none"
        self.camara = None
        self.grabacion = None
        self.alto_pantalla = '600'
        self.ancho_pantalla = '800'
        self.archivo_actual = None
        self.archivo_comprimido_actual = None
        self.load_settings()
        self.hilos = []
        self.sock = None

    def load_settings(self):
        config = os.path.expanduser('~/.config/viticulosa.txt')
        if os.path.exists(config):
            fin = open(config)
            for linea in fin:
                campos = linea.split('=')
                if len(campos) > 1:
                    if campos[0] == 'rotacion':
                        self.rotacion = campos[1].strip()
                    elif campos[0] == 'espejo':
                        self.espejo = campos[1].strip()
            fin.close()
            camara_rotacion = self.builder.get_object('camara_rotacion')
            if self.rotacion == 'none':
                camara_rotacion.set_active(0)
            elif self.rotacion == 'clockwise':
                camara_rotacion.set_active(1)
            elif self.rotacion == 'rotate-180':
                camara_rotacion.set_active(2)
            elif self.rotacion == 'counterclockwise':
                camara_rotacion.set_active(3)
            espejo = self.builder.get_object('espejo')
            if self.espejo == 'none':
                espejo.set_active(0)
            elif self.espejo == 'horizontal-flip':
                espejo.set_active(1)
            elif self.espejo == 'vertical-flip':
                espejo.set_active(2)

    def save_settings(self):
        camara_rotacion = self.builder.get_object('camara_rotacion')
        valor = camara_rotacion.get_active()
        camara = 'none'
        if valor == 0:
            camara = "none"
        elif valor == 1:
            camara = "clockwise"
        elif valor == 2:
            camara = "rotate-180"
        elif valor == 3:
            camara = "counterclockwise"

        espejo_obj = self.builder.get_object('espejo')
        valor = espejo_obj.get_active()
        espejo = 'none'
        if valor == 0:
            espejo = "none"
        elif valor == 1:
            espejo = "horizontal-flip"
        elif valor == 2:
            espejo = "vertical-flip"

        config = os.path.expanduser('~/.config/viticulosa.txt')
        if not os.path.exists(config):
            path = os.path.expanduser('~/.config')
            if not os.path.exists(path):
                os.makedirs(path)
        fout = open(config, 'w')
        fout.write('rotacion={0}\n'.format(camara))
        fout.write('espejo={0}\n'.format(espejo))
        fout.close()

    def onDestroy(self, *args):
        if self.grabacion != None:
            #self.grabacion.terminate()
            #self.grabacion.wait()
            self.send_message(b'stop ffmpeg:')
            self.grabacion = None
        if self.camara != None:
            #self.camara.terminate()
            self.send_message(b'stop camara:')
        self.save_settings()
        Gtk.main_quit()
        self.send_message(b'quit:')

    def onRotacion(self, combo):
        valor = combo.get_active()
        if valor == 0:
            self.rotacion = "none"
        elif valor == 1:
            self.rotacion = "clockwise"
        elif valor == 2:
            self.rotacion = "rotate-180"
        elif valor == 3:
            self.rotacion = "counterclockwise"
        self.save_settings()

    def onEspejo(self, combo):
        valor = combo.get_active()
        if valor == 0:
            self.espejo = "none"
        elif valor == 1:
            self.espejo = "horizontal-flip"
        elif valor == 2:
            self.espejo = "vertical-flip"
        self.save_settings()


    def onGrabarParar(self, button):
        if self.grabacion != None:
            #self.grabacion.terminate()
            #self.grabacion.wait()
            self.send_message(b'stop ffmpeg:')
            #time.sleep(10)
            self.builder.get_object("grabar").set_label('Grabar')
            self.grabacion = None
            # Se comprime el vídeo si la opción está activada
            comprimir = self.builder.get_object("compresion")
            if comprimir.get_active():
                command_line = 'comprimir: {0}'.format(self.archivo_comprimido_actual).encode()
                self.send_message(command_line)
            return
        fileselect = self.builder.get_object("directorio_salida")
        carpeta = fileselect.get_uri()
        if carpeta == None:
            dialog = Gtk.MessageDialog(
                transient_for=self.builder.get_object("window"),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="ERROR: Debe seleccionar una carpeta de grabación",
            )
            dialog.format_secondary_text(
                "Debe seleccionar una carpeta en la que guardar la grabación."
            )
            dialog.run()
            dialog.destroy()
            return
        # Se pasa de URI a archivo
        if carpeta.startswith('file://'):
            carpeta = carpeta[len('file://'):]
        fecha = datetime.datetime.now()
        #archivo = '{0}/{1}'.format(carpeta, fecha.isoformat(sep=' ', timespec='seconds').replace(':', '·'))
        archivo = '{0}/{1}'.format(carpeta, fecha.isoformat(sep=' ').replace(':', '·').split('.')[0])
        self.archivo_actual = '{0}.mp4'.format(archivo)
        self.archivo_comprimido_actual = '{0}'.format(archivo)
        print(archivo)
        #return
        self.builder.get_object("grabar").set_label('Parar')
        self.reiniciar_grabacion(archivo)

    def onVerCamara(self, button):
        if self.camara == None:
            self.reiniciar_camara()
        else:
            #self.camara.terminate()
            self.send_message(b'stop camara:')
            self.reiniciar_camara()

    def reiniciar_camara(self):
        #command_line = 'camara: -v v4l2src device=/dev/video0 ! video/x-raw,framerate=10/1 ! videoflip method={0} ! videoflip method={1} ! videoconvert ! autovideosink\n'.format(self.rotacion, self.espejo).encode()
        rotacion = ""
        if self.rotacion == 'none':
            rotacion = ""
        elif self.rotacion == 'clockwise':
            rotacion = ",transpose=1"
        elif self.rotacion == 'rotate-180':
            rotacion = ",transpose=2,transpose=2"
        elif self.rotacion == 'counterclockwise':
            rotacion = ",transpose=3,hflip"
        espejo = ""
        if self.espejo == 'none':
            espejo = ""
        elif self.espejo == 'horizontal-flip':
            espejo = ",hflip"
        elif self.espejo == 'vertical-flip':
            espejo = ",vflip"
        command_line = 'camara:  -f v4l2 -i /dev/video0 -vf "format=yuv420p{0}{1}"\n'.format(rotacion, espejo).encode()
        self.send_message(command_line)
        self.camara = True

        #command_line = 'gst-launch-1.0 -v v4l2src device=/dev/video0 ! video/x-raw,framerate=10/1 ! videoflip method={0} ! videoflip method={1} ! videoconvert ! autovideosink'.format(self.rotacion, self.espejo)
        #args = shlex.split(command_line)
        #self.camara = subprocess.Popen(args)

    def send_message(self, command_line):
        try:
            if self.sock == None:
                server_address = './uds_socket'
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.connect(server_address)
            self.sock.sendall(command_line)
            self.sock.sendall(b'\n')
            if command_line.startswith(b'stop ffmpeg'):
                data = self.sock.recv(1)
        except socket.error as msg:
            print(msg)
            sys.exit(1)
        #finally:
        #    print('closing socket')
        #    self.sock.close()


    def reiniciar_grabacion(self, archivo):
        self.pantalla_propiedades()
        # Grabación a 25 frames por segundo
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 25 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 0 -threads 0 -acodec pcm_s16le -y "{2}.mkv"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        # Se graban 5 frames por segundo para disminuir el tamaño del vídeo
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 0 -threads 0 -acodec pcm_s16le -y "{2}.mkv"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        # Se graba con alta compresión, microprocesador potente:
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx265 -pix_fmt yuv420p -preset ultrafast -crf 28 -threads 0 -y "{2}.mp4"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        # Se graba con compresión, microprocesador no potente:
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 28 -threads 0 -y "{2}.mp4"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        #print(command_line)
        #args = shlex.split(command_line)
        #self.grabacion = subprocess.Popen(args)
        #command_line = 'ffmpeg: -f alsa -ac 2  -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 28 -threads 0 -y "{2}.mp4"'.format(self.ancho_pantalla, self.alto_pantalla, archivo).encode()
        command_line = 'ffmpeg: -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx264 -strict -2 -pix_fmt yuv420p -preset ultrafast -crf 28 -threads 0 -y "{2}.mp4"'.format(self.ancho_pantalla, self.alto_pantalla, archivo).encode()
        print(command_line)
        self.send_message(command_line)
        self.grabacion = True


    def pantalla_propiedades(self):
        fin = os.popen('xwininfo -root')
        for linea in fin:
            l = linea.strip()
            if l.startswith('Height:'):
                self.alto_pantalla = l[len('Height:'):].strip()
            elif l.startswith('Width:'):
                self.ancho_pantalla = l[len('Width:'):].strip()
        fin.close()


#include main_glade main.glade

def interfaz():
    builder = Gtk.Builder()
    builder.add_from_string(main_glade)
    #builder.add_from_file('main.glade')
    builder.connect_signals(Handler(builder))
    window = builder.get_object("window")
    window.show_all()
    Gtk.main()


###############################################################################
## Parte principal

pid = os.fork()
if pid == 0:
    print('Iniciando servidor')
    servidor()
else:
    print('Iniciando interfaz')
    interfaz()