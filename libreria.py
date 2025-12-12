import sys, os, json, re
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


def leer_ficheros_txt_dict():
    """
    Devuelve un dict {nombre: contenido} con TODOS los .txt del directorio actual.
    """
    ficheros = {}
    for nombre in sorted(os.listdir(".")):
        if os.path.isfile(nombre) and nombre.lower().endswith(".txt"):
            try:
                with open(nombre, "r", encoding="utf-8", errors="replace") as f:
                    contenido = f.read()
            except Exception:
                contenido = "[NO SE PUEDE LEER]"
            ficheros[nombre] = contenido
    return ficheros


def dict_ficheros_a_html(dic_ficheros):
    """
    Convierte un dict {nombre: contenido} en un texto HTML tipo:

    <u>fichero1.txt</u>:
    ...
    <u>fichero2.txt</u>:
    ...
    """
    if not dic_ficheros:
        return ""

    partes = []
    for nombre in sorted(dic_ficheros.keys()):
        contenido = dic_ficheros[nombre].strip()
        partes.append(f"<u>{nombre}</u>:\n{contenido}")
    return "\n".join(partes)


# ╔════════════ 1) CARGAR PARÁMETROS DESDE QUESTION.parameters ═╗

def cargar_parametros(contexto, params_raw):
    """
    Lee QUESTION.parameters (JSON) y rellena las claves básicas de CONTEXTO.
    Normaliza:
      - entrada_estandar -> lista de dicts (0, 1 o varios)
      - argumentos       -> lista de dicts (0, 1 o varios)
    """
    contexto = dict(contexto)

    try:
        datos = json.loads(params_raw) if params_raw and params_raw.strip() else {}
        if datos is None:
            datos = {}
    except Exception:
        datos = {}

    contexto["ejercicio"] = datos.get("ejercicio", "ejercicio_sin_nombre")
    contexto["tipo"] = datos.get("tipo", "programa")

    # Nombres de funciones (para tipo "funcion")
    contexto["nombre_funcion_patron"] = datos.get("nombre_funcion_patron", "sol_patron")
    contexto["nombre_funcion_alumno"] = datos.get("nombre_funcion_alumno", "resolver")
    contexto["nombre_funcion"] = contexto["nombre_funcion_alumno"]

    # --- entrada_estandar: SIEMPRE lista de diccionarios ---
    spec_in = datos.get("entrada_estandar")
    if spec_in is None:
        contexto["spec_entrada_estandar"] = []
    elif isinstance(spec_in, list):
        contexto["spec_entrada_estandar"] = spec_in
    else:
        contexto["spec_entrada_estandar"] = [spec_in]

    # --- ficheros_entrada: lista de diccionarios ---
    contexto["spec_ficheros_entrada"] = datos.get("ficheros_entrada", [])

    # --- argumentos: SIEMPRE lista de diccionarios (para funciones) ---
    spec_args = datos.get("argumentos")
    if spec_args is None:
        contexto["spec_argumentos"] = []
    elif isinstance(spec_args, list):
        contexto["spec_argumentos"] = spec_args
    else:
        contexto["spec_argumentos"] = [spec_args]

    # --- ficheros_salida: qué ficheros se deben comparar (opcional) ---
    contexto["ficheros_salida"] = datos.get("ficheros_salida", None)

    contexto["restricciones"] = datos.get("restricciones", {})

    return contexto


# ╔════════════ 1b) RESTRICCIONES CÓDIGO ALUMNO ════════════════╗

