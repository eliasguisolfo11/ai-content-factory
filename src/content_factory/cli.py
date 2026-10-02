from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .providers import OllamaProvider
from .research import collect_sources
from .validation import save_json, validate_script, validate_visuals

ROOT = Path(__file__).resolve().parents[2]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9áéíóúüñ]+", "-", text)
    return text.strip("-")[:70] or "video"


def main() -> int:
    parser = argparse.ArgumentParser(description="Investiga y redacta un guion factual estructurado.")
    parser.add_argument("--account")
    parser.add_argument("--topic")
    parser.add_argument("--format", default="esto-realmente-paso", choices=["esto-realmente-paso", "ultimas-horas", "pov-historico"])
    parser.add_argument("--duration", type=int, default=75)
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"))
    parser.add_argument("--output", default="output")
    parser.add_argument("--check-ollama", action="store_true", help="Comprueba Ollama y muestra sus modelos instalados.")
    args = parser.parse_args()

    llm = OllamaProvider(args.model)
    if args.check_ollama:
        try:
            models = llm.list_models()
        except RuntimeError as exc:
            print(f"Error: {exc}")
            return 2
        print(f"Ollama responde en {llm.base_url}.")
        if models:
            print("Modelos instalados: " + ", ".join(models))
        else:
            print("No hay modelos descargados todavía.")
        if args.model not in models:
            print(f"Falta el modelo seleccionado ({args.model}). Instalalo con: ollama pull {args.model}")
            return 1
        print(f"Modelo listo: {args.model}")
        return 0

    if not args.account or not args.topic:
        parser.error("--account y --topic son obligatorios, salvo que uses --check-ollama.")

    account_path = ROOT / "accounts" / f"{args.account}.json"
    if not account_path.exists():
        parser.error(f"No existe la cuenta: {account_path}")
    account = json.loads(account_path.read_text(encoding="utf-8"))
    print(f"Buscando referencias para: {args.topic}")
    sources = collect_sources(args.topic)
    if len(sources) < 2:
        raise SystemExit("No se encontraron referencias suficientes. Revisá el tema o la conexión.")

    out = Path(args.output) / slugify(args.topic)
    out.mkdir(parents=True, exist_ok=True)
    save_json(out / "sources.json", {"topic": args.topic, "sources": sources,
                                      "research_warning": "Search extracts are leads; verify original pages and cited sources."})
    research = "\n".join(f"[{s['id']}] {s['title']} ({s['language']})\nURL: {s['url']}\nExtract: {s['extract']}" for s in sources)
    (out / "research.md").write_text(f"# Research: {args.topic}\n\n> Las referencias son pistas iniciales, no verificación editorial.\n\n{research}\n", encoding="utf-8")

    prompt = f"""Sos guionista de microdocumentales para {account['name']}.
Reglas editoriales: {account.get('editorial_rules', [])}
Formato: {args.format}. Duración exacta: {args.duration} segundos.
Tema: {args.topic}
Notas de investigación (única base factual permitida):
{research}

Creá 6 a 10 escenas con tiempos contiguos desde 0 hasta {args.duration}, español argentino natural,
narración total adecuada para {args.duration} segundos (aprox. 125-150 palabras por minuto).
Cada escena cita source_ids del listado. El objeto debe incluir title, hook, target_duration, format,
scenes (start,end,narration,visual,caption,source_ids), source_ids y editorial_notes.
No agregues ningún hecho específico que no esté en las notas. Contestá solo JSON válido."""
    print(f"Generando borrador con Ollama ({args.model})…")
    try:
        script = llm.generate_json(prompt)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"No se pudo generar el guion: {exc}") from exc
    errors = validate_script(script, {s["id"] for s in sources}, args.duration)
    if errors:
        save_json(out / "script.json", script)
        raise SystemExit("Guion guardado, pero no pasa validación:\n- " + "\n- ".join(errors))
    save_json(out / "script.json", script)
    plain = "\n\n".join(f"[{scene['start']:g}-{scene['end']:g}s] {scene['narration']}\nVISUAL: {scene['visual']}\nTEXTO: {scene['caption']}" for scene in script["scenes"])
    (out / "script.txt").write_text(f"{script['title']}\n\nHOOK: {script['hook']}\n\n{plain}\n", encoding="utf-8")

    visual_prompt = f"""Sos director de arte de Archivo Imposible. Prepará un prompt de imagen y uno de animación por escena, en el mismo orden. No reescribas narraciones ni agregues hechos.
Estilo de marca: {account.get('visual_style', '')}
Motivo/personaje recurrente: {account.get('visual_motif', '')}

Reglas: imágenes verticales 9:16; no incluyas texto legible (los rótulos van en Clipchamp); usa un estilo y paleta consistentes; mantené como referencia el personaje guía; no inventes uniformes, edificios, objetos ni detalles históricos que no estén respaldados por las notas. Si no hay evidencia suficiente, elegí un mapa, documento, paisaje o una recreación atmosférica genérica identificada como recreación. Evitá gore. La animación será sutil y no debe cambiar los hechos visuales.

Respondé solo JSON con este formato: {{"scenes":[{{"scene_number":1,"image_prompt":"...","animation_prompt":"..."}}]}}.

Escenas del guion:
{json.dumps(script['scenes'], ensure_ascii=False, indent=2)}

Notas de research:
{research}"""
    print("Preparando prompts para Gemini (imágenes) y Qwen (animación)…")
    try:
        visual_plan = llm.generate_json(visual_prompt)
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(f"No se pudo generar el plan visual: {exc}") from exc
    visual_errors = validate_visuals(visual_plan, len(script["scenes"]))
    if visual_errors:
        save_json(out / "visuals.json", visual_plan)
        raise SystemExit("Plan visual guardado, pero no pasa validación:\n- " + "\n- ".join(visual_errors))
    visual_plan["style_guide"] = account.get("visual_style", "")
    visual_plan["character_reference"] = account.get("visual_motif", "")
    save_json(out / "visuals.json", visual_plan)
    (out / "production_kit.md").write_text(make_production_kit(script, visual_plan, args.topic), encoding="utf-8")

    save_json(out / "metadata.json", {"account": account["slug"], "topic": args.topic, "format": args.format,
                                       "model": args.model, "generated_at": datetime.now(timezone.utc).isoformat(),
                                       "status": "draft_requires_human_fact_check_and_manual_video_production",
                                       "tools": ["Ollama", "Gemini", "Qwen", "Clipchamp"]})
    print(f"Borrador listo: {out.resolve()}")
    return 0


