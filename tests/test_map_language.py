"""Language selection must preserve geography, provenance, and custom input."""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from map_language import MapLanguage
from design_system import load_design
from user_layers import load_layer, render_layer

CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
NS = {"svg": "http://www.w3.org/2000/svg"}


class LanguageCatalogTests(unittest.TestCase):
    def test_default_language_is_identity_and_does_not_change_design(self):
        language = MapLanguage("global")
        design = load_design("global")
        self.assertEqual(language.text("日本", 10, 20, 30, "end"), ("日本", 10, 20, 30, "end"))
        self.assertEqual(language.design(design), design)

    def test_english_changes_text_and_type_without_mutating_design(self):
        design = load_design("global")
        original = copy.deepcopy(design)
        language = MapLanguage("global", "en")
        translated = language.design(design)
        self.assertEqual(language.tr("日本"), "Japan")
        self.assertEqual(translated["routes"], design["routes"])
        self.assertNotEqual(translated["fonts"], design["fonts"])
        self.assertEqual(design, original)
        with self.assertRaisesRegex(ValueError, "Missing en translation"):
            language.tr("未登録の日本語")
        with self.assertRaisesRegex(ValueError, "Unsupported language"):
            MapLanguage("global", "unknown")

    def test_user_words_and_source_fields_are_not_translated(self):
        layer = load_layer(ROOT / "examples/user-data/global.geojson", "global")
        original = copy.deepcopy(layer)
        fragment = "".join(render_layer(layer, lambda p: (((p[0] + 55) % 360) / 360 * 2400, 600 - p[1] * 3), 2400, 1200, lang="en"))
        self.assertIn("User data / hypothetical", fragment)
        self.assertIn("2026-10-12", fragment)
        self.assertIn(layer["features"][0]["properties"]["name"], fragment)
        self.assertEqual(layer, original)


class LanguageBuildTests(unittest.TestCase):
    def build(self, map_id, language, output):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/build.py"), map_id,
            "--svg-only", "--lang", language, "--output-dir", str(output)],
            cwd=output.parent, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        svg = ET.parse(output / f"{map_id}.svg").getroot()
        data = json.loads((output / f"{map_id}.geojson").read_text())
        return svg, data

    def test_all_three_english_maps_have_no_untranslated_builtin_text_and_keep_geometry(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for map_id in ("global", "middle-east", "gulf-hormuz-oman"):
                with self.subTest(map_id=map_id):
                    ja, japanese = self.build(map_id, "ja", directory / "ja")
                    en, english = self.build(map_id, "en", directory / "english-explicit")
                    self.assertEqual(en.get("lang"), "en")
                    self.assertEqual(english["language"], "en")
                    self.assertFalse((directory / "english-explicit/en").exists())
                    self.assertTrue(en.findall("svg:text", NS) or en.findall(".//svg:text", NS))
                    for element in en.findall(".//svg:text", NS):
                        self.assertFalse(CJK.search("".join(element.itertext())), element.text)
                    self.assertEqual([f["geometry"] for f in english["features"]],
                                     [f["geometry"] for f in japanese["features"]])
                    # Source notes remain exactly as stored, even when originally Japanese.
                    self.assertEqual([f["properties"] for f in english["features"]],
                                     [f["properties"] for f in japanese["features"]])
                    if map_id != "gulf-hormuz-oman":
                        self.assertEqual(english["as_of"], japanese["as_of"])
                    else:
                        self.assertEqual(english["metadata"], japanese["metadata"])


if __name__ == "__main__":
    unittest.main()