def comprobar_restricciones(contexto, codigo_alumno):
    """
    Comprueba las restricciones definidas en contexto["restricciones"]
    sobre el código fuente del alumno (cadena completa).
    """
    contexto = dict(contexto)

    restricciones = contexto.get("restricciones", {}) or {}
    violaciones = []

    # quitar comentarios simples para evitar falsos positivos
    lineas_sin_coment = []
    for line in codigo_alumno.splitlines():
        if "#" in line:
            line = line.split("#", 1)[0]
        lineas_sin_coment.append(line)
    codigo_limpio = "\n".join(lineas_sin_coment)

    def contiene(palabra: str) -> bool:
        return palabra in codigo_limpio

    if restricciones.get("prohibir_import"):
        if contiene("import "):
            violaciones.append("Uso de 'import' no permitido.")

    if restricciones.get("prohibir_while"):
        if contiene("while "):
            violaciones.append("Uso de bucles 'while' no permitido.")

    if restricciones.get("prohibir_for"):
        if contiene("for "):
            violaciones.append("Uso de bucles 'for' no permitido.")

    if restricciones.get("prohibir_eval"):
        if contiene("eval("):
            violaciones.append("Uso de 'eval' no permitido.")

    if restricciones.get("prohibir_exec"):
        if contiene("exec("):
            violaciones.append("Uso de 'exec' no permitido.")

    if not violaciones:
        contexto["bloquear_ejecucion"] = False
        contexto["codigo_alumno"] = codigo_alumno
        return contexto

    lista_html = "".join(f"<li>{msg}</li>" for msg in violaciones)
    html = (
        "<b>No se ha podido ejecutar tu código porque incumple las restricciones del ejercicio:</b>"
        "<ul>"
        f"{lista_html}"
        "</ul>"
    )

    contexto["bloquear_ejecucion"] = True
    contexto["award"] = 0.0
    contexto["html"] = html

    resultado = {
        "fraction": 0.0,
        "prologuehtml": html
    }
    contexto["resultado"] = json.dumps(resultado)

    return contexto


# ╔════════════ 2) GENERADORES DE DATOS (PROGRAMAS/FUNCIONES) ══╗

def _gen_entero(spec):
    minimo = spec.get("min", 1)
    maximo = spec.get("max", 100)
    return f"{r.randint(minimo, maximo)}\n"


def _gen_dos_enteros(spec):
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
    separador = spec.get("separador", "espacio")

    numeros = [str(r.randint(minimo, maximo)) for _ in range(cantidad)]

    if separador == "linea":
        return "\n".join(numeros) + "\n"
    else:
        return " ".join(numeros) + "\n"


def _generar_desde_spec(spec):
    """
    Para entrada estándar y ficheros: devuelve una CADENA.
    """
    if not isinstance(spec, dict):
        return f"{r.randint(1, 100)}\n"

    gen = spec.get("generador")

    if gen == "entero":
        return _gen_entero(spec)

    if gen == "dos_enteros":
        return _gen_dos_enteros(spec)

    if gen == "lista_enteros":
        return _gen_lista_enteros(spec)

    return f"{r.randint(1, 100)}\n"


def _generar_valor_desde_spec(spec):
    """
    Para argumentos de funciones: devuelve un VALOR Python (int, etc.).
    """
    if not isinstance(spec, dict):
        return r.randint(1, 100)

    gen = spec.get("generador")

    if gen == "entero":
        minimo = spec.get("min", 1)
        maximo = spec.get("max", 100)
        return r.randint(minimo, maximo)

    return r.randint(1, 100)


def preparar_contexto(contexto):
    """
    Genera:
      - entrada_estandar (cadena)
      - ficheros_entrada (dict nombre -> contenido)
      - argumentos (lista de valores, para funciones)
    """
    contexto = dict(contexto)

    # entrada estándar
    lista_specs = contexto.get("spec_entrada_estandar", [])
    if not lista_specs:
        contexto["entrada_estandar"] = f"{r.randint(1, 100)}\n"
    else:
        partes = []
        for spec in lista_specs:
            partes.append(_generar_desde_spec(spec))
        contexto["entrada_estandar"] = "".join(partes)

    # ficheros de entrada
    contexto["ficheros_entrada"] = {}
    for spec_f in contexto.get("spec_ficheros_entrada", []):
        if not isinstance(spec_f, dict):
            continue
        nombre = spec_f.get("nombre")
        if not nombre:
            continue
        contenido = _generar_desde_spec(spec_f)
        contexto["ficheros_entrada"][nombre] = contenido

    # argumentos para funciones
    args_specs = contexto.get("spec_argumentos", [])
    argumentos = []
    for spec in args_specs:
        argumentos.append(_generar_valor_desde_spec(spec))
    contexto["argumentos"] = argumentos

    return contexto


