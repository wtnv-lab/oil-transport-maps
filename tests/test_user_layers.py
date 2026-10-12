"""独自 GeoJSON の検証と、再生成時の振る舞いを確認する。

標準ライブラリだけで実行できる。ブラウザー、Node.js、ネット接続は不要。
実行例: python3 -m unittest discover -s tests -v
"""

import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
MODULE_SPEC = importlib.util.spec_from_file_location(
    "user_layers", ROOT / "scripts" / "user_layers.py"
)
USER_LAYERS = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(USER_LAYERS)
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def collection(*features, name="global"):
    return {
        "type": "FeatureCollection",
        "map": name,
        "updated_at": "2026-10-12" if features else None,
        "features": list(features),
    }


def point_feature(identifier="example-port"):
    return {
        "type": "Feature",
        "id": identifier,
        "geometry": {"type": "Point", "coordinates": [56.4, 25.2]},
        "properties": {
            "name": "試験用の追加港",
            "kind": "port",
            "source": 'https://example.invalid/reference?a=1&name=<試験>"',
            "observed_on": "2026-10-12",
            "status": "hypothetical",
            "note": "試験用データ。実際の港湾・航行情報ではない。",
        },
    }


def route_feature(coordinates, identifier="example-route"):
    feature = point_feature(identifier)
    feature["geometry"] = {"type": "LineString", "coordinates": coordinates}
    feature["properties"]["kind"] = "route"
    return feature


def global_project(point):
    """描画APIの契約確認用の単純な世界一周投影（経度10px/度）。"""
    longitude, latitude = point
    return ((longitude + 55) % 360 * 10, (90 - latitude) * 10)


def fragment_root(parts):
    return ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg">' + "".join(parts) + "</svg>"
    )


class TemporaryDataTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.data_dir = self.root / "data"
        self.data_dir.mkdir()
        for name in ("global", "middle-east"):
            self.write_layer(collection(name=name), name)

    def write_layer(self, data, name="global"):
        filename = self.data_dir / f"{name}.geojson"
        filename.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return filename

    def run_cli(self, *arguments, output=None, default_data=False):
        """Node が存在しない環境でも検証・SVG生成を完了できるか確認する。"""
        environment = os.environ.copy()
        environment["NODE"] = str(self.root / "node-does-not-exist")
        command = [
            sys.executable,
            str(ROOT / "scripts" / "build.py"),
            *arguments,
            "--output-dir",
            str(output or self.root / "output"),
        ]
        if not default_data:
            command.extend(["--data-dir", str(self.data_dir)])
        return subprocess.run(
            command,
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )


class CheckDataCommandTests(TemporaryDataTest):
    def test_empty_check_does_not_need_node_or_create_outputs(self):
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        result = self.run_cli("all", "--check-data")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "output").exists())
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)

    def test_all_preflight_failure_preserves_existing_outputs(self):
        invalid = collection()
        invalid["type"] = "NotAFeatureCollection"
        self.write_layer(invalid)
        output = self.root / "output"
        output.mkdir()
        originals = {
            "global.svg": b"existing global output",
            "middle-east.svg": b"existing regional output",
        }
        for name, content in originals.items():
            (output / name).write_bytes(content)
        result = self.run_cli("all", "--svg-only", output=output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("global.geojson", result.stderr)
        self.assertIn("type", result.stderr)
        self.assertEqual(
            {path.name: path.read_bytes() for path in output.iterdir()}, originals
        )

    def test_missing_file_names_the_required_file(self):
        (self.data_dir / "global.geojson").unlink()
        result = self.run_cli("global", "--check-data")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("global.geojson", result.stderr)
        self.assertFalse((self.root / "output").exists())

    def test_default_blank_files_check_without_outputs(self):
        result = self.run_cli("all", "--check-data", default_data=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "output").exists())
        for name in ("global", "middle-east"):
            layer = USER_LAYERS.load_layer(ROOT / "user-data" / f"{name}.geojson", name)
            self.assertEqual(layer["features"], [])

    def test_valid_custom_check_keeps_data_and_output_directory_untouched(self):
        filename = self.write_layer(collection(point_feature()))
        original = filename.read_bytes()
        result = self.run_cli("global", "--check-data")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(filename.read_bytes(), original)
        self.assertFalse((self.root / "output").exists())

    def test_cli_rejects_input_directory_as_output_without_overwriting_data(self):
        for name in ("global", "middle-east"):
            self.write_layer(collection(point_feature(), name=name), name)
        originals = {path.name: path.read_bytes() for path in self.data_dir.iterdir()}
        # 見た目の異なるパスでも、解決後に同じ場所なら入力を保護する。
        same_directory = self.data_dir / ".." / "data"
        for name in ("global", "middle-east", "all"):
            with self.subTest(map=name):
                result = self.run_cli(name, "--svg-only", output=same_directory)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("入力GeoJSON", result.stderr)
                self.assertEqual(
                    {path.name: path.read_bytes() for path in self.data_dir.iterdir()},
                    originals,
                )
                self.assertFalse((self.root / "output").exists())

    def test_direct_builders_reject_output_overwriting_the_input_file(self):
        for name in ("global", "middle-east"):
            self.write_layer(collection(point_feature(), name=name), name)
        originals = {path.name: path.read_bytes() for path in self.data_dir.iterdir()}
        for name in ("global", "middle-east"):
            with self.subTest(map=name):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(ROOT / "maps" / name / "build.py"),
                        "--data-file", str(Path("data") / f"{name}.geojson"),
                        "--output-dir", str(self.data_dir),
                    ],
                    cwd=self.root,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("入力GeoJSON", result.stderr)
                self.assertEqual(
                    {path.name: path.read_bytes() for path in self.data_dir.iterdir()},
                    originals,
                )
                self.assertFalse((self.root / "output").exists())


