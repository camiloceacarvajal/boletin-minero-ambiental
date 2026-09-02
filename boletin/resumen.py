"""Resumidor: sentencia completa -> titular de una línea + párrafo + si destaca.

El titular imita el registro de La Quinta Sala: la regla jurídica, no el caso.
  'Convalidación del despido en audiencia preparatoria'
  'Pureza no es requisito en tráfico de drogas'

No es latencia-sensible, así que la vía barata es la Batch API (50% menos).
`resumir_lote` usa lotes; `resumir` hace una llamada suelta para probar.
"""
import json
import os

MODELO = "claude-opus-5"

SISTEMA = """Eres un abogado chileno que redacta boletines de jurisprudencia.

Recibes el texto de una sentencia. Devuelves:

- titular: la REGLA JURÍDICA que fija el fallo, en una línea de 6 a 14 palabras,
  sin nombres de partes, sin verbos conjugados en pasado narrativo. Es un
  enunciado de doctrina, no un resumen del caso.
  Bien: "Cláusula de aceleración facultativa y prescripción"
  Bien: "Nulidad de derecho público es improcedente respecto de sentencias"
  Mal:  "La Corte rechazó el recurso de casación de la empresa X"

- resumen: 2 a 4 frases. Qué se discutía, qué resolvió y con qué fundamento.

- materia: una de: civil, penal, laboral, administrativo, constitucional,
  ambiental, tributario, familia, comercial.

- interes: 1 a 5. Cuánto le importa a un abogado en ejercicio.
  5 = cambia o unifica criterio. 1 = aplicación rutinaria sin novedad.

- normas: artículos y leyes citados como decisivos (máx. 6, formato "art. 894 CC").

Si el texto está truncado o ilegible, dilo en resumen y pon interes 1."""

ESQUEMA = {
    "type": "object",
    "properties": {
        "titular": {"type": "string"},
        "resumen": {"type": "string"},
        "materia": {"type": "string", "enum": [
            "civil", "penal", "laboral", "administrativo", "constitucional",
            "ambiental", "tributario", "familia", "comercial"]},
        "interes": {"type": "integer", "minimum": 1, "maximum": 5},
        "normas": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["titular", "resumen", "materia", "interes", "normas"],
    "additionalProperties": False,
}

SALIDA = {"format": {"type": "json_schema", "schema": ESQUEMA}}


def _cliente():
    import anthropic
    return anthropic.Anthropic()


def _peticion(rol, texto):
    return {
        # Sin cache_control a propósito: el prefijo mínimo cacheable son ~1024
        # tokens y este sistema ronda los 350, así que no cachearía igual. La
        # palanca de coste aquí es la Batch API, no el caché.
        "system": SISTEMA,
        "messages": [{"role": "user",
                      "content": f"Sentencia rol {rol}:\n\n<sentencia>\n{texto}\n</sentencia>"}],
        "output_config": {**SALIDA, "effort": "medium"},
        "thinking": {"type": "adaptive"},
        "max_tokens": 8000,
        "model": MODELO,
    }


def resumir(rol, texto):
    """Una sentencia, respuesta inmediata. Para probar y para urgencias."""
    r = _cliente().messages.create(**_peticion(rol, texto))
    return json.loads(next(b.text for b in r.content if b.type == "text"))


def resumir_lote(items):
    """items: [(id_local, rol, texto)]. Devuelve {id_local: dict}.

    Batch API: mitad de precio, hasta 24 h de espera. Para un boletín semanal
    la espera no molesta y el ahorro es la diferencia entre viable y no viable.
    """
    from anthropic.types.messages.batch_create_params import Request
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming

    cli = _cliente()
    lote = cli.messages.batches.create(requests=[
        Request(custom_id=str(i),
                params=MessageCreateParamsNonStreaming(**_peticion(rol, texto)))
        for i, rol, texto in items
    ])
    return lote.id


def recoger_lote(lote_id):
    """Lee un lote ya terminado. Los resultados llegan en cualquier orden:
    se indexan por custom_id, nunca por posición."""
    cli = _cliente()
    estado = cli.messages.batches.retrieve(lote_id)
    if estado.processing_status != "ended":
        return None
    salida = {}
    for res in cli.messages.batches.results(lote_id):
        if res.result.type != "succeeded":
            salida[res.custom_id] = {"error": res.result.type}
            continue
        msg = res.result.message
        texto = next(b.text for b in msg.content if b.type == "text")
        salida[res.custom_id] = json.loads(texto)
    return salida


def hay_credenciales():
    return bool(os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.path.exists(os.path.expanduser("~/.config/anthropic")))
