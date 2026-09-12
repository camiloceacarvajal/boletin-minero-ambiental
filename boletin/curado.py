"""Capa curada: lo que no se puede volver a raspar.

Los datos del boletín son de dos clases:

  RASPADO   rol, carátula, fecha, región, enlaces. Se vuelve a pedir al tribunal
            en cada corrida y siempre está fresco. No se versiona.

  CURADO    la doctrina y el resumen redactados a mano, más lo que se extrajo
            del PDF (normas, artículos, rastro de la Corte Suprema). Cuesta
            horas de trabajo y descargas de cientos de megas. Se versiona.

Sin esta separación, las 148 doctrinas viven solo en un SQLite que git ignora
—se pierden con el archivo— y la integración continua no puede reconstruir la
página sin bajar 182 MB de PDFs y correr OCR.
"""
import json
from pathlib import Path

RUTA = Path("datos/curado.json")

# Lo que se guarda. Clave: (fuente, rol).
CAMPOS = ("titular", "resumen", "destacada", "normas", "articulos",
          "submaterias", "corte_sup", "resuelve_inf", "estado_texto")


def exportar(con, ruta=RUTA):
    filas = con.execute(
        f"SELECT fuente, rol, {', '.join(CAMPOS)} FROM sentencias "
        "WHERE titular IS NOT NULL OR normas IS NOT NULL OR corte_sup IS NOT NULL "
        "ORDER BY fuente, rol").fetchall()
    datos = []
    for f in filas:
        reg = {"fuente": f["fuente"], "rol": f["rol"]}
        reg.update({c: f[c] for c in CAMPOS if f[c] is not None})
        datos.append(reg)
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys + indent para que el diff de git sea legible línea a línea.
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    return len(datos)


def importar(con, ruta=RUTA):
    """Vuelca el curado sobre lo raspado. Solo escribe lo que trae el archivo."""
    ruta = Path(ruta)
    if not ruta.exists():
        return 0, 0
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    puestas = huerfanas = 0
    for reg in datos:
        campos = {c: reg[c] for c in CAMPOS if c in reg}
        if not campos:
            continue
        sets = ", ".join(f"{c} = ?" for c in campos)
        n = con.execute(f"UPDATE sentencias SET {sets} WHERE fuente = ? AND rol = ?",
                        (*campos.values(), reg["fuente"], reg["rol"])).rowcount
        if n:
            puestas += 1
        else:
            # La causa está curada pero ya no aparece en el listado del tribunal:
            # o cambió de rol, o la retiraron. Conviene saberlo, no callarlo.
            huerfanas += 1
    con.commit()
    return puestas, huerfanas
