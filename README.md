# La Veta — boletín de jurisprudencia minero-ambiental

Ingesta, clasificación, resumen y publicación de sentencias de los tribunales
ambientales chilenos sobre faenas, concesiones y proyectos mineros.
Mismo modelo que [La Quinta Sala](https://laquintasala.cl), en Python, **sin API de pago**.

## Todo de una vez

```bash
./flujo.sh
```

Tarda ~5 min la primera vez (descarga PDFs) y ~30 s las siguientes.
Salida: `publico/veta.html` (el boletín) y `publico/reporte-*.html` (imprimible a PDF).

## Paso a paso

```bash
python3 cli.py ingestar --fuente 1ta   # Primer T.A. (Antofagasta): el norte minero
python3 cli.py ingestar --fuente 2ta   # Segundo T.A. (Santiago)
python3 cli.py clasificar              # marca lo minero
python3 cli.py indexar                 # normas citadas, artículos, sub-materia
python3 cli.py bajar --minero --n 120  # descarga los PDF de las mineras
python3 cli.py extraer                 # PDF -> texto
python3 cli.py ocr --minero --n 40     # rescata los escaneados (2013-2019)
python3 cli.py preparar --auto         # titular desde la tabla de contenidos
python3 cli.py veta                    # publica el boletín
python3 cli.py reportar --dias 7       # reporte del periodo
```

Cada paso es idempotente: se puede cortar y retomar sin duplicar nada.

## Las dos fuentes, y por qué estas

| | Aporta | Cobertura |
|---|---|---|
| **1.º T.A.** (`1ta`) | Titular y resumen **ya redactados por el tribunal** en su sala de prensa | 46% minero |
| **2.º T.A.** (`2ta`) | Tabla estructurada + PDF de la sentencia íntegra | 17% minero |

`juris.pjud.cl` (Corte Suprema) queda fuera: su `robots.txt` es `Disallow: /`
para todo agente y el buscador va tras reCAPTCHA.

## Cómo se redacta el titular, sin pagar

1. **`preparar --auto`** — gratis y determinista. Las sentencias del 2.º T.A. abren
   con una TABLA DE CONTENIDOS donde el propio tribunal enumera las controversias;
   de ahí sale el titular. Las del 1.º T.A. ya vienen con titular escrito.
2. **`preparar` + `cargar`** — vuelca lo pendiente a `pendientes.json`, se redacta
   a mano (o en una sesión de Claude Code, que ya está pagada en la suscripción) y
   se devuelve a la base con `cargar`.
3. **`resumir`** — vía API de pago. Está implementada, pero **no hace falta**.

## Pruebas

```bash
python3 pruebas.py
```

47 pruebas: clasificador minero (18 casos), normalización de PDF, extracción de
la tabla de contenidos, idempotencia del almacén, integridad de la base real y
la página generada (temas, recursos externos, índice de búsqueda).

## Añadir un tribunal

Una función en `boletin/fuentes.py` que rinda dicts con las claves de
`almacen.ESQUEMA`, registrada en `FUENTES`. El 3.º T.A. (Valdivia) es el siguiente.

## Comparación con La Quinta Sala (su reporte N° 47)

Su producto real no es la web: es un dashboard HTML autocontenido, embebido en un
iframe en `/reporte-semanal/`, con 88 sentencias de una semana. Campos: `sala`,
`desc`, `doctrina` (~124 car.), `resumen` (~740 car.), `materia`, `palabras`, `cat`.

| | La Quinta Sala | La Veta |
|---|---|---|
| Sentencias | 88 (una semana) | 106 (2016-2026) |
| Rol de la causa | **no** | 106/106 |
| Fecha del fallo | solo el rango de la semana | 93/106 |
| Región | **no** | 96/106 |
| Enlace a la sentencia | **no** | 15/106 |
| Enlace al expediente | **no** | 105/106 |
| Doctrina de una línea | 88/88, redactada | 37/106, automática |
| Resumen | 88/88, redactado | 30/106 |
| Normas citadas | a mano | extraídas del texto íntegro |
| Filtros | sala, resultado | tribunal, resultado, PDF, 9 materias |

**Dónde les ganamos:** trazabilidad. Ellos publican doctrina sin rol, sin fecha
individual, sin región y sin enlace al fallo — hay que creerles. Cada ficha nuestra
lleva el rol, la fecha, la región y el enlace al expediente del tribunal.
Y como tenemos el PDF, el índice de normas sale del texto, no de lo que el editor
recordó teclear: se puede preguntar qué fallos aplican el art. 17 N° 8 de la Ley
20.600 y obtener la respuesta.

**Dónde nos ganan, y es lo que importa:** la redacción. Sus 88 doctrinas están
escritas por un abogado, una por una. Las nuestras cubren 37 de 106 y salen de la
tabla de contenidos del propio tribunal — sirven para orientarse, no son doctrina.
Ese hueco no lo cierra más código: se cierra redactando, o descargando los 91 PDF
que faltan para que el índice de normas cubra el total.

## PDF escaneados

Los fallos del 2.º T.A. anteriores a ~2019 se publicaron como imagen, sin capa de
texto. `extraer` los detecta y los marca `estado_texto='escaneado'` en vez de
guardar una cadena vacía; `ocr` los rescata con tesseract en español. Es lento
(1-3 s por página), así que va como paso aparte y opcional.
