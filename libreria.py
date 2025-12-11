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
    Si hay error en el JSON, aplica valores por defecto.
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

    # "spec" de generación de datos
    contexto["spec_entrada_estandar"] = datos.get("entrada_estandar")
    contexto["spec_ficheros_entrada"] = datos.get("ficheros_entrada", [])
    contexto["spec_argumentos"] = datos.get("argumentos")

    contexto["restricciones"] = datos.get("restricciones", {})

    return contexto


# ╔════════════ 2) GENERADORES DE DATOS SEGÚN SPEC ═════════════╗

def _generar_desde_spec(spec):
    """
    Dada una spec (dict) con al menos la clave 'generador',
    devuelve una cadena de texto (para stdin o contenido de fichero).
    Versión inicial con un solo generador real ('entero') y un fallback.
    """
    if not isinstance(spec, dict):
        # Fallback: comportamiento antiguo
        return f"{r.randint(1, 100)}\n"

    gen = spec.get("generador")

    # ── Generador 'entero': un entero en [min, max] + salto de línea
    if gen == "entero":
        minimo = spec.get("min", 1)
        maximo = spec.get("max", 100)
        return f"{r.randint(minimo, maximo)}\n"

    # Aquí más adelante añadiremos otros generadores:
    # 'dos_enteros', 'lista_enteros', 'ciudades', etc.

    # Fallback si el generador no se reconoce:
    return f"{r.randint(1, 100)}\n"


def preparar_contexto(contexto):
    """
    Genera los datos concretos de entrada_estandar, ficheros_entrada y argumentos
    a partir de las 'spec' y del estado de random (ya sembrado en la plantilla).
    """
    contexto = dict(contexto)

    # ── ENTRADA ESTÁNDAR ───────────────────────────────────────
    spec_in = contexto.get("spec_entrada_estandar")
    if spec_in is None:
        # Sin spec: comportamiento antiguo
        contexto["entrada_estandar"] = f"{r.randint(1, 100)}\n"
    else:
        contexto["entrada_estandar"] = _generar_desde_spec(spec_in)

    # ── FICHEROS DE ENTRADA ────────────────────────────────────
    contexto["ficheros_entrada"] = {}
    for spec_f in contexto.get("spec_ficheros_entrada", []):
        if not isinstance(spec_f, dict):
            continue
        nombre = spec_f.get("nombre")
        if not nombre:
            continue
        contenido = _generar_desde_spec(spec_f)
        contexto["ficheros_entrada"][nombre] = contenido

    # ── ARGUMENTOS PARA FUNCIONES (por ahora sin usar) ─────────
    # Más adelante: generar estructura (lista/tupla) en función de la spec.
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
