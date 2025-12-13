import subprocess, sys, json, os, html, re, hashlib, random

MAX_CHARS = 4000
_ws_re = re.compile(r"[ \t]+")

# =========================================================
# Utilidades generales
# =========================================================

def run_py(code, stdin=""):
    with open("prog.py", "w", encoding="utf8") as f:
        f.write(code)
    try:
        r = subprocess.run(
            [sys.executable, "-B", "prog.py"],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=4
        )
        out = r.stdout or ""
        err = r.stderr or ""
        return out, err
    except subprocess.TimeoutExpired:
        return "", "Timeout expired"

def delete_if_exists(path):
    if os.path.exists(path):
        os.remove(path)

def read_text_file(path):
    if not os.path.exists(path):
        return "[NO EXISTE]"
    with open(path, "r", encoding="utf8", errors="replace") as f:
        data = f.read(MAX_CHARS + 1)
    if len(data) > MAX_CHARS:
        data = data[:MAX_CHARS] + "\n...[TRUNCADO]..."
    return data

def read_file_bytes(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()

# =========================================================
# Comparación flexible de stdout
# =========================================================

def normalize_stdout(s):
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in s.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    lines = [_ws_re.sub(" ", ln) for ln in lines]
    return "\n".join(lines)

# =========================================================
# HTML helpers
# =========================================================

def block(title, content):
    return (
        f"<strong>{html.escape(title)}</strong>\n"
        f"<pre>{html.escape((content or '').rstrip())}</pre>\n"
    )

def mostrar_test_sin_print(testcode):
    s = testcode.strip()
    if s.startswith("print(") and s.endswith(")"):
        return s[len("print("):-1].strip()
    return s

def construir_html(titulo, testcode, stdin, ficheros_iniciales, stdout, ficheros_finales):
    parts = []
    parts.append(f"<h3>{html.escape(titulo)}</h3>")

    parts.append("<h4>Contexto del test</h4>")

    if testcode.strip():
        parts.append(block("Test a ejecutar", mostrar_test_sin_print(testcode)))

    if stdin.strip():
        parts.append(block("Entrada por teclado", stdin))

    for fn, cont in ficheros_iniciales.items():
        parts.append(block(f"Fichero inicial: {fn}", cont))

    parts.append("<h4>Resultado de la ejecución</h4>")

    if stdout.strip():
        parts.append(block("Salida por pantalla", stdout))

    for fn, cont in ficheros_finales.items():
        parts.append(block(f"Fichero final: {fn}", cont))

    return "\n".join(parts).rstrip()

# =========================================================
# Semilla estable
# =========================================================

def stable_seed(test_fingerprint, student_code):
    data = (test_fingerprint + student_code).encode("utf8")
    h = hashlib.sha256(data).hexdigest()
    return int(h, 16) & 0xffffffff

# =========================================================
# Barajado de ficheros
# =========================================================

def barajar_fichero(entrada, salida=None, seed=None):
    if seed is not None:
        random.seed(seed)

    with open(entrada, "r", encoding="utf8", errors="replace") as f:
        filas = [ln.rstrip().rstrip("\n") for ln in f]

    while filas and filas[-1] == "":
        filas.pop()

    datos = [fila.split(",") for fila in filas if fila != ""]
    if not datos:
        if salida is None:
            salida = entrada + "_barajado"
        open(salida, "w").close()
        return salida

    maxc = max(len(r) for r in datos)
    for r in datos:
        r.extend([""] * (maxc - len(r)))

    columnas = list(zip(*datos))
    columnas_barajadas = []
    for col in columnas:
        col = list(col)
        random.shuffle(col)
        columnas_barajadas.append(col)

    filas_out = list(zip(*columnas_barajadas))

    if salida is None:
        salida = entrada

    with open(salida, "w", encoding="utf8") as g:
        for r in filas_out:
            g.write(",".join(r) + "\n")

    return salida

def barajar_entradas_con_seed(attach_list, seed):
    for fn in attach_list:
        if not os.path.exists(fn):
            continue
        tmp = f".__tmp_barajado__{os.path.basename(fn)}"
        barajar_fichero(fn, salida=tmp, seed=seed)
        os.replace(tmp, fn)

# =========================================================
# Inyección para patrón y alumno
# =========================================================

BARAJAR_SRC = """
import random
def barajar_fichero(entrada, salida=None, seed=None):
    if seed is not None:
        random.seed(seed)
    with open(entrada, "r", encoding="utf8", errors="replace") as f:
        filas = [ln.rstrip().rstrip("\\n") for ln in f]
    while filas and filas[-1] == "":
        filas.pop()
    datos = [fila.split(",") for fila in filas if fila != ""]
    if not datos:
        if salida is None:
            salida = entrada + "_barajado"
        open(salida, "w").close()
        return salida
    maxc = max(len(r) for r in datos)
    for r in datos:
        r.extend([""] * (maxc - len(r)))
    columnas = list(zip(*datos))
    columnas_barajadas = []
    for col in columnas:
        col = list(col)
        random.shuffle(col)
        columnas_barajadas.append(col)
    filas_out = list(zip(*columnas_barajadas))
    if salida is None:
        salida = entrada
    with open(salida, "w", encoding="utf8") as g:
        for r in filas_out:
            g.write(",".join(r) + "\\n")
    return salida
"""

# =========================================================
# TEST PRINCIPAL
# =========================================================

def do_testing():
    stdin = """{{ TEST.stdin | e('py') }}"""
    testcode = """{{ TEST.testcode | e('py') }}"""
    extra = """{{ TEST.extra | e('py') }}"""

    attachments = """{{ ATTACHMENTS | e('py') }}""".strip()
    attach_list = [a.strip() for a in attachments.split(",") if a.strip()]

    outfiles = [x.strip() for x in extra.splitlines() if x.strip()]

    student_code = """{{ STUDENT_ANSWER | e('py') }}"""

    test_fingerprint = stdin + testcode + extra
    seed = stable_seed(test_fingerprint, student_code)

    # Barajar entradas UNA VEZ
    barajar_entradas_con_seed(attach_list, seed)

    # Leer entradas reales
    inputs_dict = {fn: read_text_file(fn) for fn in attach_list}

    # ---------------- PATRÓN ----------------
    expected_stdout = ""
    expected_files_bytes = {}
    expected_files_text = {}

    answer = """{{ QUESTION.answer | e('py') }}"""
    for fn in outfiles:
        delete_if_exists(fn)

    exp_out, exp_err = run_py(BARAJAR_SRC + answer, stdin)
    if exp_err:
        print(json.dumps({"expected": "", "got": block("Error en patrón", exp_err), "fraction": 0}))
        return

    expected_stdout = exp_out
    for fn in outfiles:
        expected_files_bytes[fn] = read_file_bytes(fn)
        expected_files_text[fn] = read_text_file(fn)

    expected_html = construir_html(
        "PATRÓN",
        testcode,
        stdin,
        inputs_dict,
        expected_stdout,
        expected_files_text
    )

    for fn in outfiles:
        delete_if_exists(fn)

    # ---------------- ALUMNO ----------------
    got_out, got_err = run_py(BARAJAR_SRC + student_code + "\n" + testcode, stdin)
    got_stdout = got_out + (("\n" + got_err) if got_err else "")

    got_files_text = {fn: read_text_file(fn) for fn in outfiles}

    got_html = construir_html(
        "ALUMNO",
        testcode,
        stdin,
        inputs_dict,
        got_stdout,
        got_files_text
    )

    # ---------------- COMPARACIÓN ----------------
    ok_stdout = normalize_stdout(got_stdout) == normalize_stdout(expected_stdout)

    ok_files = True
    for fn in outfiles:
        if read_file_bytes(fn) != expected_files_bytes.get(fn):
            ok_files = False
            break

    fraction = 1 if (ok_stdout and ok_files) else 0

    print(json.dumps({
        "expected": expected_html,
        "got": got_html,
        "fraction": fraction
    }))

do_testing()
