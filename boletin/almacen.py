"""Almacén SQLite. Una fila por sentencia, idempotente por (fuente, rol)."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS sentencias (
    id           INTEGER PRIMARY KEY,
    fuente       TEXT NOT NULL,          -- '2ta', 'cs', ...
    rol          TEXT NOT NULL,          -- 'R-574-2025'
    materia      TEXT,                   -- sala / tipo de procedimiento
    caratulado   TEXT,                   -- partes
    descripcion  TEXT,                   -- texto crudo del listado
    region       TEXT,
    fecha_fallo  TEXT,                   -- ISO 8601
    resuelve     TEXT,                   -- 'rechaza' | 'acoge' | ... (lo publica el tribunal)
    resuelve_inf TEXT,                   -- deducido del PDF cuando el tribunal no lo publica
    url_pdf      TEXT,
    url_expediente TEXT,
    ruta_pdf     TEXT,                   -- copia local
    texto        TEXT,                   -- texto extraído del PDF
    estado_texto TEXT,                   -- ok | escaneado | ocr | ocr_fallido
    titular      TEXT,                   -- el resumen de una línea
    resumen      TEXT,                   -- párrafo
    destacada    INTEGER DEFAULT 0,      -- entra al boletín
    minero       INTEGER DEFAULT 0,      -- clasificador de boletin.minero
    puntaje_min  INTEGER DEFAULT 0,      -- cuántas señales mineras distintas
    normas       TEXT,                   -- leyes citadas, separadas por |
    articulos    TEXT,                   -- artículos más invocados
    submaterias  TEXT,                   -- sancionatorio / evaluación / ...
    corte_sup    TEXT,                   -- anexada · N Sala | citada | NULL
    redactor     TEXT,                   -- ministro/a que redactó (solo 3TA)
    competencia  TEXT,                   -- numeral del art. 17 Ley 20.600 (solo 3TA)
    video        TEXT,                   -- audiencia de alegatos (solo 3TA)
    visto_en     TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (fuente, rol)
);
CREATE INDEX IF NOT EXISTS idx_fecha ON sentencias (fecha_fallo DESC);
CREATE INDEX IF NOT EXISTS idx_pend  ON sentencias (titular) WHERE titular IS NULL;
"""


@contextmanager
def abrir(ruta="boletin.db", timeout=30):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    # timeout: un paso largo (bajar, ocr) puede tener la base tomada.
    con = sqlite3.connect(ruta, timeout=timeout)
    con.row_factory = sqlite3.Row
    con.executescript(ESQUEMA)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def guardar(con, reg):
    """Inserta si es nueva. Devuelve True si era nueva."""
    cur = con.execute(
        """INSERT OR IGNORE INTO sentencias
           (fuente, rol, materia, caratulado, descripcion, region,
            fecha_fallo, resuelve, url_pdf, url_expediente, titular, resumen,
            redactor, competencia, video)
           VALUES (:fuente, :rol, :materia, :caratulado, :descripcion, :region,
                   :fecha_fallo, :resuelve, :url_pdf, :url_expediente,
                   :titular, :resumen, :redactor, :competencia, :video)""",
        {k: reg.get(k) for k in (
            "fuente", "rol", "materia", "caratulado", "descripcion", "region",
            "fecha_fallo", "resuelve", "url_pdf", "url_expediente",
            "titular", "resumen", "redactor", "competencia", "video")},
    )
    return cur.rowcount > 0


def pendientes(con, campo="titular", limite=50):
    return con.execute(
        f"SELECT * FROM sentencias WHERE {campo} IS NULL AND url_pdf IS NOT NULL"
        " ORDER BY fecha_fallo DESC LIMIT ?", (limite,)).fetchall()


def actualizar(con, id_, **campos):
    """Escribe y confirma de inmediato: los pasos largos (bajar, ocr) no deben
    retener la transacción durante minutos ni perder el trabajo si se cortan."""
    sets = ", ".join(f"{k} = ?" for k in campos)
    con.execute(f"UPDATE sentencias SET {sets} WHERE id = ?",
                (*campos.values(), id_))
    con.commit()


def exportar_pendientes(con, limite=40):
    """Sentencias con texto pero sin titular, con su tabla de contenidos."""
    from boletin.controversias import extraer
    filas = con.execute(
        "SELECT id, rol, resuelve, region, descripcion, texto FROM sentencias "
        "WHERE titular IS NULL AND texto IS NOT NULL "
        "ORDER BY fecha_fallo DESC LIMIT ?", (limite,)).fetchall()
    return [{
        "id": f["id"], "rol": f["rol"], "resuelve": f["resuelve"],
        "region": f["region"], "descripcion": (f["descripcion"] or "")[:400],
        "controversias": extraer(f["texto"]),
    } for f in filas]
