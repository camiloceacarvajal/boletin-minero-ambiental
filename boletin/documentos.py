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


MINIMO_UTIL = 3000   # bajo esto, el PDF es una imagen escaneada sin capa de texto
TIENE_OCR = shutil.which("tesseract") is not None and shutil.which("pdftoppm") is not None


def es_escaneado(texto):
    return len((texto or "").strip()) < MINIMO_UTIL


def ocr(ruta, max_paginas=40, idioma="spa"):
    """Rasteriza y pasa OCR. Lento (~1-3 s por página) pero rescata los fallos
    de 2013-2019 del 2TA, que se publicaron como imagen."""
    import tempfile
    if not TIENE_OCR:
        raise RuntimeError("falta tesseract o poppler: sudo apt install tesseract-ocr-spa poppler-utils")
    piezas = []
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "200", "-gray", "-l", str(max_paginas),
                        "-png", str(ruta), f"{tmp}/p"],
                       capture_output=True, timeout=900, check=True)
        from pathlib import Path as _P
        for png in sorted(_P(tmp).glob("p-*.png")):
            r = subprocess.run(["tesseract", str(png), "stdout", "-l", idioma, "--psm", "1"],
                               capture_output=True, text=True, timeout=180)
            piezas.append(r.stdout)
    return _normalizar("\n".join(piezas))
