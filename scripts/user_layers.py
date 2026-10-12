"""独自 GeoJSON の検証と、既存地図に重ねる SVG の生成。

外部パッケージ・ネットワークを使わない。入力は出典・観測日・確認状態を持つ
Point / LineString に限定し、書き間違いを黙って無視しない。元の Feature は
変更せず返すので、作図後の GeoJSON にそのまま保存できる。
"""

import datetime
import html
import json
import math
import re
import unicodedata
from pathlib import Path

from design_system import load_design


MAPS = {"global", "middle-east"}
STATUS_LABELS = {"confirmed": "確認", "reported": "報道", "hypothetical": "仮定"}
# 入力で受け付ける値はデータ仕様。描画時の色・破線寸法とは分けて検証する。
KINDS = ("port", "route", "pipeline", "note")
LINE_STYLES = ("solid", "dashed", "dotted", "dashdot")


class LayerError(ValueError):
    """入力ファイル、Feature ID、該当フィールドを含む検証エラー。"""


def load_layer(path: Path, map_name: str) -> dict:
    """設定済みの追加レイヤーを読み込む。未作成の既定ファイルは空とする。

    利用者が明示したファイルの存在確認は呼び出し元でも行うこと。
    JSON の重複キー、NaN / Infinity、未知のキーも誤入力として拒否する。
    """
    path = Path(path)
    if map_name not in MAPS:
        raise LayerError(f"{path}: map: 未対応の地図 {map_name!r}")
    if not path.exists():
        return {"type": "FeatureCollection", "map": map_name, "updated_at": None, "features": []}

    def reject_constant(value):
        raise ValueError(f"非有限数 {value} は使用できません")

    def unique_keys(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"キー {key!r} が重複しています")
            result[key] = value
        return result

    try:
        layer = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant,
                           object_pairs_hook=unique_keys)
    except (OSError, UnicodeError, ValueError) as error:
        raise LayerError(f"{path}: JSON: {error}") from error

    context = str(path)

    def fail(field, message):
        raise LayerError(f"{context}: {field}: {message}")

    def obj(value, field, required, optional=()):
        if not isinstance(value, dict):
            fail(field, "オブジェクトにしてください")
        missing = set(required) - value.keys()
        unknown = value.keys() - set(required) - set(optional)
        if missing:
            fail(field, "必須キーがありません: " + ", ".join(sorted(missing)))
        if unknown:
            fail(field, "未知のキーです: " + ", ".join(sorted(unknown)))

    def string(value, field):
        if not isinstance(value, str) or not value.strip():
            fail(field, "空でない文字列にしてください")
        # SVG/XML に置けない制御文字・サロゲートを保存する前に排除する。
        if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0xFFFE, 0xFFFF) for c in value):
            fail(field, "改行・制御文字を含めないでください")

    def enum(value, field, choices):
        if not isinstance(value, str) or value not in choices:
            fail(field, " / ".join(choices) + " のいずれかにしてください")

    def number(value, field, low, high):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            fail(field, "有限の数値にしてください")
        if not low <= value <= high:
            fail(field, f"{low}〜{high} の範囲にしてください")

    def date(value, field):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            fail(field, "YYYY-MM-DD 形式の日付にしてください")
        try:
            datetime.date.fromisoformat(value)
        except ValueError:
            fail(field, "実在する日付にしてください")

    def pair(value, field, geo=False):
        if not isinstance(value, list) or len(value) != 2:
            fail(field, "2要素の配列にしてください")
        for i, item in enumerate(value):
            limit = (180 if i == 0 else 85) if geo else 5000
            number(item, f"{field}[{i}]", -limit, limit)

    obj(layer, "FeatureCollection", ("type", "map", "updated_at", "features"))
    enum(layer["type"], "type", ("FeatureCollection",))
    enum(layer["map"], "map", (map_name,))
    if not isinstance(layer["features"], list):
        fail("features", "配列にしてください")
    if layer["features"] or layer["updated_at"] is not None:
        date(layer["updated_at"], "updated_at")
    ids = set()
    for index, feature in enumerate(layer["features"]):
        context = f"{path}: features[{index}]"
        obj(feature, "Feature", ("type", "id", "geometry", "properties"))
        string(feature["id"], "id")
        context += f" (id={feature['id']!r})"
        if feature["id"] in ids:
            fail("id", "同じファイル内で重複しています")
        ids.add(feature["id"])
        enum(feature["type"], "type", ("Feature",))
        props = feature["properties"]
        obj(props, "properties", ("name", "kind", "source", "observed_on", "status"),
            ("note", "color", "line_style", "width", "arrows", "label", "callout"))
        for key in ("name", "source"):
            string(props[key], f"properties.{key}")
        if "note" in props:
            string(props["note"], "properties.note")
        date(props["observed_on"], "properties.observed_on")
        enum(props["kind"], "properties.kind", KINDS)
        enum(props["status"], "properties.status", tuple(STATUS_LABELS))
        if "color" in props and (not isinstance(props["color"], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", props["color"])):
            fail("properties.color", "#RRGGBB 形式にしてください")
        if "line_style" in props:
            enum(props["line_style"], "properties.line_style", LINE_STYLES)
        if "width" in props:
            number(props["width"], "properties.width", 1, 8)
        if "arrows" in props and not isinstance(props["arrows"], bool):
            fail("properties.arrows", "true / false にしてください")
        if "label" in props:
            label = props["label"]
            obj(label, "properties.label", (), ("offset", "font_size", "anchor"))
            if "offset" in label:
                pair(label["offset"], "properties.label.offset")
            if "font_size" in label:
                number(label["font_size"], "properties.label.font_size", 18, 30)
            if "anchor" in label:
                enum(label["anchor"], "properties.label.anchor", ("start", "end"))
        if "callout" in props:
            callout = props["callout"]
            obj(callout, "properties.callout", ("offset", "width", "title", "lines"))
            pair(callout["offset"], "properties.callout.offset")
            number(callout["width"], "properties.callout.width", 200, 800)
            string(callout["title"], "properties.callout.title")
            if not isinstance(callout["lines"], list) or not 1 <= len(callout["lines"]) <= 4:
                fail("properties.callout.lines", "1〜4行の文字列配列にしてください")
            for i, line in enumerate(callout["lines"]):
                string(line, f"properties.callout.lines[{i}]")
        geometry = feature["geometry"]
        obj(geometry, "geometry", ("type", "coordinates"))
        expected = "Point" if props["kind"] in ("port", "note") else "LineString"
        enum(geometry["type"], "geometry.type", (expected,))
        coords = geometry["coordinates"]
        if expected == "Point":
            pair(coords, "geometry.coordinates", geo=True)
        else:
            if not isinstance(coords, list) or len(coords) < 2:
                fail("geometry.coordinates", "2点以上の座標配列にしてください")
            for i, coord in enumerate(coords):
                pair(coord, f"geometry.coordinates[{i}]", geo=True)
                if i and coord[1] == coords[i - 1][1] and (coord[0] - coords[i - 1][0]) % 360 == 0:
                    fail(f"geometry.coordinates[{i}]", "同一点を連続して指定できません")
    return layer


def _path(points):
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def _curve(points):
    """短い区間で膨らみすぎない接線を使い、ベジェ曲線と接線用標本を返す。"""
    tangents = []
    for i, point in enumerate(points):
        previous, following = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        dx, dy = following[0] - previous[0], following[1] - previous[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:  # 往復経路の折り返し点は、入ってきた区間に接線を合わせる。
            dx, dy = point[0] - previous[0], point[1] - previous[1]
            length = math.hypot(dx, dy) or 1
        tangents.append((dx / length, dy / length))
    result, samples = f"M {points[0][0]:.2f},{points[0][1]:.2f}", [points[0]]
    for i, (a, b) in enumerate(zip(points, points[1:])):
        distance = math.dist(a, b)
        start_length = min(distance, math.dist(points[i - 1], a) if i else distance) * .29
        end_length = min(distance, math.dist(b, points[i + 2]) if i + 2 < len(points) else distance) * .29
        c = tuple(a[k] + tangents[i][k] * start_length for k in (0, 1))
        d = tuple(b[k] - tangents[i + 1][k] * end_length for k in (0, 1))
        result += f" C {c[0]:.2f},{c[1]:.2f} {d[0]:.2f},{d[1]:.2f} {b[0]:.2f},{b[1]:.2f}"
        steps = max(8, min(2000, math.ceil(distance / 2)))
        for j in range(1, steps + 1):
            t, u = j / steps, 1 - j / steps
            samples.append(tuple(u ** 3 * a[k] + 3 * u * u * t * c[k] + 3 * u * t * t * d[k] + t ** 3 * b[k] for k in (0, 1)))
    return result, samples


def _at_fraction(points, fraction):
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    target = sum(lengths) * fraction
    for a, b, length in zip(points, points[1:], lengths):
        if not length:
            continue
        if target <= length:
            part = target / length
            return (a[0] + part * (b[0] - a[0]), a[1] + part * (b[1] - a[1])), math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        target -= length
    return points[-1], 0


def _line_samples(points):
    """直線も細かく標本化し、両端が図外でも枠を横切る区間を見つける。"""
    result = [points[0]]
    for a, b in zip(points, points[1:]):
        steps = max(1, min(4000, math.ceil(math.dist(a, b) / 2)))
        for i in range(1, steps + 1):
            result.append(tuple(a[k] + (b[k] - a[k]) * i / steps for k in (0, 1)))
    return result


def _wrap_text(text, available, size):
    """CJK の字幅を概算して枠内で折り返す。実際の重なりは描画後の QA で確認。"""
    lines, row, used = [], "", 0
    for char in text:
        advance = size * (1 if unicodedata.east_asian_width(char) in "WF" else .58)
        if row and used + advance > available:
            lines.append(row)
            row, used = "", 0
        row += char
        used += advance
    return lines + ([row] if row else [])


def render_layer(layer, project, width, height, wrap=False, *, top=0):
    """検証済みレイヤーを SVG 断片へ変換する。

    project([lon, lat]) は既存地図と同じピクセル座標を返す関数。
    height は下端の y 座標、top は上端。全球図では TOP + MH / TOP を渡す。
    ラベル位置は地点（航路の場合は可視部中央）からの差分で指定する。
    """
    if not layer["features"]:
        return []  # 既定の空レイヤーでは既存 SVG を1バイトも変えない。
    # GeoJSONの明示値を優先し、省略された意匠だけを共通設定で補う。
    design = load_design(layer["map"])
    style, colors = design["user_layer"], design["colors"]
    clip_id = "user-layer-clip-" + layer["map"]
    result = [f'<defs><clipPath id="{clip_id}"><rect x="0" y="{top}" width="{width}" height="{height - top}"/></clipPath></defs>',
              f'<g class="user-data-layer" clip-path="url(#{clip_id})">']
    labels = []  # 地点名・注記は全追加航路より手前に描く。

    def text(x, y, value, size=style["label_size"], color=colors["primary"], anchor="start", halo=True):
        edge = (
            f' paint-order="stroke" stroke="{colors["ink"]}" '
            f'stroke-width="{style["label_halo"]}" stroke-linejoin="round"'
        ) if halo else ""
        return f'<text class="user-data-text" x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{style["label_weight"]}" text-anchor="{anchor}" fill="{color}"{edge}>{html.escape(value)}</text>'

    def leader(a, b, css):
        if math.dist(a, b) < 1:
            return []
        d = _path([a, b])
        return [f'<path d="{d}" fill="none" stroke="{colors["ink"]}" stroke-width="{style["leader_casing"]}"/>',
                f'<path class="{css}" d="{d}" fill="none" stroke="{colors["secondary"]}" stroke-width="{style["leader_width"]}"/>']

    def in_bounds(point):
        return 0 <= point[0] <= width and top <= point[1] <= height

    for feature in layer["features"]:
        props, geometry = feature["properties"], feature["geometry"]
        kind = props["kind"]
        color = props.get("color", style["palette"][kind])
        thickness = props.get("width", style["line_width"])

        def fail(field, message):
            raise LayerError(f"id={feature['id']!r}: {field}: {message}")

        if geometry["type"] == "Point":
            anchor = project(geometry["coordinates"])
            if not in_bounds(anchor):
                fail("geometry.coordinates", "地点が地図の描画範囲外です。対象地図と座標を確認してください")
            result.append(f'<circle class="user-data-point" cx="{anchor[0]:.2f}" cy="{anchor[1]:.2f}" r="{style["port_radius"]}" fill="{color}" stroke="{colors["ink"]}" stroke-width="{style["port_border"]}"/>')
        else:
            points = []
            for x, y in map(project, geometry["coordinates"]):
                if wrap and points:
                    while x - points[-1][0] > width / 2:
                        x -= width
                    while x - points[-1][0] < -width / 2:
                        x += width
                if not points or math.dist(points[-1], (x, y)) > 1e-9:
                    points.append((x, y))
            if len(points) < 2:
                fail("geometry.coordinates", "投影後の経路が同一点になります")
            d, samples = _curve(points) if kind == "route" else (_path(points), _line_samples(points))
            offsets = (-width, 0, width) if wrap else (0,)
            visible = []
            dash = style["dashes"][props.get("line_style", "solid")]
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            for offset in offsets:
                result.append(f'<path class="user-data-route" d="{d}" transform="translate({offset} 0)" fill="none" stroke="{color}" stroke-width="{thickness}"{dash_attr}/>')
                visible.extend((x + offset, y) for x, y in samples if in_bounds((x + offset, y)))
            if props.get("arrows", kind == "route"):
                (ax, ay), angle = _at_fraction(samples, .62)
                for offset in offsets:
                    if in_bounds((ax + offset, ay)):
                        result.append(f'<path class="user-data-arrow" d="M 0 0 L -13 -5 L -13 5 Z" fill="{color}" transform="translate({ax + offset:.2f} {ay:.2f}) rotate({angle:.2f})"/>')
            if not visible:
                fail("geometry.coordinates", "経路全体が地図の描画範囲外です。対象地図と座標を確認してください")
            anchor = visible[len(visible) // 2]
        status = STATUS_LABELS[props["status"]]
        if "label" in props or "callout" not in props:
            label = props.get("label", {})
            dx, dy = label.get("offset", (18, -18))
            tx, ty = anchor[0] + dx, anchor[1] + dy
            size, align = label.get("font_size", style["label_size"]), label.get("anchor", "start")
            end = (tx - 12 if align == "start" else tx + 12, ty - size * .42)
            distance = math.dist(anchor, end)
            if distance > 22:
                start = tuple(anchor[k] + (end[k] - anchor[k]) * 9 / distance for k in (0, 1))
                labels.extend(leader(start, end, "label-leader"))
            labels.append(text(tx, ty, f'{props["name"]}［{status}］', size, anchor=align))
        if "callout" in props:
            callout = props["callout"]
            x, y = (anchor[k] + callout["offset"][k] for k in (0, 1))
            box_width = callout["width"]
            available = box_width - 2 * style["callout_padding"]
            title_rows = _wrap_text(callout["title"], available, style["callout_title"])
            status_rows = _wrap_text(f'追加データ・{status}・{props["observed_on"]}', available, style["callout_status"])
            body_rows = [row for line in callout["lines"] for row in _wrap_text(line, available, style["callout_body"])]
            rows = ([(row, style["callout_title"], colors["primary"]) for row in title_rows]
                    + [(row, style["callout_status"], colors["muted"]) for row in status_rows]
                    + [(row, style["callout_body"], colors["secondary"]) for row in body_rows])
            box_height = style["callout_line_height"] * len(rows) + style["callout_bottom"]
            if x < 0 or y < top or x + box_width > width or y + box_height > height:
                fail("properties.callout.offset", "注記枠が地図の描画範囲をはみ出します。offset・width・本文を調整してください")
            nearest = (min(max(anchor[0], x), x + box_width), min(max(anchor[1], y), y + box_height))
            labels.extend(leader(anchor, nearest, "callout-leader"))
            labels.append(f'<rect class="callout-box" x="{x:.2f}" y="{y:.2f}" width="{box_width}" height="{box_height}" fill="{colors["panel"]}" fill-opacity="{style["callout_opacity"]}" stroke="{colors["panel_border"]}" stroke-width="{style["callout_border"]}"/>')
            for row_index, (row, size, row_color) in enumerate(rows):
                labels.append(text(x + style["callout_padding"], y + style["callout_first_y"] + style["callout_line_height"] * row_index, row, size, row_color, halo=False))
    return result + labels + ["</g>"]
