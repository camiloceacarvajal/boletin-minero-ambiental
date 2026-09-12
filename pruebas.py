#!/usr/bin/env python3
"""Pruebas del boletín. Corre con: python3 pruebas.py

No usa red salvo en las marcadas [red]. Cada prueba imprime ok/FALLA.
"""
import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from boletin import almacen, controversias, materias, minero, normas, sitio
from boletin.documentos import MINIMO_UTIL, _normalizar

FALLOS = []


def prueba(nombre, cond, detalle=""):
    print(f"  {'ok  ' if cond else 'FALLA'} {nombre}" + (f"  — {detalle}" if detalle and not cond else ""))
    if not cond:
        FALLOS.append(nombre)


print("\n== clasificador minero ==")
POSITIVOS = ["multa a Codelco por la SMA", "tranque de relaves El Torito",
             "prospección minera Campanario", "faena minera de Escondida",
             "extracción de áridos del río", "planta de beneficio de cobre",
             "sondajes mineros de prefactibilidad", "SQM salar de Llamara",
             "Compañía Minera del Pacífico", "pila de lixiviación"]
# Regresión: 'Andina' (por Codelco División Andina) hacía match dentro de
# 'Aguas Andinas' y colaba la planta de tratamiento del Mapocho al boletín.
POSITIVOS += ["Codelco División Andina depósito de lastre", "Codelco División El Salvador",
              # El 3TA solo publica la carátula: la razón social tiene que bastar.
              "Canteras Lonco S.A con Superintendencia del Medio Ambiente",
              "Aridos y Constructora San Vicente LTDA.",
              "Sociedad Comercializadora de Carbón SpA"]
NEGATIVOS = ["Aguas Andinas S.A. planta de tratamiento",
             "Salmones Camanchaca S.A. con SMA",
             "Forestal Arauco S.A. con Servicio de Evaluación Ambiental",
             "Ilustre Municipalidad de Coronel con SEA",
             "la ciudad de El Salvador en Centroamérica",
             "cordillera andina y su fauna",
             "humedal urbano Tranque La Poza", "Santuario de la Naturaleza Río Sasso",
             "multa por ruidos a un restaurante", "planta fotovoltaica Quilicura",
             "Parque Nacional Torres del Paine", "caudal ecológico del río Mapocho",
             "emisión de ruidos de un pub", "aceites lubricantes usados Ley REP"]
for t in POSITIVOS:
    prueba(f"minero: {t[:42]}", minero.es_minero(t))
for t in NEGATIVOS:
    prueba(f"NO minero: {t[:39]}", not minero.es_minero(t))
prueba("puntaje ordena por señales", minero.puntaje("Codelco relaves faena minera") > minero.puntaje("cobre extracción"))

print("\n== normalización de texto del PDF ==")
prueba("recompone tildes partidas", _normalizar("rechaz ó la acci ón") == "rechazó la acción",
       repr(_normalizar("rechaz ó la acci ón")))
prueba("colapsa saltos de línea", "\n\n\n" not in _normalizar("a\n\n\n\n\nb"))

print("\n== tabla de contenidos -> titular ==")
TOC = """TABLA DE CONTENIDOS
VISTOS: .................................. 2
I. Antecedentes de la reclamación ......... 2
II. Del proceso de reclamación judicial ... 4
CONSIDERANDO: ............................ 6
I. Eventual ineficacia del procedimiento administrativo ... 9
III. Posibilidad de presentar PdC cuando la SMA impute cargos por daño ambiental ... 26
SE RESUELVE: ............................. 40"""
cs = controversias.extraer(TOC)
prueba("extrae las controversias", len(cs) == 2, f"obtuvo {cs}")
prueba("descarta 'Antecedentes'", not any("Antecedentes" in c for c in cs))
prueba("descarta 'VISTOS'", not any(c.upper().startswith("VISTOS") for c in cs))
prueba("sin números de página", not any(re.search(r"\d{1,3}$", c) for c in cs), str(cs))
t = controversias.titular_tentativo(TOC, "acoge")
prueba("titular lleva el resultado", t and t.endswith("— acoge"), str(t))
prueba("titular quita 'Eventual'", t and not t.lower().startswith("eventual"), str(t))
prueba("sin tabla devuelve None", controversias.titular_tentativo("texto cualquiera") is None)

