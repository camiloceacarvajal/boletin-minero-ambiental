#!/usr/bin/env bash
# Flujo completo del boletín minero. Todo gratis: sin API de pago.
set -euo pipefail
cd "$(dirname "$0")"
python3 cli.py ingestar --fuente 1ta      # tribunal del norte minero
python3 cli.py ingestar --fuente 2ta      # tribunal del centro
python3 cli.py clasificar                 # marca lo minero
python3 cli.py bajar   --minero --n 25    # PDFs de las mineras
python3 cli.py extraer --n 25             # PDF -> texto
python3 cli.py indexar                    # normas, artículos, sub-materia (tras tener texto)
python3 cli.py preparar --auto            # titular desde la tabla de contenidos
python3 cli.py veta                       # publico/veta.html
python3 cli.py reportar --dias 3650       # reporte imprimible
