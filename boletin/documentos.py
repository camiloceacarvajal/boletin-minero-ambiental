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