print("\n== umbral de texto útil ==")
from boletin.documentos import es_escaneado
# Una resolución de una página ronda los 900 caracteres: el umbral fijo la
# descartaba como si fuera una imagen en blanco.
prueba("913 caracteres en 1 página sirven", not es_escaneado("x" * 913, 1))
prueba("913 caracteres en 40 páginas no", es_escaneado("x" * 913, 40))
prueba("vacío es escaneado siempre", es_escaneado("", 1) and es_escaneado(""))

print("\n== normas citadas ==")
TXT = ("conforme a los artículos 17 N° 3 y 18 de la Ley N° 20.600, y el artículo 53 "
       "de la Ley N° 19.880, en relación con la Ley 19.300 y el D.S. N° 40/2012. "
       "El artículo 17 N° 3 se aplica también según el Código de Aguas. "
       "Y de nuevo el Código de Aguas rige la materia. "
       "Ver artículo 17 N° 3 y artículo 53. Artículo 53 y artículo 53 otra vez. "
       "Ley N° 20.600 y Ley 20.600 y Ley N°20.600.")
ns = normas.extraer(TXT, minimo=2)
prueba("reconoce la Ley 20.600 por su nombre",
       any("20.600" in n and "Tribunales Ambientales" in n for n in ns), str(ns))
prueba("'20600' y '20.600' son la misma ley", normas._norm("20600") == "20.600")
prueba("detecta el Código de Aguas", "Código de Aguas" in ns, str(ns))
prueba("descarta lo citado una sola vez (D.S. 40/2012)", "D.S. 40/2012" not in ns, str(ns))
prueba("la Ley 19.880, citada una vez, tampoco entra",
       not any("19.880" in n for n in ns), str(ns))
arts = normas.articulos(TXT)
prueba("extrae 'art. 17 N° 3'", "art. 17 N° 3" in arts, str(arts))
prueba("extrae 'art. 53'", "art. 53" in arts, str(arts))
prueba("texto vacío no revienta", normas.extraer(None) == [] and normas.articulos("") == [])

print("\n== rastro de la Corte Suprema ==")
prueba("detecta el fallo anexado",
       (normas.corte_suprema("Pronunciado por la Tercera Sala de la Corte Suprema") or "")
       .startswith("anexada"))
prueba("lee el rol de casación del listado",
       normas.corte_suprema(None, "ver Sentencia de la Excma. Corte Suprema rol N° 24.870-2018")
       == "casación rol 24.870-2018")
prueba("limpia el punto sobrante del rol",
       normas.corte_suprema(None, "Sentencia de la Excma. Corte Suprema rol N°117.379.-2020")
       == "casación rol 117.379-2020")
prueba("anuncio sin rol queda como 'resuelta en casación'",
       normas.corte_suprema(None, "ver Sentencia de la Excma. Corte Suprema") == "resuelta en casación")
prueba("el fallo anexado manda sobre el listado",
       (normas.corte_suprema("Pronunciada por la Tercera Sala de la Corte Suprema",
                             "ver Sentencia de la Excma. Corte Suprema") or "").startswith("anexada"))
prueba("sin rastro devuelve None", normas.corte_suprema("texto cualquiera", "otra cosa") is None)

print("\n== sub-materias ==")
prueba("multa en UTA es sancionatorio",
       "Sancionatorio SMA" in materias.clasificar("multa de 56 UTA por la SMA"))
prueba("RCA es evaluación",
       "Evaluación (SEIA)" in materias.clasificar("la resolución de calificación ambiental del proyecto"))
prueba("Convenio 169 es consulta indígena",
       "Consulta indígena" in materias.clasificar("aplicación del Convenio 169 a la comunidad"))
prueba("sin señales cae en 'Ambiental'", materias.clasificar("texto neutro") == ["Ambiental"])

print("\n== resultado deducido del fallo ==")
RESOLUTIVO = ("SE RESUELVE: 1. Rechazar la excepción de incompetencia opuesta por la "
              "demandada. 2. Rechazar la alegación de falta de legitimación activa. "
              "3. Acoger la demanda de reparación por daño ambiental interpuesta por "
              "el actor. 4. Cada parte pagará sus costas.")
