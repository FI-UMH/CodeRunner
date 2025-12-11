def preparar_contexto(contexto):
    """
    Genera los datos concretos de entrada_estandar, ficheros_entrada y argumentos
    a partir de las 'spec' y del estado de random (ya sembrado en la plantilla).

    Ahora soporta:
      - spec_entrada_estandar = dict  -> un solo bloque
      - spec_entrada_estandar = list  -> varios bloques concatenados
    """
    contexto = dict(contexto)

    # ── ENTRADA ESTÁNDAR ───────────────────────────────────────
    spec_in = contexto.get("spec_entrada_estandar")

    if spec_in is None:
        # Sin spec: comportamiento antiguo
        contexto["entrada_estandar"] = f"{r.randint(1, 100)}\n"

    elif isinstance(spec_in, list):
        # Lista de specs -> concatenar lo que devuelva cada generador
        partes = []
        for spec in spec_in:
            partes.append(_generar_desde_spec(spec))
        contexto["entrada_estandar"] = "".join(partes)

    else:
        # Un solo diccionario como antes
        contexto["entrada_estandar"] = _generar_desde_spec(spec_in)

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

    # ── ARGUMENTOS PARA FUNCIONES (más adelante) ───────────────
    contexto["argumentos"] = None

    return contexto
