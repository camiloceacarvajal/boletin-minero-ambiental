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
