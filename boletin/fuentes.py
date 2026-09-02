"""Fuentes de sentencias.

Cada fuente es una función que devuelve dicts normalizados. Añadir un tribunal
es escribir una función más y registrarla en FUENTES; nada más cambia.

Sólo se raspa lo que robots.txt permite. juris.pjud.cl NO está aquí a propósito:
su robots.txt es `Disallow: /` para todo agente y la búsqueda va tras reCAPTCHA.
"""
import re
import time
import unicodedata
from datetime import date

import requests
from bs4 import BeautifulSoup

CABECERAS = {"User-Agent": "boletin-jurisprudencia/0.1 (+contacto: ccea@mbienes.cl)"}
PAUSA = 1.0  # segundos entre peticiones: cortesía con el servidor


def _get(url, **kw):
    time.sleep(PAUSA)
    r = requests.get(url, headers=CABECERAS, timeout=45, **kw)
    r.raise_for_status()
    return r


def _limpiar(s):
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", " ", s).strip()


def _fecha_iso(txt):
    """'25-8-2026' | '25-08-2026' -> '2026-08-25'."""
    m = re.search(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", txt or "")
    if not m:
        return None
    d, mes, a = (int(x) for x in m.groups())
    try:
        return date(a, mes, d).isoformat()
    except ValueError:
        return None


# --- Segundo Tribunal Ambiental -------------------------------------------
URL_2TA = "https://tribunalambiental.cl/sentencias-e-informes/sentencias/"

# Las 4 tablas TablePress de la página, en orden de aparición.
MATERIAS_2TA = {
    "tablepress-28": "Reclamaciones",
    "tablepress-29": "Daño ambiental",
    "tablepress-30": "Consultas SMA",
    "tablepress-31": "Solicitudes SMA",
}


def segundo_tribunal_ambiental():
    """Listado público de sentencias del 2TA (Santiago). robots.txt: permitido."""
    soup = BeautifulSoup(_get(URL_2TA).text, "lxml")

    for tabla in soup.select("table.tablepress"):
        materia = MATERIAS_2TA.get(tabla.get("id"), "Otras")

        for fila in tabla.select("tbody tr"):
            celdas = fila.find_all("td")
            if len(celdas) < 2:
                continue

            rol = _limpiar(celdas[0].get_text())
            if not re.match(r"^[A-Z]-\d+-\d{4}", rol):
                continue

            desc_celda = celdas[1]
            texto = _limpiar(desc_celda.get_text(" "))

            # Ojo: la mayoría de los enlaces a PDF dicen solo "ver", no "ver
            # sentencia". Filtrar por el texto perdía 297 de 494. Se toma
            # cualquier .pdf, prefiriendo el que se anuncia como sentencia.
            pdfs, otros = [], []
            for a in desc_celda.find_all("a", href=True):
                etiqueta = _limpiar(a.get_text()).lower()
                (pdfs if a["href"].lower().endswith(".pdf") else otros).append(
                    (etiqueta, a["href"]))

            pdf = next((u for k, u in pdfs if "sentencia" in k), None) \
                or (pdfs[0][1] if pdfs else None)
            expediente = next((u for k, u in otros
                               if "expediente" in k or k == "ver"), None) \
                or (otros[0][1] if otros else None)

            yield {
                "fuente": "2ta",
                "rol": rol,
                "materia": materia,
                "caratulado": texto.split(". Relacionado con")[0][:300],
                "descripcion": texto,
                "region": _campo(texto, "Región"),
                "fecha_fallo": _fecha_iso(_campo(texto, "Fecha del fallo")),
                "resuelve": (_campo(texto, "Resuelve") or "").rstrip(".").lower() or None,
                "url_pdf": pdf,
                "url_expediente": expediente,
            }


def _campo(texto, etiqueta):
    """Extrae 'Región: Metropolitana.' -> 'Metropolitana'."""
    m = re.search(rf"{etiqueta}\s*:\s*([^.]*(?:\.[^ ]|[^.])*?)\s*(?:\.|$)", texto)
    return _limpiar(m.group(1)) if m else None


FUENTES = {
    "2ta": segundo_tribunal_ambiental,
}


def descargar_pdf(url, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and destino.stat().st_size > 0:
        return destino
    destino.write_bytes(_get(url).content)
    return destino


# --- Primer Tribunal Ambiental (Antofagasta: el norte minero) --------------
# No publica una tabla de sentencias, pero cada fallo sale como entrada de
# noticia con titular y resumen YA REDACTADOS por el tribunal. Para un boletín
# eso es materia prima terminada, gratis y sin modelo.
API_1TA = "https://1ta.cl/wp-json/wp/v2/posts"

# El cuerpo de una noticia de sentencia siempre abre declarándolo.
ES_SENTENCIA = re.compile(
    r"en sentencia dictada|dict[óo] (una )?sentencia|sentencia del (primer )?tribunal|"
    r"(rechaz|acogi|ratific|confirm|desestim|anul|invalid)[óo]\b|"
    r"se (rechaza|acoge|ratifica|confirma|desestima|anula)\b|"
    r"(rechaza|acoge|ratifica|confirma|desestima) (la|el|reclamo|reclamaci)", re.I)

# Trámite, audiencia o aviso: hay noticia pero todavía no hay fallo.
NO_ES_FALLO = re.compile(
    r"a tr[áa]mite\b|a tramitaci[óo]n\b|admit\w*|acog\w* a tr|"
    r"en audiencia|audiencia de (vista|conciliaci)|reclama\w* (ante|en contra)|"
    r"presenta(n|ron|ba)?|present[óo]|interpone(n)?|interpusieron|interpuso|"
    r"reclaman contra|recurren ante|se realizar[áa]|convoca|alegatos|"
    r"queda en acuerdo|en estudio|inicia (el )?estudio", re.I)

ROL_1TA = re.compile(r"\b([RDSC])[\s\-]*N?[°º]?\s*(\d{1,4})[\s\-]+(\d{4})\b")

REGIONES = ("Arica y Parinacota", "Tarapacá", "Antofagasta", "Atacama", "Coquimbo")


def _sin_html(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s or "")
    # El 1TA usa WPBakery: el texto real va DESPUÉS de los shortcodes [vc_row ...].
    s = re.sub(r"\[/?vc_[^\]]*\]|\[/?[a-z_]+[^\]]{0,200}\]", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    import html as _h
    return _limpiar(_h.unescape(s))


def primer_tribunal_ambiental(paginas=8, por_pagina=100):
    """Entradas del 1TA que anuncian una sentencia. robots.txt: permitido."""
    for pag in range(1, paginas + 1):
        r = _get(API_1TA, params={
            "per_page": por_pagina, "page": pag, "orderby": "date", "order": "desc",
            "_fields": "id,date,link,title,content,excerpt"})
        lote = r.json()
        if not lote:
            return

        for p in lote:
            titulo = _sin_html(p["title"]["rendered"])
            cuerpo = _sin_html(p["content"]["rendered"])
            # El tipo de noticia lo declara el titular; el cuerpo confirma el fallo.
            if NO_ES_FALLO.search(titulo):
                continue
            if not ES_SENTENCIA.search(titulo + " " + cuerpo[:900]):
                continue

            m = ROL_1TA.search(cuerpo) or ROL_1TA.search(titulo)
            rol = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else f"1TA-{p['id']}"
            region = next((g for g in REGIONES if g.lower() in cuerpo.lower()), None)

            yield {
                "fuente": "1ta",
                "rol": rol,
                "materia": "Reclamaciones",
                "caratulado": titulo,
                "descripcion": cuerpo[:1200],
                "region": region,
                "fecha_fallo": p["date"][:10],
                "resuelve": _resultado(titulo + " " + cuerpo[:400]),
                # El titular ya viene escrito por el tribunal.
                "titular": titulo,
                "resumen": cuerpo[:700],
                "url_pdf": None,
                "url_expediente": p["link"],
            }


def _resultado(t):
    t = t.lower()
    if re.search(r"\bacogi[óo]\b|se acoge|acoge la reclamaci", t):   return "acoge"
    if re.search(r"rechaz[óo]|se rechaza|desestim", t):              return "rechaza"
    if re.search(r"ratific|confirm|mantuvo|se confirma", t):         return "confirma"
    if re.search(r"anul[óo]|dej[óo] sin efecto|invalid", t):         return "anula"
    return None


FUENTES["1ta"] = primer_tribunal_ambiental
