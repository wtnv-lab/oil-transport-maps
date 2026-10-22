"""共通設定を変更したときの伝播と、表示を壊す設定の拒否を確認する。"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from design_system import contrast_ratio, load_design


class DesignSystemTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "design", self.root / "design")

    def update(self, relative, change):
        path = self.root / "design" / relative
        data = json.loads(path.read_text())
        change(data)
        path.write_text(json.dumps(data))

    def test_shared_loading_color_reaches_both_maps_and_added_data(self):
        self.update("foundations.json", lambda d: d["colors"].update(loading="#fedcba"))
        region = load_design("middle-east", self.root)
        world = load_design("global", self.root)
        self.assertEqual(region["routes"]["loading"], "#fedcba")
        self.assertEqual(world["routes"]["S"], "#fedcba")
        self.assertEqual(world["user_layer"]["palette"]["note"], "#fedcba")

    def test_profile_override_keeps_other_common_values_and_does_not_leak(self):
        self.update("profiles/global.json", lambda d: d.setdefault("colors", {}).update(primary="#ffffff"))
        world = load_design("global", self.root)
        region = load_design("middle-east", self.root)
        self.assertEqual(world["colors"]["primary"], "#ffffff")
        self.assertNotEqual(region["colors"]["primary"], "#ffffff")
        world["colors"]["ink"] = "#ffffff"
        self.assertNotEqual(load_design("global", self.root)["colors"]["ink"], "#ffffff")

    def test_unknown_reference_fails_instead_of_drawing_invalid_color(self):
        self.update("profiles/global.json", lambda d: d["routes"].update(S="{colors.missing}"))
        with self.assertRaisesRegex(ValueError, "未定義の色参照"):
            load_design("global", self.root)

    def test_collapsed_callout_spacing_is_rejected(self):
        self.update("profiles/global.json", lambda d: d["callout"].update(line_height=10))
        with self.assertRaisesRegex(ValueError, "行送り"):
            load_design("global", self.root)

    def test_contrast_reference_endpoints(self):
        self.assertAlmostEqual(contrast_ratio("#000000", "#ffffff"), 21)
        self.assertAlmostEqual(contrast_ratio("#445566", "#445566"), 1)


if __name__ == "__main__":
    unittest.main()