prueba("lo accesorio no tapa el fondo", controversias.resultado(RESOLUTIVO) == "acoge",
       str(controversias.resultado(RESOLUTIVO)))
DISIDENTE = ("SE RESUELVE: 1. Rechazar la reclamación interpuesta. 2. Cada parte pagará "
             "sus costas. Acordada con el voto en contra del Ministro señor López, "
             "quien estuvo por acoger la reclamación.")
prueba("el voto disidente no invierte el resultado",
       controversias.resultado(DISIDENTE) == "rechaza", str(controversias.resultado(DISIDENTE)))
prueba("sin parte resolutiva devuelve None", controversias.resultado("texto cualquiera") is None)
prueba("texto vacío no revienta", controversias.resultado(None) is None)

print("\n== almacén ==")
tmp = Path("/tmp/prueba_boletin.db")
tmp.unlink(missing_ok=True)
REG = dict(fuente="2ta", rol="R-1-2020", materia="Reclamaciones", caratulado="X con Y",
           descripcion="minera", region="Atacama", fecha_fallo="2020-01-01",
           resuelve="acoge", url_pdf=None, url_expediente=None, titular="T", resumen="R")
with almacen.abrir(tmp) as con:
    prueba("primera inserción es nueva", almacen.guardar(con, REG))
    prueba("segunda es ignorada (idempotente)", not almacen.guardar(con, REG))
    prueba("guarda titular y resumen",
           con.execute("SELECT titular, resumen FROM sentencias").fetchone()[:2] == ("T", "R"))
    otro = {**REG, "rol": "R-2-2020"}
    almacen.guardar(con, otro)
    prueba("rol distinto sí entra",
           con.execute("SELECT COUNT(*) FROM sentencias").fetchone()[0] == 2)
    almacen.actualizar(con, 1, minero=1, puntaje_min=3)
    prueba("actualizar escribe columnas nuevas",
           con.execute("SELECT minero, puntaje_min FROM sentencias WHERE id=1").fetchone()[:2] == (1, 3))
tmp.unlink(missing_ok=True)

print("\n== base real ==")
db = Path("boletin.db")
if not db.exists():
    print("  (sin boletin.db: corre `python3 cli.py ingestar` primero)")
else:
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    q = lambda s: con.execute(s).fetchone()[0]
    total, mineras = q("SELECT COUNT(*) FROM sentencias"), q("SELECT COUNT(*) FROM sentencias WHERE minero=1")
    from boletin.fuentes import FUENTES
    prueba("hay sentencias de cada fuente registrada",
           q("SELECT COUNT(DISTINCT fuente) FROM sentencias") == len(FUENTES),
           f"{q('SELECT COUNT(DISTINCT fuente) FROM sentencias')} fuentes con datos "
           f"de {len(FUENTES)} registradas")
    prueba("el 3TA aporta redactor y competencia",
           q("SELECT COUNT(*) FROM sentencias WHERE fuente='3ta' AND redactor IS NULL") == 0)
    prueba("hay sentencias mineras", mineras > 50, f"{mineras}")
    prueba("las mineras son minoría del total", mineras < total, f"{mineras}/{total}")
    prueba("no hay roles duplicados por fuente",
           q("SELECT COUNT(*) FROM (SELECT fuente,rol FROM sentencias GROUP BY fuente,rol HAVING COUNT(*)>1)") == 0)
    prueba("las fechas son ISO",
           q("SELECT COUNT(*) FROM sentencias WHERE fecha_fallo IS NOT NULL AND fecha_fallo NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'") == 0)
    # Un PDF escaneado no tiene capa de texto: debe quedar explicado, no en silencio.
    prueba("todo PDF descargado tiene texto o motivo",
           q("SELECT COUNT(*) FROM sentencias WHERE ruta_pdf IS NOT NULL "
             "AND texto IS NULL AND estado_texto IS NULL") == 0)
    prueba("todo estado_texto es un valor conocido",
           q("SELECT COUNT(*) FROM sentencias WHERE estado_texto IS NOT NULL "
             "AND estado_texto NOT IN ('ok','escaneado','ocr','ocr_fallido')") == 0)
    prueba("ningún texto guardado está vacío",
           q("SELECT COALESCE(MIN(LENGTH(TRIM(texto))),99999) FROM sentencias "
             "WHERE texto IS NOT NULL") > 0)
    # El 2TA publica el resultado; el 3TA no. Contrastar la heurística contra el
    # dato real del 2TA es la única forma de saber cuánto vale cuando se aplica
    # al 3TA a ciegas. Medido en 95%: si baja de 90, algo se rompió.
    aciertos = fallos = 0
    for f in con.execute("SELECT resuelve, texto FROM sentencias WHERE fuente='2ta' "
                         "AND texto IS NOT NULL AND resuelve IS NOT NULL"):
        d = controversias.resultado(f["texto"])
        if d is None:
            continue
        real = (f["resuelve"] or "").lower()
        if d.split()[0] in real or (d == "acoge parcialmente" and "parcial" in real):
            aciertos += 1
        else:
            fallos += 1
    muestras = aciertos + fallos
    if muestras < 10:
        # Sin PDFs descargados no hay nada que medir. Pasa en integración
        # continua, donde la base se rehace desde el raspado y el curado.
        print(f"  --   deducción del resultado: sin muestra ({muestras} casos con texto)")
    else:
        tasa = 100 * aciertos // muestras
        prueba(f"la deducción del resultado acierta >=95% ({tasa}%)", tasa >= 95,
               f"{aciertos}/{muestras}")

    prueba("el 1TA trae titular y resumen del tribunal",
           q("SELECT COUNT(*) FROM sentencias WHERE fuente='1ta' AND titular IS NULL") == 0)