# ╔════════════ 3) ENTORNO PATRÓN (PROGRAMAS) ══════════════════╗

def preparar_entorno_patron(contexto):
    contexto = dict(contexto)

    patron_out = StringIO()
    contexto["_patron_out"] = patron_out

    sys.stdout = patron_out
    sys.stdin = StringIO(contexto.get("entrada_estandar", ""))

    crear_ficheros(contexto.get("ficheros_entrada", {}))

    return contexto


def finalizar_entorno_patron(contexto):
    contexto = dict(contexto)

    patron_out = contexto.get("_patron_out")
    if patron_out is not None:
        contexto["salida_patron"] = patron_out.getvalue()
    else:
        contexto["salida_patron"] = ""

    dic = leer_ficheros_txt_dict()
    contexto["ficheros_patron_dict"] = dic
    contexto["ficheros_patron_html"] = dict_ficheros_a_html(dic)

    return contexto


# ╔════════════ 4) ENTORNO ALUMNO (PROGRAMAS) ══════════════════╗

def preparar_entorno_alumno(contexto):
    contexto = dict(contexto)

    alumno_out = StringIO()
    contexto["_alumno_out"] = alumno_out

    sys.stdout = alumno_out
    sys.stdin = StringIO(contexto.get("entrada_estandar", ""))

    crear_ficheros(contexto.get("ficheros_entrada", {}))

    return contexto


def finalizar_entorno_alumno(contexto):
    contexto = dict(contexto)

    alumno_out = contexto.get("_alumno_out")
    if alumno_out is not None:
        contexto["salida_alumno"] = alumno_out.getvalue()
    else:
        contexto["salida_alumno"] = ""

    dic = leer_ficheros_txt_dict()
    contexto["ficheros_alumno_dict"] = dic
    contexto["ficheros_alumno_html"] = dict_ficheros_a_html(dic)

    sys.stdout = sys.__stdout__

    return contexto


# ╔════════════ 5) EVALUAR PROGRAMAS ═══════════════════════════╗

def evaluar_programas(contexto):
    """
    Compara salida_patron / salida_alumno y ficheros (modo programa).
    Usa dicts de ficheros si están presentes.
    """
    contexto = dict(contexto)

    salida_patron = contexto.get("salida_patron", "").strip()
    salida_alumno = contexto.get("salida_alumno", "").strip()

    dic_pat = contexto.get("ficheros_patron_dict", {})
    dic_alu = contexto.get("ficheros_alumno_dict", {})

    specs_salida = contexto.get("ficheros_salida", None)

    if specs_salida:
        nombres = [spec.get("nombre") for spec in specs_salida if isinstance(spec, dict)]
        dic_pat_cmp = {n: dic_pat.get(n, "") for n in nombres}
        dic_alu_cmp = {n: dic_alu.get(n, "") for n in nombres}
    else:
        nombres = sorted(dic_pat.keys())
        dic_pat_cmp = {n: dic_pat.get(n, "") for n in nombres}
        dic_alu_cmp = {n: dic_alu.get(n, "") for n in nombres}

    hay_ficheros = bool(dic_pat_cmp or dic_alu_cmp)
    ficheros_iguales = (dic_pat_cmp == dic_alu_cmp)

    if not hay_ficheros:
        coincide = (salida_alumno == salida_patron)
    else:
        coincide = (salida_alumno == salida_patron) and ficheros_iguales

    award = 1.0 if coincide else 0.0

    contexto["coinciden"] = coincide
    contexto["award"] = award
    contexto["ficheros_comparados"] = nombres

    return contexto


# ╔════════════ 6) EVALUAR FUNCIONES ═══════════════════════════╗

