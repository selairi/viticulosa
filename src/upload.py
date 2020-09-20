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

#import cgi, cgitb
import os, sys
import time
import random
import fcntl
import owncloud
import socket

#cgitb.enable()

UPLOAD_DIR = '../server/uploads'
COMPRIMIDOS_DIR = '../server/comprimidos'
CAPACIDAD_NUBE = 2000000000 # 2Gb
#CAPACIDAD_NUBE =  4000000*2
MUTEX_SUBIDA = ["../server/mutex_subida1.lck", "../server/mutex_subida2.lck"]
MUTEX_COMPRESION_VIDEO = ["../server/mutex_compresion1.lck", "../server/mutex_compresion2.lck"]


class Parser:
    def __init__(self):
        self.line = bytearray()
        self.archivo = None
        self.quit = False
        self.parametro = {}
        self.uploaded_file_path = None

    def close(self):
        if self.archivo:
            self.archivo.flush()
            self.archivo.close()

    def feed(self, data):
        if not self.archivo:
            n = 0
            for ch in data:
                n += 1
                #print(ch)
                if ch == 10: # ch == '\n'
                    print('Procesando línea:')
                    self.linea()
                    self.line = bytearray()
                    if self.archivo:
                        print('Almacenando: ', data[n:])
                        self.archivo.write(data[n:])
                        #self.archivo.write(b'--------------')
                        break
                else:
                    self.line.append(ch)
        else:
            self.archivo.write(data)

    def linea(self):
        line = self.line.strip()
        if line.startswith(b'echo:'):
            print('Cerrando servidor')
            self.quit =True
        elif b'=' in line:
            comando = line.decode().split('=')
            self.parametro[comando[0].strip()] = comando[1].strip()
        elif line.startswith(b'####'):
            # Se comienza la subida de un archivo
            if 'filename' in self.parametro.keys():
                self.uploaded_file_path = os.path.join(UPLOAD_DIR, '{0}-{1}'.format(self.parametro['login'], os.path.basename(self.parametro['filename'])))
                print('Cargando archivo:', self.uploaded_file_path)
                self.archivo = open(self.uploaded_file_path, 'wb')
        else:
            print("Mensaje no conocido:")
            print(self.line)
            print()




def save_uploaded_file():
    print('Content-Type: text/html; charset=UTF-8')
    print()
    print("""
        <html>
        <head>
          <title>Upload File</title>
        </head>
        <body>
        """)

    form = cgi.FieldStorage()
    if 'file' not in form:
        print('<h1>Not found parameter: file</h1>')
        return

    if 'login' not in form:
        print('<h1>Not found parameter: login</h1>')
        return

    if 'password' not in form:
        print('<h1>Not found parameter: password</h1>')
        return

    if 'ruta' not in form:
        print('<h1>Not found parameter: ruta</h1>')
        return

    form_file = form['file']
    if not form_file.file:
        print('<h1>Not found parameter: file</h1>')
        return

    if not form_file.filename:
        print('<h1>Not found parameter: file</h1>')
        return

    uploaded_file_path = os.path.join(UPLOAD_DIR, '{0}-{1}'.format(form['login'].value, os.path.basename(form_file.filename)))
    fout=open(uploaded_file_path, 'wb')
    n = 0
    while True:
        chunk = form_file.file.read(100000)
        if not chunk:
            break
        fout.write (chunk)
        n += 1
    fout.close()
    print('<h1>Completed file upload</h1>')
    print(uploaded_file_path)
    print()
    print(n)
    print("""
        <hr>
        <a href="../upload.html">Back to upload page</a>

        """)
    # El archivo ha sido subido al servidor, se comienza a procesar
    sys.stdout.flush()
    sys.stdout = open('salida.txt','w')
    #sys.stderr = open('errores.txt','w')
    newpid = os.fork()
    #newpid = 0
    if newpid == 0:
        # Se crea un proceso hijo encargado de subir el archivo a la nube
        sys.stderr.write('Procesando...\n')
        comprimido_file_path = compresion_video(uploaded_file_path)
        print('Se inicia procesar')
        mutex = Locker(MUTEX_SUBIDA)
        ok = -1
        intentos = 50
        while ok != 0 and intentos > 0:
            if mutex.entrar():
                try:
                    ok = procesar(form['login'].value, form['password'].value, form['ruta'].value, comprimido_file_path, form_file.filename)
                except Exception as err:
                    sys.stderr.write("Error: {0}\n".format(err))
                    #sys.stderr.write(err)
                mutex.salir()
                if ok == 2: # Error en las credenciales
                    sys.stderr.write("Error en las credenciales de usuario o en la conexión con owncloud.\n")
                    break
                if ok != 0:
                    # Cuando se produce un error, se espera un tiempo aleatorio antes de volver a intentarlo
                    time.sleep(random.randint(3, 10))
            intentos -= 1
        exit(ok)
    else:
        sys.stderr.write('Cerrando el proceso padre\n')
        exit(0) # Se termina el proceso padre



