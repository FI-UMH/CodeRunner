def crear_ficheros(FICHEROS):
    for nombre_fichero in FICHEROS.keys():
        with open(nombre_fichero,"w",encoding="utf-8") as f:
            f.write(FICHEROS[nombre_fichero])
    return

def leer_ficheros():
    partes = []
    for nombre in sorted(os.listdir(".")):
        # Solo archivos .txt
        if os.path.isfile(nombre) and nombre.lower().endswith(".txt"):
            try:
                with open(nombre, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
            except Exception:
                contenido = "[NO SE PUEDE LEER]"
            partes.append(f"<u>{nombre}</u>:\n{contenido.strip()}")
    return "\n".join(partes)

def cuadrado1(x):
    return x*x
