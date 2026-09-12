"""Titular de primera pasada sin modelo, gratis y determinista.

Las sentencias de los tribunales ambientales abren con una TABLA DE CONTENIDOS
donde el propio tribunal enumera las controversias que va a resolver. Eso es
materia prima de titular escrita por el tribunal: no hay que inferir nada.

No reemplaza el resumen redactado —la tabla dice de qué se discute, no cómo se
resolvió— pero deja el 80% del camino hecho sin gastar un peso.
"""
import re

RUIDO = re.compile(
    r'^(vistos|considerando|conclusi[óo]n(es)?|antecedentes de la reclamaci[óo]n|'
    r'antecedentes de la demanda|antecedentes de la solicitud|'
    r'del proceso de reclamaci[óo]n judicial|del proceso judicial|'
    r'apartado final.*|otras alegaciones|de las dem[áa]s alegaciones|'
    r'de las otras alegaciones|se resuelve|tabla de contenidos|'
    r'parte (expositiva|considerativa|resolutiva))[:.]?$', re.I)

# 'I.', '1.', 'IV)', '2 -' al principio de la entrada
NUMERAL = re.compile(r'^(?:[IVXLC]{1,5}|\d{1,2})\s*[.\-–)]\s*')


def extraer(texto, max_items=6):
    """Devuelve las controversias declaradas, de la más general a la más concreta."""
    ini = texto.find("TABLA DE CONTENIDOS")
    if ini < 0:
        return []
    fin = texto.find("SE RESUELVE", ini)
    bloque = texto[ini + len("TABLA DE CONTENIDOS"): fin if fin > 0 else ini + 5000]

    plano = re.sub(r"\s+", " ", bloque)
    plano = re.sub(r"[.…]{2,}", " ⋯ ", plano)      # puntos guía -> separador
    plano = re.sub(r"\s*⋯\s*\d+\s*", " ⋯ ", plano)  # y el número de página fuera

    salida, vistos = [], set()
    for trozo in plano.split("⋯"):
        t = NUMERAL.sub("", trozo.strip())
        t = re.sub(r"\s+\d+\s*$", "", t).strip()    # número pegado al final
        # A veces dos entradas quedan pegadas sin puntos guía: 'texto 20 3. Acerca...'
        t = re.split(r"\s+\d{1,3}\s+\d{1,2}\s*[.\-–)]\s+", t)[0].strip()
        t = re.sub(r"^Controversia\s*(N[°º]?)?\s*[IVX\d]*\s*:\s*", "", t, flags=re.I)
        if not (18 < len(t) < 160) or RUIDO.match(t):
            continue
        clave = t.lower()[:40]
        if clave in vistos:
            continue
        vistos.add(clave)
        salida.append(t)
    return salida[:max_items]


def titular_tentativo(texto, resuelve=None):
    """La controversia más específica, que suele ser la que decide el caso."""
    cs = extraer(texto)
    if not cs:
        return None
    # Se prefiere la más larga: las genéricas ('Alegaciones formales') son cortas.
    mejor = max(cs, key=len)
    mejor = re.sub(r"^(eventual(es)?|supuesta?|acerca de|de la|del|sobre)\s+", "",
                   mejor, flags=re.I)
    mejor = mejor[0].upper() + mejor[1:]
    if resuelve:
        mejor = f"{mejor} — {resuelve}"
    return mejor


# --- cómo resolvió, leído del propio fallo ---------------------------------
# El 3TA no publica el resultado en su tabla, a diferencia del 2TA. Se deduce
# de la parte resolutiva, que siempre abre con un verbo en infinitivo.
# El encabezado de la decisión es 'SE RESUELVE' / 'RESUELVE:'. 'POR TANTO' solo
# abre la cita de normas —a veces larguísima— y en el 3TA reaparece DESPUÉS de
# lo resuelto, así que sirve nada más como último recurso.
_ANCLA = re.compile(r"\bSE\s+RESUELVE\b|(?<![A-Za-zÁÉÍÓÚÑ])RESUELVE\s*:|"
                    r"\bSE\s+DECLARA\b|\bSE\s+AUTORIZA\b", re.I)
