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


#import shlex, subprocess
import socket
import os, sys
import datetime
import os.path
import threading
import time
import owncloud
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
        self.load_settings()
        self.hilos = []
        self.mostrar_mensaje_fin_subida = False
        self.credenciales_modificadas = True
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
                    elif campos[0] == 'servidor':
                        self.builder.get_object("servidor").set_text(campos[1].strip())
                    elif campos[0] == 'login':
                        self.builder.get_object("login").set_text(campos[1].strip())
                    elif campos[0] == 'curso':
                        self.builder.get_object("curso").set_text(campos[1].strip())
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

        servidor = self.builder.get_object("servidor").get_text()
        login = self.builder.get_object("login").get_text()
        curso = self.builder.get_object("curso").get_text()

        config = os.path.expanduser('~/.config/viticulosa.txt')
        if not os.path.exists(config):
            path = os.path.expanduser('~/.config')
            if not os.path.exists(path):
                os.makedirs(path)
        fout = open(config, 'w')
        fout.write('rotacion={0}\n'.format(camara))
        fout.write('espejo={0}\n'.format(espejo))
        fout.write('servidor={0}\n'.format(servidor))
        fout.write('login={0}\n'.format(login))
        fout.write('curso={0}\n'.format(curso))
        fout.close()

    def onDestroy(self, *args):
        if self.grabacion != None:
            #self.grabacion.terminate()
            #self.grabacion.wait()
            self.send_message(b'stop ffmpeg:')
            self.grabacion = None
            if self.builder.get_object("subir_videos").get_active():
                # Se sube el archivo a la nube
                print("Subiendo al servidor...")
                thread = threading.Thread(target=self.subir_al_servidor)
                thread.daemon = True
                thread.start()
                self.hilos.append(thread)
        if self.camara != None:
            #self.camara.terminate()
            self.send_message(b'stop camara:')
        self.save_settings()
        for thread in self.hilos:
            if thread.is_alive():
                self.mostrar_mensaje_fin_subida = True
                dialog = Gtk.MessageDialog(
                    transient_for=self.builder.get_object("window"),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="ERROR: Hay un proceso de carga al servidor en marcha",
                    )
                dialog.format_secondary_text(
                        "Todavía hay un vídeo que se está transfiriendo al servidor de EducaMadrid. Si está guardando los vídeos en un dispositivo extraible, por favor, no lo desconecte todavía"
                    )
                dialog.run()
                dialog.destroy()
                return
        Gtk.main_quit()
        self.send_message(b'quit:')

    def onMensajeFinSubida(self):
        hilos_vivos = False
        for thread in self.hilos:
            if thread.is_alive():
                hilos_vivos = True
                break
        if not hilos_vivos:
            dialog = Gtk.MessageDialog(
                transient_for=self.builder.get_object("window"),
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.CANCEL,
                text="Han finalizado los procesos de subida",
                )
            dialog.format_secondary_text(
                "Los vídeos han sido trasferidos al servidor, puede desconectar los dispositivos extraibles en el caso de que esté guardando ahí sus vídeos"
            )
            dialog.run()
            dialog.destroy()
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


    def onSubirVideos(self, ok):
        ok = self.builder.get_object("subir_videos").get_active()
        self.builder.get_object("servidor").set_sensitive(ok)
        self.builder.get_object("login").set_sensitive(ok)
        self.builder.get_object("password").set_sensitive(ok)
        self.builder.get_object("curso").set_sensitive(ok)

    def onCredenciales(self, entry):
        self.credenciales_modificadas = True

    def onGrabarParar(self, button):
        if self.grabacion != None:
            #self.grabacion.terminate()
            #self.grabacion.wait()
            self.send_message(b'stop ffmpeg:')
            #time.sleep(10)
            self.builder.get_object("grabar").set_label('Grabar')
            self.grabacion = None
            if self.builder.get_object("subir_videos").get_active():
                # Se sube el archivo a la nube
                print("Subiendo al servidor...")
                thread = threading.Thread(target=self.subir_al_servidor)
                thread.daemon = True
                thread.start()
                self.hilos.append(thread)
            return
        if self.credenciales_modificadas and self.builder.get_object("subir_videos").get_active():
            dialog = Gtk.MessageDialog(
                transient_for=self.builder.get_object("window"),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="ERROR: Debe comprobar las credenciales",
            )
            dialog.format_secondary_text(
                "Debe verificar que las credenciales son correctas. Pulse el boton de comprobar credenciales."
            )
            dialog.run()
            dialog.destroy()
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
        #archivo = '{0}/{1}'.format(carpeta, fecha.isoformat(sep=' ', timespec='seconds').replace(':', '·'))
        archivo = '{0}/{1}'.format(carpeta, fecha.isoformat(sep=' ').replace(':', '·').split('.')[0])
        self.archivo_actual = '{0}.mp4'.format(archivo)
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


    def onComprobarCredenciales(self, button):
        if not self.builder.get_object("subir_videos").get_active():
            dialog = Gtk.MessageDialog(
                transient_for=self.builder.get_object("window"),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="ERROR: Debe activar la subida de vídeos",
            )
            dialog.format_secondary_text(
                "Para poder comprobar las credenciales, debe activar la subida de vídeos."
            )
            dialog.run()
            dialog.destroy()
            return
        # Se deben comprobar que las credenciales de conexión a EducaMadrid son correctas
        # y que el servidor está activo
        self.credenciales_modificadas = False
        # Servidor activo
        servidor = self.builder.get_object("servidor").get_text()
        r = None
        try:
            #r = requests.post(servidor.strip()+'/cgi-bin/upload.py', data={})
            r = self.check_server()
        except Exception as err:
            self.credenciales_modificadas = True
            dialog = Gtk.MessageDialog(
                transient_for=self.builder.get_object("window"),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="ERROR: No se puede conectar con el servidor",
            )
            dialog.format_secondary_text(
                "Verifique que la dirección del servidor es la correcta y que el servidor está activo. Verifique que el equipo puede navegar correctamente."
            )
            dialog.run()
            dialog.destroy()
        if r:
            # Servidor activo
            # Se comprueban las credenciales de owncloud
            oc = None
            try:
                oc = owncloud.Client('http://cloud.educa.madrid.org', dav_endpoint_version = 10)
                usuario = self.builder.get_object("login").get_text().strip()
                password = self.builder.get_object("password").get_text()
                oc.login(usuario, password)
            except Exception as err:
                self.credenciales_modificadas = True
            # Se comparten en la nube y se envían los enlaces por correo, sólo si se pasa la opción "enviar" por línea de comandos:
            if oc == None:
                self.credenciales_modificadas = True
            if self.credenciales_modificadas:
                dialog = Gtk.MessageDialog(
                    transient_for=self.builder.get_object("window"),
                    flags=0,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="ERROR: Las credenciales no son válidas",
                )
                dialog.format_secondary_text(
                    "Verifique el usuario o contraseña. Verifique que el equipo puede navegar correctamente."
                )
                dialog.run()
                dialog.destroy()
            else:
                dialog = Gtk.MessageDialog(
                    transient_for=self.builder.get_object("window"),
                    flags=0,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.CANCEL,
                    text="Las credenciales son válidas",
                )
                dialog.format_secondary_text(
                    "Las credenciales son válidas."
                )
                dialog.run()
                dialog.destroy()
        else:
            self.credenciales_modificadas = True
            dialog = Gtk.MessageDialog(
                transient_for=self.builder.get_object("window"),
                flags=0,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.CANCEL,
                text="ERROR: No se puede conectar con el servidor",
            )
            dialog.format_secondary_text(
                "Verifique que la dirección del servidor es la correcta y que el servidor está activo. Verifique que el equipo puede navegar correctamente."
            )
            dialog.run()
            dialog.destroy()


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

    def check_server(self):
        ok = False
        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect the socket to the port where the server is listening
        servidor = self.builder.get_object("servidor").get_text()
        if ':' in servidor:
            try:
                server_address = (servidor.split(':')[0], int(servidor.split(':')[1]))
                print('connecting to {} port {}'.format(*server_address))
                sock.connect(server_address)
                # Send data
                message = b'\n'
                print('sending {!r}'.format(message))
                sock.sendall(message)
                ok = True
            except Exception as err:
                print('Error:', err)
            finally:
                print('closing socket')
                sock.close()
        return ok

    def subir_al_servidor(self):
        print("Subiendo al servidor...")
        servidor = self.builder.get_object("servidor").get_text()
        login = self.builder.get_object("login").get_text()
        password = self.builder.get_object("password").get_text()
        curso = self.builder.get_object("curso").get_text()
        #with open(self.archivo_actual, 'rb') as f:
        #    r = requests.post(servidor.strip()+'/cgi-bin/upload.py',
        #        data={'login': login, 'password': password, 'ruta': '/CLASES/{0}'.format(curso)},
        #        files={'file': f})
        #    print(r.text)
        #time.sleep(10)

        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect the socket to the port where the server is listening
        servidor = self.builder.get_object("servidor").get_text()
        if ':' in servidor:
            try:
                server_address = (servidor.split(':')[0], int(servidor.split(':')[1]))
                print('connecting to {} port {}'.format(*server_address))
                sock.connect(server_address)
                # Send data
                message = 'login={0}\n'.format(login)
                sock.sendall(message.encode())
                message = 'password={0}\n'.format(password)
                sock.sendall(message.encode())
                message = 'ruta=/CLASES/{0}\n'.format(curso)
                sock.sendall(message.encode())
                message = 'filename={0}\n'.format(self.archivo_actual)
                sock.sendall(message.encode())
                sock.sendall(b'####\n')
                fin = open(self.archivo_actual, 'rb')
                while True:
                    data = fin.read(16)
                    #print(data)
                    if data:
                        sock.sendall(data)
                    else:
                        break
                fin.close()
            except Exception as err:
                print('Error en cliente:', err)
            finally:
                print('closing socket')
                sock.close()

        print("Fin de la subida")
        if self.mostrar_mensaje_fin_subida:
            GLib.idle_add(self.onMensajeFinSubida)


#include main_glade main.glade

builder = Gtk.Builder()
#builder.add_from_string(main_glade)
builder.add_from_file('main.glade')
builder.connect_signals(Handler(builder))

window = builder.get_object("window")
window.show_all()

Gtk.main()