def make_production_kit(script: dict, visual_plan: dict, topic: str) -> str:
    visuals = {v["scene_number"]: v for v in visual_plan["scenes"]}
    parts = [
        f"# Kit de producción — {script['title']}",
        f"\nTema: {topic}  \nDuración objetivo: {script['target_duration']} s  \nFormato: vertical 9:16",
        "\n## Pasos",
        "1. Revisá `research.md` y corregí datos y nombres propios antes de producir.",
        "2. En Gemini, generá la primera imagen/personaje de referencia. Reutilizala en las demás escenas para mantener consistencia.",
        "3. Generá una imagen vertical por escena con cada `image_prompt`; agregá los rótulos después en el editor.",
        "4. En Qwen, animá cada imagen con su `animation_prompt`; respetá el orden y los tiempos. Identificá las escenas sintéticas como recreaciones cuando corresponda.",
        "5. En Clipchamp, importá clips en orden, añadí narración (voz propia o TTS), música con licencia adecuada y subtítulos en español. Revisá nombres y puntuación a mano.",
        "6. Exportá en 1080 × 1920 y mirá el video completo antes de publicarlo.",
        "\n## Escenas (orden de Clipchamp)",
    ]
    for i, scene in enumerate(script["scenes"], 1):
        v = visuals[i]
        parts.extend([
            f"\n### Escena {i:02d} — {scene['start']:g}–{scene['end']:g} s",
            f"**Narración:** {scene['narration']}",
            f"**Texto en pantalla:** {scene['caption']}",
            f"**Imagen para Gemini:** {v['image_prompt']}",
            f"**Movimiento para Qwen:** {v['animation_prompt']}",
            f"**Fuentes:** {', '.join(scene['source_ids'])}",
        ])
    parts.extend([
        "\n## Nota",
        "Gemini, Qwen y Clipchamp se usan manualmente en este MVP. Sus funciones y límites gratuitos pueden cambiar según la cuenta y la región. Este kit prepara los insumos; no inicia sesión, sube archivos ni publica por vos.",
    ])
    return "\n".join(parts) + "\n"