print("\n== página generada ==")
p = Path("publico/veta.html")
if not p.exists():
    print("  (sin veta.html: corre `python3 cli.py veta`)")
else:
    h = p.read_text(encoding="utf-8")
    n = h.count("<article ")
    prueba("una ficha por sentencia minera", n == mineras, f"{n} fichas vs {mineras} mineras")
    prueba("define el tema claro en :root", ":root{" in h.replace("\n", "").replace(" ", ""))
    prueba("define el tema oscuro", "prefers-color-scheme:dark" in h)
    prueba("permite alternar tema a mano", '[data-theme=dark]' in h)
    # Solo cuenta lo que la página CARGA (src=, <link>), no los enlaces del texto.
    cargas = re.findall(r'src="([^"]+)"', h) + re.findall(r'<link[^>]+href="([^"]+)"', h)
    externas = [u for u in cargas
                if u.startswith(("http://", "//"))
                or (u.startswith("https://")
                    and not re.match(r"https://fonts\.(googleapis|gstatic)\.com", u))]
    prueba("no carga recursos externos salvo tipografías", not externas, str(externas))
    prueba("las tipografías tienen alternativa local",
           "Georgia" in h and "system-ui" in h)
    prueba("el buscador tiene índice en cada ficha", h.count("data-buscar=") == n)
    prueba("los enlaces a PDF son absolutos al tribunal",
           all(u.startswith("https://") for u in re.findall(r'href="([^"]*\.pdf)"', h)))
    prueba("el cuerpo pinta fondo propio", re.search(r"body\{[^}]*background:var\(--bg\)", h) is not None)
    # Cazó un ReferenceError real: 'materia' se usaba sin declarar.
    js = re.search(r"<script>(.*?)</script>", h, re.S)
    js = js.group(1) if js else ""
    declaradas = set(re.findall(r"\b(?:var|let|const|function)\s+(\w+)", js))
    declaradas |= set(re.findall(r",\s*(\w+)\s*=", js))
    declaradas |= set(re.findall(r"function\s*\(([^)]*)\)", js)[0].split(",")) if re.findall(r"function\s*\(([^)]*)\)", js) else set()
    usadas = {"activo", "materia", "fichas", "pintar", "conteo", "vacio"}
    faltan = sorted(u for u in usadas if u not in declaradas)
    prueba("toda variable del JS está declarada", not faltan, f"sin declarar: {faltan}")

print()
if FALLOS:
    print(f"FALLARON {len(FALLOS)}: " + ", ".join(FALLOS))
    sys.exit(1)
print("todas las pruebas pasaron")
