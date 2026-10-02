import unittest

from content_factory.validation import validate_script, validate_visuals


def sample_script():
    scenes = []
    for i in range(5):
        scenes.append({
            "start": i * 15,
            "end": (i + 1) * 15,
            "narration": " ".join(["Esta historia necesita contexto, evidencia y una explicación clara para quien la escucha."] * 3),
            "visual": "Mapa o recreación editorial identificada como tal, sin simular una fotografía histórica.",
            "caption": "CONTEXTO",
            "source_ids": ["S01"],
        })
    return {"title": "Un hecho documentado", "hook": "Esta historia ocurrió y hay fuentes para revisarla.",
            "target_duration": 75, "format": "esto-realmente-paso", "scenes": scenes,
            "source_ids": ["S01"], "editorial_notes": []}


class ValidationTests(unittest.TestCase):
    def test_accepts_contiguous_script_with_known_sources(self):
        self.assertEqual(validate_script(sample_script(), {"S01"}, 75), [])

    def test_rejects_unknown_source_reference(self):
        script = sample_script()
        script["scenes"][0]["source_ids"] = ["S99"]
        self.assertTrue(any("IDs de fuente" in error for error in validate_script(script, {"S01"}, 75)))

    def test_accepts_visual_prompts_in_scene_order(self):
        visuals = {"scenes": [
            {"scene_number": i, "image_prompt": "Mapa documental vertical con luz tenue.",
             "animation_prompt": "Acercamiento lento y leve movimiento de partículas."}
            for i in range(1, 6)
        ]}
        self.assertEqual(validate_visuals(visuals, 5), [])

    def test_rejects_duplicate_or_incomplete_visual_scenes(self):
        visuals = {"scenes": [
            {"scene_number": 1, "image_prompt": "Mapa documental vertical con luz tenue.",
             "animation_prompt": "Acercamiento lento y leve movimiento de partículas."},
            {"scene_number": 1, "image_prompt": "", "animation_prompt": "movimiento sutil"},
        ]}
        errors = validate_visuals(visuals, 2)
        self.assertTrue(any("sin repeticiones" in error for error in errors))
        self.assertTrue(any("image_prompt" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
