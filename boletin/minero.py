"""Clasificador minero, determinista y sin coste.

Dos listas: términos que por sí solos bastan (titulares mineros, faenas,
minerales) y términos ambiguos que solo cuentan si van acompañados. Así 'oro'
en 'Santuario El Oro' no arrastra el caso al boletín.
"""
import re

FUERTE = re.compile(r"""
 \bminer[ao]s?\b|\bminer[íi]a\b|faena\ minera|concesi[óo]n\ minera|
 relave|tranque\ de\ relave|dep[óo]sito\ de\ relaves|botadero|
 pila\ de\ lixiviaci|planta\ de\ beneficio|sondaje|prospecci[óo]n\ minera|
 rajo\ (abierto|open)|pirquin|sernageomin|
 codelco|escondida|collahuasi|candelaria|pelambres|caserones|zald[íi]var|
 anglo\ american|antofagasta\ minerals|barrick|kinross|teck|albemarle|
 \bsqm\b|lundin|spence|centinela|quebrada\ blanca|el\ abra|ministro\ hales|
 chuquicamata|radomiro\ tomic|gabriela\ mistral|lomas\ bayas|sierra\ gorda|
 pascua\ lama|el\ teniente|los\ bronces|andina|salvador|mantos\ blancos|
 compa[ñn][íi]a\ minera|sociedad\ contractual\ minera|\bscm\b|
 cat[óo]dos\ de\ cobre|concentrado\ de\ cobre|salmuera
""", re.I | re.X)

DEBIL = re.compile(r"\b(cobre|oro|plata|litio|hierro|molibdeno|salar|"
                   r"[áa]ridos?|canteras?|explotaci[óo]n)\b", re.I)
CONTEXTO = re.compile(r"\b(extracci[óo]n|yacimiento|mineral|explotaci[óo]n|"
                      r"faena|planta|proyecto|proces|proceso|proces[óa])\w*", re.I)


def es_minero(texto):
    t = texto or ""
    if FUERTE.search(t):
        return True
    return bool(DEBIL.search(t) and CONTEXTO.search(t))


def puntaje(texto):
    """Cuántas señales fuertes distintas: sirve para ordenar por 'cuán minero'."""
    return len({m.group(0).lower() for m in FUERTE.finditer(texto or "")})
