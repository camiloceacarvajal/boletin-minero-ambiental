"""Índice de normas citadas, extraído del texto íntegro de la sentencia.

Esta es la ventaja estructural sobre un boletín redactado a mano: quien resume
teclea las normas que recuerda; quien tiene el PDF las extrae todas. Permite
preguntar "qué fallos aplican el art. 17 N°3 de la Ley 20.600" y responder.
"""
import re
from collections import Counter

# Leyes chilenas por número, con o sin 'N°'
LEY = re.compile(r"\bLey\s*(?:N\s*[°º]?\s*)?(\d{1,3}\.?\d{3})\b", re.I)
DL = re.compile(r"\b(?:D\.?L\.?|Decreto\s+Ley)\s*(?:N\s*[°º]?\s*)?(\d{1,4})\b", re.I)
DS = re.compile(r"\b(?:D\.?S\.?|Decreto\s+Supremo)\s*(?:N\s*[°º]?\s*)?(\d{1,4})\s*(?:/\s*(\d{4}))?", re.I)
ART = re.compile(r"\bart[íi]culos?\s+(\d{1,4})\s*(?:(bis|ter|qu[áa]ter))?"
                 r"(?:\s*N\s*[°º]?\s*(\d{1,2}))?", re.I)

# Cuerpos legales por nombre corto -> etiqueta canónica
CUERPOS = {
    r"c[óo]digo civil": "Código Civil",
    r"c[óo]digo de procedimiento civil|\bcpc\b": "CPC",
    r"c[óo]digo procesal penal|\bcpp\b": "CPP",
    r"c[óo]digo penal": "Código Penal",
    r"c[óo]digo del trabajo": "Código del Trabajo",
    r"c[óo]digo de aguas": "Código de Aguas",
    r"c[óo]digo de miner[íi]a": "Código de Minería",
    r"c[óo]digo tributario": "Código Tributario",
    r"constituci[óo]n pol[íi]tica": "Constitución",
}

# Las leyes que de verdad importan en lo ambiental-minero
CONOCIDAS = {
    "19.300": "Ley 19.300 · Bases del Medio Ambiente",
    "20.600": "Ley 20.600 · Tribunales Ambientales",
    "20.417": "Ley 20.417 · LOSMA",
    "19.880": "Ley 19.880 · Bases de Procedimiento Administrativo",
    "18.575": "Ley 18.575 · Bases de la Administración",
    "20.920": "Ley 20.920 · Ley REP",
    "19.253": "Ley 19.253 · Ley Indígena",
    "21.600": "Ley 21.600 · SBAP",
    "18.248": "Ley 18.248 · Código de Minería",
    "18.097": "Ley 18.097 · Concesiones Mineras",
    "21.210": "Ley 21.210 · Modernización Tributaria",
    "19.496": "Ley 19.496 · Protección al Consumidor",
}


def _norm(n):
    """'20600' y '20.600' son la misma ley."""
    n = n.replace(".", "")
    return f"{n[:-3]}.{n[-3:]}" if len(n) > 3 else n


def extraer(texto, minimo=2):
    """Normas citadas al menos `minimo` veces, de la más citada a la menos."""
    if not texto:
        return []
    cuenta = Counter()

    for m in LEY.finditer(texto):
        n = _norm(m.group(1))
        cuenta[CONOCIDAS.get(n, f"Ley {n}")] += 1
    for m in DL.finditer(texto):
        cuenta[f"D.L. {m.group(1)}"] += 1
    for m in DS.finditer(texto):
        anio = f"/{m.group(2)}" if m.group(2) else ""
        cuenta[f"D.S. {m.group(1)}{anio}"] += 1
    for patron, etiqueta in CUERPOS.items():
        n = len(re.findall(patron, texto, re.I))
        if n:
            cuenta[etiqueta] += n

    return [n for n, c in cuenta.most_common(12) if c >= minimo]


def articulos(texto, tope=8):
    """Los artículos más invocados, como 'art. 17 N° 3'."""
    if not texto:
        return []
    cuenta = Counter()
    for m in ART.finditer(texto):
        num, suf, ordinal = m.group(1), m.group(2), m.group(3)
        et = f"art. {num}"
        if suf: et += f" {suf.lower()}"
        if ordinal: et += f" N° {ordinal}"
        cuenta[et] += 1
    return [a for a, c in cuenta.most_common(tope) if c >= 3]


# --- rastro de la Corte Suprema -------------------------------------------
# Algunos PDF del 2TA traen anexado el fallo de casación de la CS sobre la
# propia sentencia. Es la única vía legítima que tenemos a texto de la Corte:
# juris.pjud.cl está cerrado por robots.txt y reCAPTCHA.
_CS_ANEXADO = re.compile(
    r"Pronunciad[oa] por la (Primera|Segunda|Tercera|Cuarta) Sala de la Corte Suprema", re.I)
_CS_CITADA = re.compile(
    r"Corte Suprema[^.]{0,80}?\bRol\b[^.]{0,40}?(\d{1,6})[\s\-]+(\d{4})", re.I)


def corte_suprema(texto):
    """'anexada' si el fallo de la CS viene en el PDF; 'citada' si solo se
    invoca su jurisprudencia; None si no aparece."""
    if not texto:
        return None
    m = _CS_ANEXADO.search(texto)
    if m:
        return f"anexada · {m.group(1)} Sala"
    if _CS_CITADA.search(texto):
        return "citada"
    return None
