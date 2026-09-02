#!/usr/bin/env python3
"""Boletín de jurisprudencia — línea de comandos.

  python3 cli.py ingestar            # raspa la fuente y guarda lo nuevo
  python3 cli.py bajar --n 20        # descarga los PDF pendientes
  python3 cli.py extraer             # PDF -> texto
  python3 cli.py clasificar          # marca las sentencias mineras
  python3 cli.py indexar             # normas citadas, artículos y sub-materia
  python3 cli.py preparar --auto     # titular desde la tabla de contenidos (gratis)
  python3 cli.py preparar            # vuelca a pendientes.json para redactarlo
  python3 cli.py cargar              # y lo devuelve a la base
  python3 cli.py resumir --n 10      # alternativa: API de pago
  python3 cli.py veta               # BOLETÍN MINERO -> publico/veta.html
  python3 cli.py publicar            # boletín general -> publico/index.html
  python3 cli.py reportar --dias 7   # reporte del periodo, listo para PDF
"""
import argparse
import sys
from pathlib import Path

from boletin import almacen, documentos, fuentes, sitio

BASE = Path(__file__).parent
DB = BASE / "boletin.db"
PDFS = BASE / "pdfs"


def ingestar(args):
    nuevas = total = 0
    with almacen.abrir(DB) as con:
        for reg in fuentes.FUENTES[args.fuente]():
            total += 1
            nuevas += almacen.guardar(con, reg)
    print(f"{total} sentencias en la fuente, {nuevas} nuevas")


def bajar(args):
    with almacen.abrir(DB) as con:
        pend = con.execute(
            "SELECT id, rol, url_pdf FROM sentencias "
            "WHERE ruta_pdf IS NULL AND url_pdf IS NOT NULL "
            + ("AND minero = 1 " if args.minero else "")
            + "ORDER BY puntaje_min DESC, fecha_fallo DESC LIMIT ?", (args.n,)).fetchall()
        for f in pend:
            destino = PDFS / f"{f['rol'].replace(' ', '_')}.pdf"
            try:
                fuentes.descargar_pdf(f["url_pdf"], destino)
                almacen.actualizar(con, f["id"], ruta_pdf=str(destino))
                print(f"  ok  {f['rol']}")
            except Exception as e:
                print(f"  --  {f['rol']}: {type(e).__name__}", file=sys.stderr)
    print(f"{len(pend)} descargas intentadas")


def extraer(args):
    n = 0
    with almacen.abrir(DB) as con:
        pend = con.execute(
            "SELECT id, rol, ruta_pdf FROM sentencias "
            "WHERE texto IS NULL AND ruta_pdf IS NOT NULL LIMIT ?", (args.n,)).fetchall()
        for f in pend:
            try:
                t = documentos.texto_de_pdf(f["ruta_pdf"])
                almacen.actualizar(con, f["id"], texto=t)
                n += 1
                print(f"  ok  {f['rol']}  ({len(t):,} caracteres)")
            except Exception as e:
                print(f"  --  {f['rol']}: {e}", file=sys.stderr)
    print(f"{n} textos extraídos")


def resumir(args):
    from boletin import resumen
    if not resumen.hay_credenciales():
        sys.exit("sin credenciales: exporta ANTHROPIC_API_KEY o corre `ant auth login`")
    with almacen.abrir(DB) as con:
        pend = con.execute(
            "SELECT id, rol, texto FROM sentencias "
            "WHERE titular IS NULL AND texto IS NOT NULL LIMIT ?", (args.n,)).fetchall()
        for f in pend:
            r = resumen.resumir(f["rol"], documentos.trozos_relevantes(f["texto"]))
            almacen.actualizar(con, f["id"], titular=r["titular"], resumen=r["resumen"],
                               materia=r["materia"], destacada=int(r["interes"] >= 4))
            print(f"  [{r['interes']}] {f['rol']}  {r['titular']}")


def publicar(args):
    with almacen.abrir(DB) as con:
        filas = [dict(r) for r in con.execute(
            "SELECT * FROM sentencias WHERE fecha_fallo IS NOT NULL "
            "ORDER BY fecha_fallo DESC LIMIT ?", (args.n,)).fetchall()]
    ruta = sitio.generar(filas, destino=BASE / "publico" / "index.html",
                         plantillas=BASE / "plantillas")
    print(f"{len(filas)} sentencias -> {ruta}")


def reportar(args):
    """Reporte del periodo: solo sentencias ya resumidas."""
    from datetime import date, timedelta
    hasta = args.hasta or date.today().isoformat()
    desde = args.desde or (date.fromisoformat(hasta) - timedelta(days=args.dias)).isoformat()
    with almacen.abrir(DB) as con:
        filas = con.execute(
            "SELECT * FROM sentencias WHERE titular IS NOT NULL "
            "AND fecha_fallo BETWEEN ? AND ? ORDER BY fecha_fallo DESC",
            (desde, hasta)).fetchall()
    if not filas:
        sys.exit(f"nada resumido entre {desde} y {hasta}: corre `resumir` primero")
    ruta = sitio.reporte(filas, destino=BASE / "publico" / f"reporte-{hasta}.html",
                         plantillas=BASE / "plantillas", desde=desde, hasta=hasta)
    print(f"{len(filas)} sentencias -> {ruta}")


