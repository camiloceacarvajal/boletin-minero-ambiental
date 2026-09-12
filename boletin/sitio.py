"""Genera el sitio estático. Sin servidor: HTML plano que se sube a cualquier sitio."""
import itertools
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

MESES = ("enero febrero marzo abril mayo junio julio agosto "
         "septiembre octubre noviembre diciembre").split()


def _en_palabras(iso):
    if not iso:
        return "Sin fecha"
    a, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {MESES[m - 1]} de {a}"


def generar(filas, destino="publico/index.html", plantillas="plantillas",
            titulo="Boletín Ambiental", subtitulo="Sentencias del Segundo Tribunal Ambiental",
            fuente="tribunalambiental.cl"):
    env = Environment(loader=FileSystemLoader(plantillas),
                      autoescape=select_autoescape(["html"]))
    filas = sorted(filas, key=lambda r: (r["fecha_fallo"] or ""), reverse=True)
    por_fecha = [(_en_palabras(k), list(g))
                 for k, g in itertools.groupby(filas, key=lambda r: r["fecha_fallo"])]

    html = env.get_template("portada.html").render(
        titulo=titulo, subtitulo=subtitulo, fuente=fuente,
        por_fecha=por_fecha, total=len(filas),
        generado=_en_palabras(date.today().isoformat()),
    )
    salida = Path(destino)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    return salida


def reporte(filas, destino, plantillas="plantillas", desde=None, hasta=None,
            titulo="Reporte semanal", fuente="Segundo Tribunal Ambiental"):
    """Reporte para suscriptores: solo lo resumido, con índice y listo para PDF."""
    env = Environment(loader=FileSystemLoader(plantillas),
                      autoescape=select_autoescape(["html"]))
    # Primero las destacadas, y dentro de cada bloque de la más reciente a la más antigua.
    filas = sorted((dict(f) for f in filas),
                   key=lambda r: (r.get("destacada") or 0, r["fecha_fallo"] or ""),
                   reverse=True)
    for f in filas:
        f["fecha_larga"] = _en_palabras(f["fecha_fallo"])

    html = env.get_template("reporte.html").render(
        titulo=titulo, fuente=fuente, sentencias=filas, total=len(filas),
        desde=_en_palabras(desde), hasta=_en_palabras(hasta))
    salida = Path(destino)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    return salida


TRIBUNAL = {"1ta": "1.º T.A. · Norte", "2ta": "2.º T.A. · Centro", "3ta": "3.º T.A. · Sur"}


def _clase(resuelve):
    r = (resuelve or "").lower()
    if r.startswith("acoge") or "acoge" in r[:12]: return "acoge"
    if r.startswith("rechaza") or "rechaz" in r[:12]: return "rechaza"
    return "otro"


def minero(filas, destino, plantillas="plantillas", titulo="La Veta — jurisprudencia minero-ambiental"):
    """Boletín minero: una página, filtros y buscador en el navegador."""
    env = Environment(loader=FileSystemLoader(plantillas),
                      autoescape=select_autoescape(["html"]))
    ss = []
    for f in filas:
        d = dict(f)
        # Si el tribunal no publica el resultado, se usa el deducido del PDF,
        # marcado como tal para no hacerlo pasar por dato oficial.
        d["inferido"] = not d.get("resuelve") and bool(d.get("resuelve_inf"))
        if d["inferido"]:
            d["resuelve"] = d["resuelve_inf"]
        d["clase"] = _clase(d.get("resuelve"))
        d["tribunal"] = TRIBUNAL.get(d["fuente"], d["fuente"])
        d["fecha_larga"] = _en_palabras(d.get("fecha_fallo"))
        d["titular"] = d.get("titular") or d.get("caratulado") or d["rol"]
        d["cs"] = d.get("corte_sup")
        d["subs"] = [x for x in (d.get("submaterias") or "").split("|") if x]
        d["normas_l"] = [x for x in (d.get("normas") or "").split("|") if x]
        d["arts"] = [x for x in (d.get("articulos") or "").split("|") if x]
        # Índice de búsqueda: todo en minúsculas, en un solo atributo.
        d["buscable"] = " ".join(str(x or "") for x in (
            d["rol"], d["titular"], d.get("resumen"), d.get("descripcion"),
            d.get("region"), d.get("resuelve"), d["tribunal"],
            d.get("submaterias"), d.get("normas"), d.get("articulos"),
            "corte suprema" if d.get("corte_sup") else "",
            d.get("redactor"), d.get("competencia"))).lower()
        ss.append(d)

    ss.sort(key=lambda r: (r.get("fecha_fallo") or ""), reverse=True)
    cuenta = lambda p: sum(1 for s in ss if p(s))
    from collections import Counter
    subs = Counter(x for s in ss for x in s["subs"] if x != "Ambiental")
    normas_top = Counter(x for s in ss for x in s["normas_l"])

    html = env.get_template("minero.html").render(
        titulo=titulo, sentencias=ss, total=len(ss),
        n_1ta=cuenta(lambda s: s["fuente"] == "1ta"),
        n_2ta=cuenta(lambda s: s["fuente"] == "2ta"),
        n_acoge=cuenta(lambda s: s["clase"] == "acoge"),
        n_rechaza=cuenta(lambda s: s["clase"] == "rechaza"),
        n_texto=cuenta(lambda s: s.get("texto")),
        n_cs=cuenta(lambda s: s.get("cs")),
        n_3ta=cuenta(lambda s: s["fuente"] == "3ta"),
        submaterias=[m for m, _ in subs.most_common(9)],
        normas_top=[n for n, _ in normas_top.most_common(8)],
        bajada="Fallos de los tribunales ambientales chilenos sobre faenas, "
               "concesiones y proyectos mineros. Seleccionados, clasificados y "
               "enlazados a su texto íntegro.",
        generado=_en_palabras(date.today().isoformat()))
    salida = Path(destino)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    return salida


def portada_sitio(filas, destino, plantillas="plantillas", reporte="reporte.html"):
    """Portada de GitHub Pages: enlaza el boletín y el reporte."""
    env = Environment(loader=FileSystemLoader(plantillas),
                      autoescape=select_autoescape(["html"]))
    ss = [dict(f) for f in filas]
    html = env.get_template("portada-sitio.html").render(
        titulo="La Veta — jurisprudencia minero-ambiental chilena",
        bajada=("Las sentencias de los tres tribunales ambientales de Chile sobre "
                "faenas, concesiones y proyectos mineros: clasificadas, resumidas "
                "y enlazadas a su texto íntegro."),
        n_mineras=len(ss),
        n_doctrina=sum(1 for s in ss if s.get("titular")),
        n_cs=sum(1 for s in ss if s.get("corte_sup")),
        reporte=reporte,
        generado=_en_palabras(date.today().isoformat()))
    salida = Path(destino)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    return salida
