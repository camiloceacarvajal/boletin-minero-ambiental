"""PDF -> texto. Usa pdftotext (poppler), que es rápido y no necesita ruedas."""
import re
import shutil
import subprocess

TIENE_PDFTOTEXT = shutil.which("pdftotext") is not None


def texto_de_pdf(ruta, max_paginas=60):
    if not TIENE_PDFTOTEXT:
        raise RuntimeError("falta pdftotext: sudo apt install poppler-utils")
    salida = subprocess.run(
        ["pdftotext", "-l", str(max_paginas), "-nopgbrk", str(ruta), "-"],
        capture_output=True, text=True, timeout=120,
    )
    return _normalizar(salida.stdout)


def _normalizar(t):
    """Las sentencias del PJUD vienen con el texto espaciado ('rechaz ó')."""
    t = re.sub(r"(\w) (?=[óáéíúñ])", r"\1", t)      # corta la separación por tildes
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def trozos_relevantes(texto, limite_chars=60_000):
    """Una sentencia larga no cabe entera ni conviene: lo que decide está al
    principio (VISTOS) y al final (lo resolutivo). Nos quedamos con las puntas."""
    if len(texto) <= limite_chars:
        return texto
    mitad = limite_chars // 2
    return texto[:mitad] + "\n\n[... texto intermedio omitido ...]\n\n" + texto[-mitad:]


MINIMO_UTIL = 1500   # bajo esto, el PDF es una imagen escaneada sin capa de texto
MINIMO_POR_PAGINA = 400   # una resolución de una página son ~900 caracteres
TIENE_OCR = shutil.which("tesseract") is not None and shutil.which("pdftoppm") is not None


def es_escaneado(texto, paginas=None):
    """Un umbral fijo descarta documentos cortos legítimos: las resoluciones de
    una página rondan los 900 caracteres. Cuando se sabe cuántas páginas tiene,
    el umbral se escala; si no, se usa el fijo."""
    n = len((texto or "").strip())
    if paginas:
        return n < min(MINIMO_UTIL, paginas * MINIMO_POR_PAGINA)
    return n < MINIMO_UTIL


def _paginas(ruta):
    r = subprocess.run(["pdfinfo", str(ruta)], capture_output=True, text=True, timeout=60)
    m = re.search(r"Pages:\s+(\d+)", r.stdout)
    return int(m.group(1)) if m else 0


def ocr(ruta, cabeza=12, cola=8, dpi=150, idioma="spa"):
    """OCR de las puntas del documento, no de todo.

    Rasterizar 140 paginas a 200 dpi son ~10 min por sentencia y no compensa:
    lo que hace falta para titular e indexar normas esta en los VISTOS y en la
    parte resolutiva. Se rescatan `cabeza` paginas del principio y `cola` del
    final; a 150 dpi tesseract sigue leyendo bien un PDF de texto rasterizado.
    """
    import tempfile
    from pathlib import Path as _P
    if not TIENE_OCR:
        raise RuntimeError("falta tesseract o poppler: sudo apt install tesseract-ocr-spa poppler-utils")

    total = _paginas(ruta)
    tramos = [(1, min(cabeza, total or cabeza))]
    if total and total > cabeza + cola:
        tramos.append((total - cola + 1, total))

    piezas = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (desde, hasta) in enumerate(tramos):
            subprocess.run(["pdftoppm", "-r", str(dpi), "-gray",
                            "-f", str(desde), "-l", str(hasta),
                            "-png", str(ruta), f"{tmp}/t{i}"],
                           capture_output=True, timeout=600, check=True)
        for png in sorted(_P(tmp).glob("t*.png")):
            r = subprocess.run(["tesseract", str(png), "stdout", "-l", idioma,
                                "--psm", "1"],
                               capture_output=True, text=True, timeout=120)
            piezas.append(r.stdout)
    return _normalizar("\n".join(piezas))
