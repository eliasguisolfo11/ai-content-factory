import json
from pathlib import Path


def validate_script(script: dict, source_ids: set[str], duration: int) -> list[str]:
    errors: list[str] = []
    allowed_top = {"title", "hook", "target_duration", "format", "scenes", "source_ids", "editorial_notes"}
    extras = set(script) - allowed_top
    if extras:
        errors.append("Campos no permitidos en el guion: " + ", ".join(sorted(extras)))
    for key in ("title", "hook", "format", "scenes", "source_ids"):
        if key not in script:
            errors.append(f"Falta el campo requerido: {key}")
    scenes = script.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 5:
        errors.append("El guion debe tener al menos 5 escenas.")
        return errors
    if script.get("target_duration") != duration:
        errors.append("target_duration no coincide con la duración solicitada.")
    if not set(script.get("source_ids", [])) <= source_ids:
        errors.append("El guion cita IDs de fuente que no existen en el research.")
    expected_start = 0
    for i, scene in enumerate(scenes, 1):
        extras = set(scene) - {"start", "end", "narration", "visual", "caption", "source_ids"}
        if extras:
            errors.append(f"Escena {i}: campos no permitidos: " + ", ".join(sorted(extras)))
        for key in ("start", "end", "narration", "visual", "caption", "source_ids"):
            if key not in scene:
                errors.append(f"Escena {i}: falta {key}.")
        if not all(k in scene for k in ("start", "end", "narration", "source_ids")):
            continue
        if abs(float(scene["start"]) - expected_start) > 0.1:
            errors.append(f"Escena {i}: los tiempos no son contiguos (esperado {expected_start}s).")
        if float(scene["end"]) <= float(scene["start"]):
            errors.append(f"Escena {i}: end debe ser posterior a start.")
        expected_start = float(scene["end"])
        if not set(scene["source_ids"]) or not set(scene["source_ids"]) <= source_ids:
            errors.append(f"Escena {i}: debe citar IDs de fuente existentes.")
    if abs(expected_start - duration) > 1.0:
        errors.append(f"La suma de escenas da {expected_start:.1f}s y el objetivo es {duration}s.")

    total_words = sum(len(str(s.get("narration", "")).split()) for s in scenes)
    low, high = int(duration * 1.8), int(duration * 2.8)
    if not low <= total_words <= high:
        errors.append(f"La narración tiene {total_words} palabras; para {duration}s se esperaba aproximadamente {low}-{high}.")
    return errors


def validate_visuals(visuals: dict, scene_count: int) -> list[str]:
    scenes = visuals.get("scenes") if isinstance(visuals, dict) else None
    if not isinstance(scenes, list) or len(scenes) != scene_count:
        return [f"El plan visual debe tener exactamente {scene_count} escenas."]
    errors: list[str] = []
    expected = set(range(1, scene_count + 1))
    actual: list[int] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            errors.append("Cada escena visual debe ser un objeto JSON.")
            continue
        number = scene.get("scene_number")
        if not isinstance(number, int):
            errors.append("Cada escena visual debe tener scene_number entero.")
            continue
        actual.append(number)
        for key in ("image_prompt", "animation_prompt"):
            if not isinstance(scene.get(key), str) or len(scene[key].strip()) < 12:
                errors.append(f"Escena visual {number}: falta un {key} útil.")
    if set(actual) != expected or len(actual) != len(set(actual)):
        errors.append("scene_number debe enumerar sin repeticiones desde 1.")
    return errors


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
