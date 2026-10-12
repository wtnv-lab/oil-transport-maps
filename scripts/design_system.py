"""両図と見本帳が参照するデザイン設定。Python標準ライブラリのみを使う。

共通値は design/foundations.json、縮尺ごとの値は design/profiles/ に置く。
このモジュールは意匠だけを扱い、座標・出典・情報基準日は変更しない。
"""

import copy
import json
import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAP_IDS = ("middle-east", "global")


def _merge(base, overrides):
    """辞書だけを再帰マージする。配列は置換し、読み込み元は書き換えない。"""
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _validate(design):
    for name, color in {**design["colors"], **design["routes"], **design["user_layer"]["palette"]}.items():
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError(f"色は #RRGGBB で指定してください: {name}={color!r}")
    for role in ("sans", "geographic"):
        fonts = design["fonts"][role]
        if not isinstance(fonts, list) or not fonts or not all(
            isinstance(font, str) and font and not re.search(r'[<>;{}\\"]', font)
            for font in fonts
        ):
            raise ValueError(f"書体リストが不正です: {role}")
    for role, spec in design["typography"].items():
        size, weight = spec["size"], spec["weight"]
        if not isinstance(size, (int, float)) or not math.isfinite(size) or size <= 0:
            raise ValueError(f"文字サイズは正の数です: {role}")
        if weight not in range(100, 901, 100):
            raise ValueError(f"文字の太さは100〜900の100刻みです: {role}")
    if any(not isinstance(n, (int, float)) or not math.isfinite(n) or n < 0 for n in design["halo"].values()):
        raise ValueError("縁取り幅は0以上の数です")
    callout = design["callout"]
    if callout["line_height"] <= design["typography"].get("callout_body", {"size": 0})["size"]:
        raise ValueError("バルーンの行送りは本文サイズより大きくしてください")
    if not 0 < callout["title_y"] < callout["body_y"] < callout["base_height"]:
        raise ValueError("バルーンの見出し・本文・下余白の順序を確認してください")
    if not 0 < callout["padding_x"] < callout["title_x"]:
        raise ValueError("バルーンの左余白と見出し位置を確認してください")
    if not 1 <= design["preview"]["raster_scale"] <= 4:
        raise ValueError("PNGの倍率は1〜4にしてください")


def _resolve_colors(value, colors):
    if isinstance(value, dict):
        return {key: _resolve_colors(child, colors) for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_colors(child, colors) for child in value]
    if isinstance(value, str):
        match = re.fullmatch(r"\{colors\.([a-z_]+)\}", value)
        if match:
            reference = match.group(1)
            if reference not in colors:
                raise ValueError(f"未定義の色参照: {value}")
            return colors[reference]
    return value


def load_design(map_id, root=ROOT):
    """共通設定に地図別設定を重ね、独立した辞書を返す。未知の地図は拒否。"""
    if map_id not in MAP_IDS:
        raise ValueError(f"未知の地図: {map_id!r}")
    directory = Path(root) / "design"
    foundations = json.loads((directory / "foundations.json").read_text())
    profile = json.loads((directory / "profiles" / f"{map_id}.json").read_text())
    design = _merge(foundations, profile)
    # 同じ積載色等を二重管理しない。参照は colors の1階層に限定する。
    design = _resolve_colors(design, design["colors"])
    _validate(design)
    return design


def font_stack(families):
    """日本語の書体名を引用し、CSSの汎用ファミリーは引用しない。"""
    generic = {"serif", "sans-serif", "monospace", "system-ui"}
    return ",".join(font if font in generic else json.dumps(font, ensure_ascii=False) for font in families)


def svg_css(design):
    """既存クラスを維持しつつ、両図の書体・縁取りを同じ規則で生成する。"""
    halo = design["halo"]
    ink = design["colors"]["ink"]
    return "\n".join([
        f'text{{font-family:{font_stack(design["fonts"]["sans"])}}}',
        f'.halo{{paint-order:stroke;stroke:{ink};stroke-width:{halo["default"]};stroke-linejoin:round}}',
        f'.place-label.halo,.port-label.halo{{stroke-width:{halo["port"]}}}',
        f'.passage-label.halo,.pipeline-label.halo{{stroke-width:{halo["passage"]}}}',
        '.area-label,.geographic-label{'
        f'font-family:{font_stack(design["fonts"]["geographic"])};'
        f'letter-spacing:{design["geographic_letter_spacing_em"]}em;stroke:none' + '}',
        'path{stroke-linecap:round;stroke-linejoin:round}',
    ])


def contrast_ratio(foreground, background):
    """不透明sRGBの相対輝度比。写真・背景地図との実画素比較ではない。"""
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * w for c, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    first, second = sorted((luminance(foreground), luminance(background)))
    return (second + 0.05) / (first + 0.05)