# Funciones útiles para manejar owncloud
# Verifica si un archivo existe en la nube
def owncloud_exists(oc, ruta):
	file_info = None
	try:
		file_info = oc.file_info(ruta)
	except owncloud.owncloud.HTTPResponseError as res:
		#print('La ruta no existe', res)
		pass
	return file_info

# Crea todas las subcarpetas de la ruta dada
def owncloud_mkdir(oc, path):
	ruta = ''
	for p in path.split('/'):
		ruta += '/' + p
		print(ruta)
		file_info = owncloud_exists(oc, ruta)
		if file_info == None:
		    oc.mkdir(ruta)


# Mutex para no permitir que varios procesos hagan la subida a la vez
class Locker:
    def __init__(self, archivos):
        n = random.randint(0, len(archivos) - 1)
        self.archivo = archivos[n]

    def entrar(self):
        sys.stderr.write('Acquiriendo el candado...\n')
        self.fp = open(self.archivo, "w")
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
        return True

    def salir(self):
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
        self.fp.close()
        sys.stderr.write('Cerrando el candado...\n')


def procesar(usuario, password, ruta, uploaded_file_path, filename):
    # Se intenta adquirir el mutex para entrar en la sección crítica
    sys.stderr.write('Dentro de procesar...\n')
    sys.stderr.flush()

    oc = None

    # Se conecta con la nube
    print('Conectado con owncloud...')
    sys.stdout.flush()
    try:
        oc = owncloud.Client('http://cloud.educa.madrid.org', dav_endpoint_version = 10)
        oc.login(usuario, password)
    except Exception as err:
        sys.stderr.write("Error: {0}\n".format(err))
        return 2
    sys.stderr.write('Conectado')
    # Se comparten en la nube y se envían los enlaces por correo, sólo si se pasa la opción "enviar" por línea de comandos:
    if oc != None:
        # Se crea una carpeta si no existe
        owncloud_mkdir(oc, ruta)

        # Se borran archivos de la nube si no se tiene espacio necesario para borrar
        print('Se borran archivos de la nube si no se tiene espacio necesario para borrar')
        archivo_nube = '{0}/{1}'.format(ruta, os.path.basename(filename))
        borrar_archivos_cola_nube(oc, uploaded_file_path, archivo_nube)

        # Se sube el archivo a la nube
        print('Se sube el archivo a la nube', uploaded_file_path, "\tRuta", archivo_nube)
        ok = oc.put_file(archivo_nube, uploaded_file_path)
        if not ok:
            # Se espera un tiempo aleatorio antes de volver a intentar la subida
            #time.sleep(random.randint(3, 10))
            print('Error al subir el archivo')
            pass
        else:
            print('Archivo subido')
            archivos_nube = oc.get_file_contents("/CLASES/archivos.txt").decode("utf-8")
            bytes_video = os.path.getsize(uploaded_file_path)
            archivos_nube += '{0}\t{1}\n'.format(archivo_nube, bytes_video)
            oc.put_file_contents("/CLASES/archivos.txt", archivos_nube.encode())
            os.unlink(uploaded_file_path)
            oc.logout()
            return 0
    else:
        sys.stderr.write("Error al conectar con owncloud")
    if oc != None:
        oc.logout()
    return 1



