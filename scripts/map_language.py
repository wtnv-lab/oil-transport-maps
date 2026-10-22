"""Map text and language-specific layout, kept separate from route geometry.

Japanese remains the default. English catalogues translate built-in labels only;
user-supplied source text and GeoJSON provenance are never rewritten.
"""
import copy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("ja", "en")
CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")


class MapLanguage:
    def __init__(self, map_id, language="ja", root=ROOT):
        if language not in LANGUAGES:
            raise ValueError(f"Unsupported language: {language!r}")
        self.language = language
        self.map_id = map_id
        self.catalog = {}
        if language != "ja":
            path = Path(root) / "maps" / map_id / "locales" / f"{language}.json"
            self.catalog = json.loads(path.read_text(encoding="utf-8"))

    def tr(self, value):
        value = str(value)
        if self.language == "ja":
            return value
        translated = self.catalog.get("translations", {}).get(value)
        if translated is not None:
            return translated
        if CJK.search(value):
            raise ValueError(f"Missing {self.language} translation in {self.map_id}: {value}")
        return value

    def text(self, value, x, y, size, anchor="start"):
        """Return translated text and its optional language-specific placement."""
        layout = self.catalog.get("layout", {}).get(str(value), {})
        return (self.tr(value), layout.get("x", x), layout.get("y", y),
                layout.get("size", size), layout.get("anchor", anchor))

    def design(self, design):
        """Override fonts and type sizes without changing geometry or route colors."""
        if self.language == "ja":
            return design
        result = copy.deepcopy(design)
        result["fonts"].update(self.catalog.get("fonts", {}))
        for role, values in self.catalog.get("typography", {}).items():
            result["typography"][role].update(values)
        return result