def clasificar(args):
    """Marca las sentencias mineras. Determinista, sin coste, reejecutable."""
    from boletin.minero import es_minero, puntaje
    n = 0
    with almacen.abrir(DB) as con:
        for f in con.execute("SELECT id, descripcion, caratulado, titular FROM sentencias"):
            campo = " ".join(filter(None, (f["descripcion"], f["caratulado"], f["titular"])))
            m = es_minero(campo)
            almacen.actualizar(con, f["id"], minero=int(m), puntaje_min=puntaje(campo))
            n += m
    print(f"{n} sentencias mineras marcadas")


def indexar(args):
    """Extrae normas, artículos y sub-materias del texto. Gratis y reejecutable."""
    from boletin import materias, normas
    n = 0
    with almacen.abrir(DB) as con:
        filas = con.execute("SELECT id, texto, descripcion, resumen, titular "
                            "FROM sentencias").fetchall()
        for f in filas:
            largo = f["texto"] or ""
            corto = " ".join(filter(None, (f["titular"], f["resumen"], f["descripcion"])))
            base = largo or corto
            almacen.actualizar(
                con, f["id"],
                normas="|".join(normas.extraer(largo)) or None,
                articulos="|".join(normas.articulos(largo)) or None,
                submaterias="|".join(materias.clasificar(base)))
            n += 1
    print(f"{n} sentencias indexadas")


def preparar(args):
    """Vuelca lo pendiente a un JSON para redactar los titulares a mano o en
    una sesión de Claude Code, sin gastar API."""
    import json
    from boletin.controversias import titular_tentativo
    with almacen.abrir(DB) as con:
        items = almacen.exportar_pendientes(con, args.n)
        if args.auto:
            escritos = 0
            for it in items:
                f = con.execute("SELECT texto, resuelve FROM sentencias WHERE id=?",
                                (it["id"],)).fetchone()
                t = titular_tentativo(f["texto"], f["resuelve"])
                if not t:          # sentencia sin tabla de contenidos: se deja pendiente
                    continue
                almacen.actualizar(con, it["id"], titular=t)
                escritos += 1
            print(f"{escritos} titulares automáticos escritos "
                  f"({len(items) - escritos} sin tabla de contenidos, quedan pendientes)")
            return
    destino = BASE / "pendientes.json"
    destino.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(items)} sentencias -> {destino}")
    print("Redacta 'titular' y 'resumen' en ese archivo y luego: python3 cli.py cargar")


def cargar(args):
    """Lee pendientes.json ya redactado y lo guarda en la base."""
    import json
    ruta = Path(args.archivo)
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    n = 0
    with almacen.abrir(DB) as con:
        for it in datos:
            if not it.get("titular"):
                continue
            almacen.actualizar(con, it["id"], titular=it["titular"],
                               resumen=it.get("resumen"),
                               materia=it.get("materia", "ambiental"),
                               destacada=int(it.get("interes", 3) >= 4))
            n += 1
    print(f"{n} titulares cargados")


def veta(args):
    """Publica el boletín minero."""
    with almacen.abrir(DB) as con:
        filas = [dict(r) for r in con.execute(
            "SELECT * FROM sentencias WHERE minero = 1 "
            "ORDER BY fecha_fallo DESC").fetchall()]
    ruta = sitio.minero(filas, destino=BASE / "publico" / "veta.html",
                        plantillas=BASE / "plantillas")
    print(f"{len(filas)} sentencias mineras -> {ruta}")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ingestar"); a.add_argument("--fuente", default="2ta"); a.set_defaults(f=ingestar)
    a = sub.add_parser("bajar")
    a.add_argument("--n", type=int, default=20)
    a.add_argument("--minero", action="store_true", help="solo sentencias mineras")
    a.set_defaults(f=bajar)
    a = sub.add_parser("extraer");  a.add_argument("--n", type=int, default=20); a.set_defaults(f=extraer)
    a = sub.add_parser("resumir");  a.add_argument("--n", type=int, default=10); a.set_defaults(f=resumir)
    a = sub.add_parser("publicar"); a.add_argument("--n", type=int, default=60); a.set_defaults(f=publicar)
    a = sub.add_parser("clasificar"); a.set_defaults(f=clasificar)
    a = sub.add_parser("indexar"); a.set_defaults(f=indexar)
    a = sub.add_parser("preparar")
    a.add_argument("--n", type=int, default=40)
    a.add_argument("--auto", action="store_true",
                   help="escribe titulares desde la tabla de contenidos, sin intervención")
    a.set_defaults(f=preparar)
    a = sub.add_parser("cargar")
    a.add_argument("--archivo", default=str(BASE / "pendientes.json"))
    a.set_defaults(f=cargar)
    a = sub.add_parser("veta"); a.set_defaults(f=veta)
    a = sub.add_parser("reportar")
    a.add_argument("--dias", type=int, default=7)
    a.add_argument("--desde"); a.add_argument("--hasta")
    a.set_defaults(f=reportar)

    args = p.parse_args()
    args.f(args)


if __name__ == "__main__":
    main()
