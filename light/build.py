
fout = open("viticulosa.py", "w")
fin = open("main.py")
for linea in fin:
    if linea.startswith('#include'):
        args = linea.split()
        variable = args[1]
        archivo = args[2]
        include = open(archivo)
        archivo_texto = include.read()
        include.close()
        fout.write('{0} = """{1}"""\n'.format(variable, archivo_texto))
    else:
        fout.write(linea)
fin.close()
fout.close()