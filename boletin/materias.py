"""Sub-materia dentro de lo ambiental. 'Ambiental' a secas no informa: lo que
un abogado busca es sancionatorio, evaluación, daño o consulta indígena.
"""
import re

REGLAS = [
    ("Consulta indígena", r"consulta ind[íi]gena|convenio 169|comunidad(es)? (ind[íi]gena|colla|diaguita|atacame|aymara|mapuche)"),
    ("Daño ambiental",    r"da[ñn]o ambiental|reparaci[óo]n del medio|acci[óo]n de reparaci"),
    ("Sancionatorio SMA", r"programa de cumplimiento|\bPdC\b|procedimiento sancionatorio|"
                          r"multa de \d|UTA\b|formulaci[óo]n de cargos|art[íi]culo 40 de la LOSMA"),
    ("Elusión al SEIA",   r"elusi[óo]n|ingreso al (SEIA|Sistema de Evaluaci)|consulta de pertinencia"),
    ("Evaluación (SEIA)", r"resoluci[óo]n de calificaci[óo]n ambiental|\bRCA\b|estudio de impacto|"
                          r"declaraci[óo]n de impacto|comit[ée] de ministros|l[íi]nea de base"),
    ("Invalidación",      r"invalidaci[óo]n|art[íi]culo 53 de la Ley 19.880"),
    ("Norma de emisión",  r"norma de emisi[óo]n|ruido|\bPM10\b|\bPM2[,.]5\b|calidad del aire"),
    ("Residuos y REP",    r"\bREP\b|responsabilidad extendida|valorizaci[óo]n|residuos"),
    ("Agua",              r"c[óo]digo de aguas|derechos de aprovechamiento|caudal ecol[óo]gico|acu[íi]fero"),
    ("Áreas protegidas",  r"santuario de la naturaleza|parque nacional|reserva nacional|"
                          r"sitio prioritario|humedal|\bSBAP\b|monumento natural"),
]
COMPILADAS = [(n, re.compile(p, re.I)) for n, p in REGLAS]


def clasificar(texto, tope=3):
    """Devuelve las sub-materias presentes, en orden de peso en el texto."""
    t = texto or ""
    puntajes = [(n, len(r.findall(t))) for n, r in COMPILADAS]
    puntajes = [(n, c) for n, c in puntajes if c]
    puntajes.sort(key=lambda x: -x[1])
    return [n for n, _ in puntajes[:tope]] or ["Ambiental"]