class InputValidationTests(TemporaryDataTest):
    def assert_rejected(self, data, field):
        filename = self.write_layer(data)
        with self.assertRaises(ValueError) as caught:
            USER_LAYERS.load_layer(filename, "global")
        self.assertIn("global.geojson", str(caught.exception))
        self.assertIn(field, str(caught.exception))
        return str(caught.exception)

    def test_out_of_range_or_non_numeric_coordinates_identify_the_field(self):
        for coordinate in ([181, 25], [-181, 25], [56, 86], [56, -86], [True, 25], [56, "25"]):
            with self.subTest(coordinate=coordinate):
                feature = point_feature()
                feature["geometry"]["coordinates"] = coordinate
                message = self.assert_rejected(collection(feature), "geometry.coordinates")
                self.assertIn("features[0]", message)
                self.assertIn(feature["id"], message)

    def test_coordinate_dimensions_are_not_silently_discarded(self):
        for coordinate in ([56], [56, 25, 0]):
            with self.subTest(coordinate=coordinate):
                feature = point_feature()
                feature["geometry"]["coordinates"] = coordinate
                self.assert_rejected(collection(feature), "geometry.coordinates")

    def test_non_finite_json_numbers_are_rejected_with_filename(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                feature = point_feature()
                feature["geometry"]["coordinates"][0] = value
                self.assert_rejected(collection(feature), "JSON")

    def test_boolean_is_not_a_stroke_width(self):
        feature = point_feature()
        feature["properties"]["width"] = True
        self.assert_rejected(collection(feature), "properties.width")

    def test_duplicate_feature_ids_are_rejected(self):
        feature = point_feature()
        duplicate = copy.deepcopy(feature)
        duplicate["geometry"]["coordinates"] = [58, 24]
        message = self.assert_rejected(collection(feature, duplicate), "id")
        self.assertIn("features[1]", message)
        self.assertIn(feature["id"], message)

    def test_geometry_and_kind_must_match(self):
        for kind in ("route", "pipeline"):
            with self.subTest(kind=kind):
                feature = point_feature()
                feature["properties"]["kind"] = kind
                self.assert_rejected(collection(feature), "geometry.type")
        feature = route_feature([[56, 25], [59, 22]])
        feature["properties"]["kind"] = "port"
        self.assert_rejected(collection(feature), "geometry.type")

    def test_invalid_or_non_iso_dates_are_rejected(self):
        for value in ("2026-02-30", "20261012", "2026-1-2", True):
            with self.subTest(value=value):
                feature = point_feature()
                feature["properties"]["observed_on"] = value
                self.assert_rejected(collection(feature), "properties.observed_on")
        data = collection(point_feature())
        data["updated_at"] = "2026-13-01"
        self.assert_rejected(data, "updated_at")

    def test_misspelled_fields_are_reported_instead_of_ignored(self):
        for container, key in (
            ("collection", "featurez"),
            ("properties", "colour"),
            ("geometry", "coordinate"),
        ):
            with self.subTest(container=container):
                feature = point_feature()
                data = collection(feature)
                target = data if container == "collection" else feature[container]
                target[key] = "typo"
                self.assert_rejected(data, key)

    def test_map_mismatch_identifies_map_field(self):
        self.assert_rejected(collection(name="middle-east"), "map")

    def test_color_cannot_inject_an_svg_attribute(self):
        feature = point_feature()
        feature["properties"]["color"] = '#ffffff" onload="alert(1)'
        self.assert_rejected(collection(feature), "properties.color")

    def test_duplicate_json_keys_are_rejected(self):
        filename = self.data_dir / "global.geojson"
        filename.write_text(
            '{"type":"FeatureCollection","map":"global","map":"global",'
            '"updated_at":null,"features":[]}', encoding="utf-8"
        )
        with self.assertRaises(ValueError) as caught:
            USER_LAYERS.load_layer(filename, "global")
        self.assertIn("global.geojson", str(caught.exception))
        self.assertIn("map", str(caught.exception))

    def test_degenerate_routes_are_rejected_including_antimeridian_alias(self):
        for coordinates in ([[56, 25], [56, 25]], [[180, 20], [-180, 20]]):
            with self.subTest(coordinates=coordinates):
                self.assert_rejected(
                    collection(route_feature(coordinates)), "geometry.coordinates"
                )

    def test_source_and_observation_metadata_survive_validation_and_rendering(self):
        data = collection(point_feature())
        original = copy.deepcopy(data)
        loaded = USER_LAYERS.load_layer(self.write_layer(data), "global")
        self.assertEqual(loaded, original)
        USER_LAYERS.render_layer(loaded, global_project, 3600, 1800, wrap=True)
        self.assertEqual(loaded, original)


class LayerRenderingTests(TemporaryDataTest):
    def render(self, feature):
        layer = USER_LAYERS.load_layer(self.write_layer(collection(feature)), "global")
        parts = USER_LAYERS.render_layer(layer, global_project, 3600, 1800, wrap=True)
        return fragment_root(parts), "".join(parts)

    def test_empty_layer_contributes_no_svg_bytes(self):
        layer = USER_LAYERS.load_layer(self.data_dir / "global.geojson", "global")
        self.assertEqual(USER_LAYERS.render_layer(layer, global_project, 3600, 1800), [])

    def test_text_is_escaped_without_changing_its_visible_content(self):
        feature = point_feature()
        feature["properties"]["name"] = '<港 & "試験">'
        feature["properties"]["label"] = {"offset": [20, -20]}
        feature["properties"]["callout"] = {
            "offset": [100, 100], "width": 500,
            "title": '<見出し & "引用">',
            "lines": ['A</text><script>alert(1)</script>&B'],
        }
        root, raw = self.render(feature)
        visible = "".join(root.itertext())
        self.assertIn(feature["properties"]["name"], visible)
        self.assertIn(feature["properties"]["callout"]["title"], visible)
        self.assertIn(feature["properties"]["callout"]["lines"][0], visible)
        self.assertIn("&lt;", raw)
        self.assertIn("&amp;", raw)
        self.assertFalse(
            any(element.tag.rsplit("}", 1)[-1] == "script" for element in root.iter())
        )
        self.assertFalse(any("onload" in element.attrib for element in root.iter()))

    def test_callout_is_a_rectangle_with_a_straight_arrowless_leader(self):
        feature = point_feature()
        feature["properties"]["callout"] = {
            "offset": [100, 100], "width": 420,
            "title": "追加情報", "lines": ["テスト用の注記"],
        }
        root, _ = self.render(feature)
        boxes = root.findall('.//svg:rect[@class="callout-box"]', SVG_NS)
        self.assertEqual(len(boxes), 1)
        self.assertNotIn("rx", boxes[0].attrib)
        self.assertNotIn("ry", boxes[0].attrib)
        leaders = root.findall('.//svg:path[@class="callout-leader"]', SVG_NS)
        self.assertEqual(len(leaders), 1)
        self.assertEqual(re.findall(r"[A-Za-z]", leaders[0].get("d")), ["M", "L"])
        self.assertNotIn("marker-start", leaders[0].attrib)
        self.assertNotIn("marker-end", leaders[0].attrib)

    def test_world_edge_route_crosses_the_seam_without_spanning_the_world(self):
        feature = route_feature([[-56, 20], [-54, 20]])
        feature["properties"]["callout"] = {
            "offset": [-400, 60], "width": 300,
            "title": "世界端", "lines": ["境界をまたぐ模式航路"],
        }
        root, _ = self.render(feature)
        paths = root.findall('.//svg:path[@class="user-data-route"]', SVG_NS)
        self.assertTrue(paths)
        extents = []
        for path in paths:
            values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", path.get("d"))]
            xs = values[::2]
            self.assertLess(max(xs) - min(xs), 40)
            offset = float(re.search(r"translate\((-?[\d.]+)", path.get("transform")).group(1))
            extents.append((min(xs) + offset, max(xs) + offset))
        self.assertTrue(any(left <= 0 < right for left, right in extents), extents)
        self.assertTrue(any(left < 3600 <= right for left, right in extents), extents)

    def test_callout_outside_the_canvas_is_reported_not_silently_clipped(self):
        feature = point_feature()
        feature["properties"]["callout"] = {
            "offset": [4000, 100], "width": 420,
            "title": "図外になる注記", "lines": ["テスト用"],
        }
        with self.assertRaises(ValueError) as caught:
            self.render(feature)
        self.assertIn(feature["id"], str(caught.exception))
        self.assertIn("callout", str(caught.exception))

    def test_invisible_feature_is_reported_instead_of_disappearing(self):
        feature = point_feature()
        layer = USER_LAYERS.load_layer(self.write_layer(collection(feature)), "global")
        with self.assertRaises(ValueError) as caught:
            USER_LAYERS.render_layer(layer, lambda point: (-100, -100), 1000, 600)
        self.assertIn(feature["id"], str(caught.exception))
        self.assertIn("geometry", str(caught.exception))


class DataEditIntegrationTests(TemporaryDataTest):
    def generate(self):
        result = self.run_cli("global", "--svg-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / "output"
        return {
            name: (output / name).read_bytes()
            for name in ("global.svg", "global.geojson")
        }

    def test_add_edit_and_delete_are_reflected_by_each_rebuild(self):
        baseline = self.generate()
        feature = point_feature("editable-feature")
        feature["properties"]["name"] = "追加テスト港A"
        self.write_layer(collection(feature))
        added = self.generate()
        self.assertIn("追加テスト港A", added["global.svg"].decode())
        exported = json.loads(added["global.geojson"])
        saved = [item for item in exported["features"] if item.get("id") == feature["id"]]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["properties"]["source"], feature["properties"]["source"])
        self.assertEqual(saved[0]["properties"]["observed_on"], "2026-10-12")
        self.assertEqual(saved[0]["properties"]["status"], "hypothetical")
        feature["properties"]["name"] = "更新テスト港B"
        feature["geometry"]["coordinates"] = [58.5, 23.6]
        self.write_layer(collection(feature))
        edited = self.generate()
        self.assertIn("更新テスト港B", edited["global.svg"].decode())
        self.assertNotIn("追加テスト港A", edited["global.svg"].decode())
        exported = json.loads(edited["global.geojson"])
        saved = next(item for item in exported["features"] if item.get("id") == feature["id"])
        self.assertEqual(saved["geometry"]["coordinates"], [58.5, 23.6])
        self.write_layer(collection())
        deleted = self.generate()
        self.assertEqual(deleted, baseline)

    def test_bundled_examples_build_both_maps_with_preserved_sources(self):
        initial = self.run_cli("all", "--svg-only")
        self.assertEqual(initial.returncode, 0, initial.stderr)
        output = self.root / "output"
        base_heights = {
            name: float(ET.parse(output / f"{name}.svg").getroot().get("height"))
            for name in ("global", "middle-east")
        }
        originals = {}
        for name in ("global", "middle-east"):
            example = ROOT / "examples" / "user-data" / f"{name}.geojson"
            self.assertTrue(example.is_file(), f"同梱例がありません: {example.name}")
            layer = USER_LAYERS.load_layer(example, name)
            self.assertTrue(layer["features"])
            originals[name] = layer
            self.write_layer(layer, name)
        result = self.run_cli("all", "--svg-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, layer in originals.items():
            with self.subTest(map=name):
                root = ET.parse(output / f"{name}.svg").getroot()
                self.assertEqual(float(root.get("height")), base_heights[name] + 36)
                self.assertIsNotNone(root.find('.//svg:g[@class="user-data-layer"]', SVG_NS))
                exported = json.loads((output / f"{name}.geojson").read_text(encoding="utf-8"))
                for feature in layer["features"]:
                    matches = [
                        item for item in exported["features"]
                        if item.get("id") == feature["id"]
                    ]
                    self.assertEqual(matches, [feature])
                self.assertIn("user_data", exported)
                self.assertEqual(exported["user_data"]["updated_at"], layer["updated_at"])


if __name__ == "__main__":
    unittest.main()