def evaluar_funciones(contexto, gbls):
    contexto = dict(contexto)

    nom_pat = contexto.get("nombre_funcion_patron")
    nom_alu = contexto.get("nombre_funcion_alumno")
    args = contexto.get("argumentos", [])

    f_pat = gbls.get(nom_pat)
    f_alu = gbls.get(nom_alu)

    if f_pat is None or f_alu is None:
        contexto["salida_patron"] = f"[No se encontró la función patrón '{nom_pat}']"
        contexto["salida_alumno"] = f"[No se encontró la función alumna '{nom_alu}']"
        contexto["ficheros_patron_dict"] = {}
        contexto["ficheros_alumno_dict"] = {}
        contexto["ficheros_patron_html"] = ""
        contexto["ficheros_alumno_html"] = ""
        contexto["coinciden"] = False
        contexto["award"] = 0.0
        return contexto

    try:
        res_pat = f_pat(*args)
    except Exception as e:
        contexto["salida_patron"] = f"[Error ejecutando patrón: {e}]"
        contexto["salida_alumno"] = ""
        contexto["ficheros_patron_dict"] = {}
        contexto["ficheros_alumno_dict"] = {}
        contexto["ficheros_patron_html"] = ""
        contexto["ficheros_alumno_html"] = ""
        contexto["coinciden"] = False
        contexto["award"] = 0.0
        return contexto

    try:
        res_alu = f_alu(*args)
    except Exception as e:
        contexto["salida_patron"] = repr(res_pat)
        contexto["salida_alumno"] = f"[Error ejecutando función del alumno: {e}]"
        contexto["ficheros_patron_dict"] = {}
        contexto["ficheros_alumno_dict"] = {}
        contexto["ficheros_patron_html"] = ""
        contexto["ficheros_alumno_html"] = ""
        contexto["coinciden"] = False
        contexto["award"] = 0.0
        return contexto

    coincide = (res_alu == res_pat)
    award = 1.0 if coincide else 0.0

    contexto["salida_patron"] = repr(res_pat)
    contexto["salida_alumno"] = repr(res_alu)
    contexto["ficheros_patron_dict"] = {}
    contexto["ficheros_alumno_dict"] = {}
    contexto["ficheros_patron_html"] = ""
    contexto["ficheros_alumno_html"] = ""
    contexto["coinciden"] = coincide
    contexto["award"] = award

    return contexto


# ╔════════════ 7) CONSTRUIR RESULTADO (HTML + JSON) ═══════════╗

def construir_resultado(contexto):
    contexto = dict(contexto)

    tipo = contexto.get("tipo", "programa")

    salida_patron = contexto.get("salida_patron", "")
    salida_alumno = contexto.get("salida_alumno", "")
    ficheros_patron_html = contexto.get("ficheros_patron_html", "")
    ficheros_alumno_html = contexto.get("ficheros_alumno_html", "")
    award = contexto.get("award", 0.0)

    if tipo == "funcion":
        argumentos = contexto.get("argumentos", [])
        args_str = ", ".join(repr(a) for a in argumentos)

        html = (
            "<b>Evaluación de función</b><br>"
            f"<b>Argumentos usados:</b> <pre>{args_str}</pre>"
            "<table style='width:100%; border-collapse:collapse; margin-top:0.5em;'>"
            "<tr>"
            "  <th style='width:50%; text-align:left;'><b>FUNCIÓN ALUMNO</b></th>"
            "  <th style='width:50%; text-align:left;'><b>FUNCIÓN CORRECTA</b></th>"
            "</tr>"
            "<tr>"
            "  <td style='vertical-align:top; border-right:1px solid #ccc;'>"
            "    <b>Valor devuelto</b><br>"
            "    <pre>" + salida_alumno + "</pre>"
            "  </td>"
            "  <td style='vertical-align:top;'>"
            "    <b>Valor devuelto</b><br>"
            "    <pre>" + salida_patron + "</pre>"
            "  </td>"
            "</tr>"
            "</table>"
        )

    elif ficheros_alumno_html == "" and ficheros_patron_html == "":
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
            "    <pre>" + ficheros_alumno_html + "</pre>"
            "  </td>"
            "  <td style='vertical-align:top;'>"
            "    <b>Pantalla</b><br>"
            "    <pre>" + salida_patron + "</pre>"
            "    <b>Ficheros</b><br>"
            "    <pre>" + ficheros_patron_html + "</pre>"
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