_ANCLA_DEBIL = re.compile(r"\bPOR\s+TANTO\b", re.I)

# Lo resolutivo suele abrir despachando lo procesal ("Rechazar la excepción de
# incompetencia...") y recién después decidir el fondo ("Acoger la demanda..."),
# así que quedarse con el primer verbo se equivoca. Se busca el verbo aplicado
# al OBJETO PRINCIPAL y solo si no aparece se cae al primero que haya.
_PRINCIPAL = r"(?:la\s+)?(?:demanda|reclamaci[óo]n|reclamo|solicitud|consulta)"
_ACCESORIO = r"(?:la\s+|el\s+)?(?:excepci[óo]n|incidente|objeci[óo]n|alegaci[óo]n|tacha)"

_FONDO = [
    ("acoge parcialmente", rf"acoger\s+(?:parcialmente|en\s+parte)\s+{_PRINCIPAL}|"
                           rf"acoger\s+{_PRINCIPAL}[^.]{{0,40}}?\s+(?:s[óo]lo|parcialmente)"),
    ("acoge",              rf"acoger\s+(?:en\s+todas\s+sus\s+partes\s+)?{_PRINCIPAL}"),
    ("rechaza",            rf"rechazar\s+(?:en\s+todas\s+sus\s+partes\s+)?{_PRINCIPAL}"),
    ("inadmisible",        rf"declarar\s+(?:la\s+)?inadmisi\w+\s+(?:de\s+)?{_PRINCIPAL}"),
    ("autoriza",           r"autorizar\s+(?:la\s+)?medida|se\s+autoriza\s+la\s+medida"),
    ("aprueba",            r"aprobar\s+(?:la\s+)?(?:sanci[óo]n|avenimiento|conciliaci[óo]n)|"
                           r"se\s+aprueba\s+(?:el\s+|la\s+)?(?:avenimiento|sanci[óo]n)"),
    ("anula",              rf"anular\s+{_PRINCIPAL}|dejar\s+sin\s+efecto\s+la\s+resoluci"),
]
_RESPALDO = [
    ("autoriza",    r"\bautorizar\b|se\s+autoriza\b"),
    ("aprueba",     r"\baprobar\b|se\s+aprueba\b"),
    ("acoge",       r"\bacoger\b"),
    ("rechaza",     r"\brechazar\b"),
    ("inadmisible", r"\binadmisibl\w+"),
]
_FONDO = [(n, re.compile(p, re.I)) for n, p in _FONDO]
_RESPALDO = [(n, re.compile(p, re.I)) for n, p in _RESPALDO]


def resultado(texto, ventana=2500):
    """Deduce el resultado leyendo la última parte resolutiva del fallo.

    Se toma la ÚLTIMA aparición de 'SE RESUELVE' porque el índice del documento
    la repite al principio, con el número de página al lado.
    """
    if not texto:
        return None
    ult = None
    for m in _ANCLA.finditer(texto):
        ult = m
    if not ult:
        for m in _ANCLA_DEBIL.finditer(texto):
            ult = m
    if not ult:
        return None
    bloque = texto[ult.start(): ult.start() + ventana]
    # El voto disidente dice lo contrario de lo resuelto ("estuvo por acoger"):
    # todo lo que venga después de ese marcador sobra.
    disidencia = re.search(r"acordada\s+con\s+el\s+voto|voto\s+(?:en\s+contra|disidente)|"
                           r"se\s+previene|prevenci[óo]n\s+del\s+[Mm]inistro", bloque, re.I)
    if disidencia:
        bloque = bloque[:disidencia.start()]
    # Fuera lo accesorio, que es lo que confunde: 'Rechazar la excepción de...'
    limpio = re.sub(rf"(?:rechazar|acoger)\s+{_ACCESORIO}[^.;]{{0,120}}[.;]", " ",
                    bloque, flags=re.I)

    for nombre, pat in _FONDO:
        if pat.search(limpio):
            return nombre
    for nombre, pat in _RESPALDO:
        if pat.search(limpio):
            return nombre
    return None
