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




import shlex, subprocess
import os
import datetime
import os.path
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class Handler:
    def __init__(self, builder):
        self.builder = builder
        self.rotacion = "none"
        self.espejo = "none"
        self.camara = None
        self.grabacion = None
        self.alto_pantalla = '600'
        self.ancho_pantalla = '800'
        self.load_settings()

    def load_settings(self):
        config = os.path.expanduser('~/.config/webcam.txt')
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

        config = os.path.expanduser('~/.config/webcam.txt')
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
            self.grabacion.terminate()
            self.grabacion.wait()
            self.grabacion = None
        if self.camara != None:
            self.camara.terminate()
        Gtk.main_quit()

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
            self.grabacion.terminate()
            self.grabacion.wait()
            self.builder.get_object("grabar").set_label('Grabar')
            self.grabacion = None
            return
        fileselect = builder.get_object("directorio_salida")
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
        archivo = '{0}/{1}'.format(carpeta, fecha.isoformat(sep=' ', timespec='seconds').replace(':', '·'))
        print(archivo)
        #return
        self.builder.get_object("grabar").set_label('Parar')
        self.reiniciar_grabacion(archivo)

    def onVerCamara(self, button):
        if self.camara == None:
            self.reiniciar_camara()
        else:
            self.camara.terminate()
            self.reiniciar_camara()

    def reiniciar_camara(self):
        command_line = 'gst-launch-1.0 -v v4l2src device=/dev/video0 ! video/x-raw,framerate=10/1 ! videoflip method={0} ! videoflip method={1} ! videoconvert ! autovideosink'.format(self.rotacion, self.espejo)
        args = shlex.split(command_line)
        self.camara = subprocess.Popen(args)

    def reiniciar_grabacion(self, archivo):
        self.pantalla_propiedades()
        # Grabación a 25 frames por segundo
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 25 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 0 -threads 0 -acodec pcm_s16le -y "{2}.mkv"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        # Se graban 5 frames por segundo para disminuir el tamaño del vídeo
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 0 -threads 0 -acodec pcm_s16le -y "{2}.mkv"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        # Se graba con alta compresión, microprocesador potente:
        #command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx265 -pix_fmt yuv420p -preset ultrafast -crf 28 -threads 0 -y "{2}.mp4"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        # Se graba con compresión, microprocesador no potente:
        command_line = 'ffmpeg -f alsa -ac 2 -i pulse -f x11grab -r 5 -s {0}x{1} -i :0.0 -vcodec libx264 -pix_fmt yuv420p -preset ultrafast -crf 28 -threads 0 -y "{2}.mp4"'.format(self.ancho_pantalla, self.alto_pantalla, archivo)
        print(command_line)
        args = shlex.split(command_line)
        self.grabacion = subprocess.Popen(args)

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

builder = Gtk.Builder()
builder.add_from_string(main_glade)
builder.connect_signals(Handler(builder))

window = builder.get_object("window")
window.show_all()

Gtk.main()