def borrar_archivos_cola_nube(oc, uploaded_file_path, archivo_nube):
    # Se descarga la lista de archivos de la nube y se borran los suficientes para que se pueda subir el vídeo
    bytes_video = os.path.getsize(uploaded_file_path)
    archivos_nube = ""
    sys.stderr.write('Se verifica que existe el archivo clases')
    sys.stderr.flush()
    if owncloud_exists(oc, "/CLASES/archivos.txt"):
        archivos_nube = oc.get_file_contents("/CLASES/archivos.txt").decode("utf-8")
    else:
        sys.stderr.write('Creando clases')
        owncloud_mkdir(oc, "/CLASES")
    archivos_finales = ""
    capacidad_libre = CAPACIDAD_NUBE
    sys.stderr.write(archivos_nube)
    sys.stderr.write("{0}".format(len(archivos_nube.split('\n'))))
    for archivo in archivos_nube.split('\n'):
        if len(archivo.strip().split("\t")) > 1:
            print(archivo.strip().split("\t"))
            [nombre, tamagno] = archivo.strip().split("\t")
            capacidad_libre -= int(tamagno)

    # Se borran archivos hasta que haya capacidad en la nube
    for archivo in archivos_nube.split('\n'):
        if len(archivo.split("\t")) > 1:
            [nombre, tamagno] = archivo.split("\t")
            # Se borran archivos si no hay capacidad o ya estaba en la nube
            sys.stderr.write('\n--{0}--\t--{1}-- {2}\n'.format(nombre, archivo_nube, nombre == archivo_nube))
            if capacidad_libre < bytes_video or nombre == archivo_nube:
                capacidad_libre += int(tamagno)
                if owncloud_exists(oc, nombre):
                    oc.delete(nombre)
                sys.stderr.write('\nEliminando --{0}--\t--{1}--\n'.format(nombre, archivo_nube))
            else:
                archivos_finales += '{0}\n'.format(archivo)

    oc.put_file_contents("/CLASES/archivos.txt", archivos_finales.encode())


def compresion_video(uploaded_file_path):
    mutex = Locker(MUTEX_COMPRESION_VIDEO)
    mutex.entrar()
    # Se obtiene el tamaño del vídeo
    comando = 'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of default=nw=1 "{0}"'.format(uploaded_file_path)
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
    filename = os.path.basename(uploaded_file_path)
    comprimido_file_path = '{0}/{1}'.format(COMPRIMIDOS_DIR, filename)
    comando = 'ffmpeg -i "{0}" {1} -vcodec libx264 -crf 30 "{2}" > /dev/stderr'.format(uploaded_file_path, calidad, comprimido_file_path)
    os.system(comando)
    sys.stderr.write('\n{0}\n'.format(comando))
    mutex.salir()
    os.unlink(uploaded_file_path)
    return comprimido_file_path



##################################################3
# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port
server_address = ('0.0.0.0', 8000)
print('starting up on {} port {}'.format(*server_address))
sock.bind(server_address)

# Listen for incoming connections
sock.listen()

while True:
    # Wait for a connection
    print('waiting for a connection')
    connection, client_address = sock.accept()
    print('connection from', client_address)
    try:
        newpid = os.fork()
        #newpid = 0
        if newpid == 0:

            parser = Parser()

            # Receive the data in small chunks and retransmit it
            while True:
                data = connection.recv(16)
                #print('received {!r}'.format(data))
                if data:
                    parser.feed(data)
                    if parser.quit:
                        connection.sendall(data)
                        parser.quit = False
                else:
                    print('no data from', client_address)
                    parser.close()
                    if parser.uploaded_file_path:
                        # Se sube el archivo a la nube
                        print('Procesando...\n')
                        comprimido_file_path = compresion_video(parser.uploaded_file_path)
                        print('Se inicia procesar')
                        mutex = Locker(MUTEX_SUBIDA)
                        ok = -1
                        intentos = 5
                        while ok != 0 and intentos > 0:
                            if mutex.entrar():
                                try:
                                    ok = procesar(parser.parametro['login'], parser.parametro['password'], parser.parametro['ruta'], comprimido_file_path, parser.parametro['filename'])
                                except Exception as err:
                                    sys.stderr.write("Error: {0}\n".format(err))
                                    #sys.stderr.write(err)
                                mutex.salir()
                                if ok == 2: # Error en las credenciales
                                    sys.stderr.write("Error en las credenciales de usuario o en la conexión con owncloud.\n")
                                    break
                                if ok != 0:
                                    # Cuando se produce un error, se espera un tiempo aleatorio antes de volver a intentarlo
                                    time.sleep(random.randint(3, 10))
                            intentos -= 1
                    exit(0)
    finally:
        # Clean up the connection
        connection.close()
