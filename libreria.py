import sys, os, json
from io import StringIO
import random as r


# ╔════════════ UTILIDADES DE FICHEROS ═════════════════════════╗

def crear_ficheros(dic_ficheros):
    """
    Crea ficheros de texto a partir de un dict {nombre: contenido}.
    """
    if not dic_ficheros:
        return
    for nombre, contenido in dic_ficheros.items():
        with open(nombre, "w", encoding="utf-8") as f:
            f.write(contenido)


def leer_ficheros_txt():
    """
    Devuelve un solo string con el contenido de todos los .txt
    del directorio actual, ordenados por nombre.
    """
    partes = []
    for nombre in sorted(os.listdir(".")):
        if os.path.isfile(nombre) and nombre.lower().endswith(".txt"):
            try:
                with open(nombre, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
            except Exception:
                contenido = "[NO SE PUEDE LEER]"
            partes.append(f"<u>{nombre}</u>:\n{contenido.strip()}")
    return "\n".join(partes)


# ╔════════════ 1) CARGAR PARÁMETROS DESDE QUESTION.parameters ═╗

def cargar_parametros(contexto, params_raw):
    """
    Lee QUESTION.parameters (JSON) y rellena las claves básicas de CONTEXTO.
    Se normaliza:
      - entrada_estandar -> lista de dicts (0, 1 o varios)
    """
    contexto = dict(contexto)

    try:
        datos = json.loads(params_raw) if params_raw and params_raw.strip() else {}
        if datos is None:  # por si viene "null"
            datos = {}
    except Exception:
        datos = {}

    contexto["ejercicio"] = datos.get("ejercicio", "ejercicio_sin_nombre")
    contexto["tipo"] = datos.get("tipo", "programa")
    contexto["nombre_funcion"] = datos.get("nombre_funcion")

    # --- entrada_estandar: SIEMPRE lista de diccionarios ---
    spec_in = datos.get("entrada_estandar")

    if spec_in is None:
        contexto["spec_entrada_estandar"] = []      # sin definición
    elif isinstance(spec_in, list):
        contexto["spec_entrada_estandar"] = spec_in
    else:
        # modo retrocompatible: si el profe puso un dict, lo envolvemos en lista
        contexto["spec_entrada_estandar"] = [spec_in]

    # ficheros_entrada ya es lista de dicts en el JSON
    contexto["spec_ficheros_entrada"] = datos.get("ficheros_entrada", [])
    contexto["spec_argumentos"] = datos.get("argumentos")

    contexto["restricciones"] = datos.get("restricciones", {})

    return contexto



# ╔════════════ 2) GENERADORES DE DATOS SEGÚN SPEC ═════════════╗

def _gen_entero(spec):
    minimo = spec.get("min", 1)
    maximo = spec.get("max", 100)
    return f"{r.randint(minimo, maximo)}\n"


def _gen_dos_enteros(spec):
    # Permite min/max comunes o separados para cada entero
    min_comun = spec.get("min", 1)
    max_comun = spec.get("max", 100)

    min1 = spec.get("min1", min_comun)
    max1 = spec.get("max1", max_comun)
    min2 = spec.get("min2", min_comun)
    max2 = spec.get("max2", max_comun)

    a = r.randint(min1, max1)
    b = r.randint(min2, max2)
    return f"{a} {b}\n"


def _gen_lista_enteros(spec):
    cantidad = spec.get("cantidad", 5)
    minimo = spec.get("min", 0)
    maximo = spec.get("max", 9)
    separador = spec.get("separador", "espacio")  # "espacio" o "linea"

    numeros = [str(r.randint(minimo, maximo)) for _ in range(cantidad)]

    if separador == "linea":
        return "\n".join(numeros) + "\n"
    else:
        # Por defecto: todos en una línea separados por espacio
        return " ".join(numeros) + "\n"


def _generar_desde_spec(spec):
    """
    Dada una spec (dict) con al menos la clave 'generador',
    devuelve una cadena de texto (para stdin o contenido de fichero).
    """
    if not isinstance(spec, dict):
        # Fallback: comportamiento antiguo
        return f"{r.randint(1, 100)}\n"

    gen = spec.get("generador")

    if gen == "entero":
        return _gen_entero(spec)

    if gen == "dos_enteros":
        return _gen_dos_enteros(spec)

    if gen == "lista_enteros":
        return _gen_lista_enteros(spec)

    # Aquí más adelante añadiremos otros generadores:
    # 'texto_ciudades', 'matriz_enteros', etc.

    # Fallback si el generador no se reconoce:
    return f"{r.randint(1, 100)}\n"


def preparar_contexto(contexto):
    """
    Genera los datos concretos de entrada_estandar, ficheros_entrada y argumentos
    a partir de las 'spec' y del estado de random (ya sembrado en la plantilla).

    entrada_estandar:
      - siempre se interpreta como lista de specs (0, 1 o varias)
      - si la lista está vacía -> comportamiento antiguo (entero aleatorio 1..100)
    """
    contexto = dict(contexto)

    # ── ENTRADA ESTÁNDAR (lista de specs) ─────────────────────
    lista_specs = contexto.get("spec_entrada_estandar", [])

    if not lista_specs:
        # Sin specs: fallback antiguo
        contexto["entrada_estandar"] = f"{r.randint(1, 100)}\n"
    else:
        partes = []
        for spec in lista_specs:
            partes.append(_generar_desde_spec(spec))
        contexto["entrada_estandar"] = "".join(partes)

    # ── FICHEROS DE ENTRADA (igual que antes) ─────────────────
    contexto["ficheros_entrada"] = {}
    for spec_f in contexto.get("spec_ficheros_entrada", []):
        if not isinstance(spec_f, dict):
            continue
        nombre = spec_f.get("nombre")
        if not nombre:
            continue
        contenido = _generar_desde_spec(spec_f)
        contexto["ficheros_entrada"][nombre] = contenido

    # ── ARGUMENTOS PARA FUNCIONES (pendiente) ─────────────────
    contexto["argumentos"] = None

    return contexto


# ╔════════════ 3) ENTORNO PATRÓN ══════════════════════════════╗

def preparar_entorno_patron(contexto):
    """
    Redirige stdout y stdin para ejecutar el PATRÓN.
    Crea los ficheros de entrada a partir de contexto["ficheros_entrada"].
    """
    contexto = dict(contexto)

    patron_out = StringIO()
    contexto["_patron_out"] = patron_out

    # Redirigir stdout y stdin
    sys.stdout = patron_out
    sys.stdin = StringIO(contexto.get("entrada_estandar", ""))

    # Crear ficheros de entrada
    crear_ficheros(contexto.get("ficheros_entrada", {}))

    return contexto


def finalizar_entorno_patron(contexto):
    """
    Lee la salida del patrón y los ficheros tras su ejecución.
    (No restaura stdout aún, porque luego lo pisará el entorno del alumno.)
    """
    contexto = dict(contexto)

    patron_out = contexto.get("_patron_out")
    if patron_out is not None:
        contexto["salida_patron"] = patron_out.getvalue()
    else:
        contexto["salida_patron"] = ""

    contexto["ficheros_patron"] = leer_ficheros_txt()

    return contexto


# ╔════════════ 4) ENTORNO ALUMNO ══════════════════════════════╗

def preparar_entorno_alumno(contexto):
    """
    Redirige stdout y stdin para ejecutar el código del alumno.
    Vuelve a crear los ficheros de entrada.
    """
    contexto = dict(contexto)

    alumno_out = StringIO()
    contexto["_alumno_out"] = alumno_out

    sys.stdout = alumno_out
    sys.stdin = StringIO(contexto.get("entrada_estandar", ""))

    crear_ficheros(contexto.get("ficheros_entrada", {}))

    return contexto


def finalizar_entorno_alumno(contexto):
    """
    Lee la salida y los ficheros tras la ejecución del alumno.
    Restaura sys.stdout al final.
    """
    contexto = dict(contexto)

    alumno_out = contexto.get("_alumno_out")
    if alumno_out is not None:
        contexto["salida_alumno"] = alumno_out.getvalue()
    else:
        contexto["salida_alumno"] = ""

    contexto["ficheros_alumno"] = leer_ficheros_txt()

    # Restaurar stdout
    sys.stdout = sys.__stdout__

    return contexto


# ╔════════════ 5) COMPARAR PATRÓN Y ALUMNO ════════════════════╗

def comparar(contexto):
    """
    Compara salida_patron / salida_alumno y ficheros.
    """
    contexto = dict(contexto)

    salida_patron = contexto.get("salida_patron", "").strip()
    salida_alumno = contexto.get("salida_alumno", "").strip()
    ficheros_patron = contexto.get("ficheros_patron", "")
    ficheros_alumno = contexto.get("ficheros_alumno", "")

    if ficheros_alumno == "" and ficheros_patron == "":
        coincide = (salida_alumno == salida_patron)
    else:
        coincide = (salida_alumno == salida_patron) and (ficheros_alumno == ficheros_patron)

    award = 1.0 if coincide else 0.0

    contexto["coinciden"] = coincide
    contexto["award"] = award

    return contexto


# ╔════════════ 6) CONSTRUIR RESULTADO (HTML + JSON) ═══════════╗

def construir_resultado(contexto):
    """
    Construye el HTML de feedback y el JSON final.
    Guarda el JSON en CONTEXTO["resultado"].
    """
    contexto = dict(contexto)

    salida_patron = contexto.get("salida_patron", "")
    salida_alumno = contexto.get("salida_alumno", "")
    ficheros_patron = contexto.get("ficheros_patron", "")
    ficheros_alumno = contexto.get("ficheros_alumno", "")
    award = contexto.get("award", 0.0)

    if ficheros_alumno == "" and ficheros_patron == "":
        html = (
            "<table style='width:100%; border-collapse:collapse;'>"
            "<tr>"
            "  <th style='width:50%; text-align:left;'><b>RESULTADO ALUMNO</b></th>"
            "  <th style='width:50%; text-align:left;'><b>RESULTADO CORRECTO</b></th>"
            "</tr>"
            "<tr>"
            "  <td style='vertical-align:top; border-right:1px solid #ccc;'>"
            "    <b>Pantalla</b><br>"
            "    <pre>" + salida_alumno + "</pre>"
            "  </td>"
            "  <td style='vertical-align:top;'>"
            "    <b>Pantalla</b><br>"
            "    <pre>" + salida_patron + "</pre>"
            "  </td>"
            "</tr>"
            "</table>"
        )
    else:
        html = (
            "<table style='width:100%; border-collapse:collapse;'>"
            "<tr>"
            "  <th style='width:50%; text-align:left;'><b>RESULTADO ALUMNO</b></th>"
            "  <th style='width:50%; text-align:left;'><b>RESULTADO CORRECTO</b></th>"
            "</tr>"
            "<tr>"
            "  <td style='vertical-align:top; border-right:1px solid #ccc;'>"
            "    <b>Pantalla</b><br>"
            "    <pre>" + salida_alumno + "</pre>"
            "    <b>Ficheros</b><br>"
            "    <pre>" + ficheros_alumno + "</pre>"
            "  </td>"
            "  <td style='vertical-align:top;'>"
            "    <b>Pantalla</b><br>"
            "    <pre>" + salida_patron + "</pre>"
            "    <b>Ficheros</b><br>"
            "    <pre>" + ficheros_patron + "</pre>"
            "  </td>"
            "</tr>"
            "</table>"
        )

    contexto["html"] = html

    resultado = {
        "fraction": award,
        "prologuehtml": html
    }

    contexto["resultado"] = json.dumps(resultado)

    return contexto
