"""ペルシャ湾・ホルムズ海峡の拡大図を保存済み背景とGeoJSONから生成する。

位置・形状: data/zoom-routes.geojson、投影: data/base-projection.json。
表題・日付・注記: metadata.json、意匠: 共通の中東図デザイン設定。
SVG・GeoJSONを出力し、矢印・PNG・配置検査は専用render.cjsで処理する。
海路は模式表現。再生成だけでは情勢や個船の実績は更新されない。
"""
import argparse
import base64
import json
import math
import sys
from html import escape
from pathlib import Path


D = Path(__file__).resolve().parent
ROOT = D.parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from design_system import load_design, svg_css


DS = load_design("middle-east")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
args = parser.parse_args()
OUT = args.output_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
if OUT == D or OUT == D / "data":
    parser.error("出力先を入力フォルダーと別にしてください。")

STEM = OUT / "gulf-hormuz-oman"
META = json.loads((D / "metadata.json").read_text())
C, L, S, SP = DS["colors"], DS["lines"], DS["symbols"], DS["spacing"]
R = DS["routes"]
T = DS["typography"]
W, H, TOP, BOT = 1800, 810, 84, SP["compact_footer_height"]
meta = json.loads((D / "data/base-projection.json").read_text())
(west, south), (east, north) = meta["bounds"]
features = json.loads((D / "data/zoom-routes.geojson").read_text())["features"]
SPM = next(
    f["geometry"]["coordinates"]
    for f in features
    if f["properties"]["category"] == "crude_sbm"
)
svg = []
a = svg.append
M = lambda p: math.log(math.tan(math.pi / 4 + math.radians(p) / 2))


def xy(p):
    return (
        (p[0] - west) / (east - west) * W,
        TOP + (M(north) - M(p[1])) / (M(north) - M(south)) * H,
    )


def text(x, y, value, role="label", color=None, anchor="start", css=""):
    spec = T[role]
    a(
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{spec["size"]}" '
        f'font-weight="{spec["weight"]}" fill="{color or C["primary"]}" '
        f'text-anchor="{anchor}" class="{css}">{escape(value)}</text>'
    )


def stroke(d, color, width, dash=None, cls="", arrows=None):
    # Purple branches intentionally join. A casing would cut a dark notch in the trunk.
    if color != R["gulf"]:
        a(
            f'<path d="{d}" fill="none" stroke="{C["route_casing"]}" '
            f'stroke-width="{width + L["route_casing_extra"]}" '
            f'opacity="{L["route_casing_opacity"]}"/>'
        )
    extra = f' data-arrow-size="{arrows}"' if arrows is not None else ""
    a(
        f'<path d="{d}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" class="{cls}"{extra}'
        + (f' stroke-dasharray="{dash}"' if dash else "")
        + "/>"
    )


def smooth(
    coords,
    color,
    width,
    kind="pair",
    dash=None,
    arrow_size=None,
    start_bearing=None,
    end_bearing=None,
):
    ps = list(map(xy, coords))
    d = f"M {ps[0][0]:.2f},{ps[0][1]:.2f}"
    for i, (p, q) in enumerate(zip(ps, ps[1:])):
        prev = ps[max(0, i - 1)]
        nxt = ps[min(len(ps) - 1, i + 2)]

        def unit(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            n = math.hypot(dx, dy)
            return dx / n, dy / n

        u = unit(prev, q)
        v = unit(p, nxt)
        length = math.dist(p, q)

        # Shared endpoint tangents keep adjoining route features visually smooth.
        def bearing_vector(deg):
            rad = math.radians(deg)
            return math.sin(rad), -math.cos(rad)

        if i == 0 and start_bearing is not None:
            u = bearing_vector(start_bearing)
        if i == len(ps) - 2 and end_bearing is not None:
            v = bearing_vector(end_bearing)
        ca = 0.25 * min(length, math.dist(prev, p) or length)
        cb = 0.25 * min(length, math.dist(q, nxt) or length)
        c1 = (p[0] + u[0] * ca, p[1] + u[1] * ca)
        c2 = (q[0] - v[0] * cb, q[1] - v[1] * cb)
        d += (
            f" C {c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} "
            f"{q[0]:.2f},{q[1]:.2f}"
        )
    stroke(
        d, color, width, dash,
        "route " + kind if kind else "",
        arrow_size or L["marine_arrow"],
    )


def leader(p, q, color=None, marker_gap=None):
    length = math.dist(p, q)
    gap = SP["leader_marker_gap"] if marker_gap is None else marker_gap
    p = (
        p[0] + (q[0] - p[0]) * gap / length,
        p[1] + (q[1] - p[1]) * gap / length,
    )
    d = f"M {p[0]:.2f},{p[1]:.2f} L {q[0]:.2f},{q[1]:.2f}"
    a(
        f'<path d="{d}" stroke="{C["leader_casing"]}" '
        f'stroke-width="{L["leader_casing_width"]}" '
        f'opacity="{L["leader_casing_opacity"]}"/>'
    )
    a(
        f'<path d="{d}" class="label-leader" '
        f'stroke="{color or C["leader"]}" stroke-width="{L["leader_width"]}"/>'
    )


def point(p, label, at, role="port", anchor="start", kind="port", sub=None):
    x, y = xy(p)
    tx, ty = at
    leader(
        (x, y),
        (
            tx - SP["label_gap"] if anchor == "start" else tx + SP["label_gap"],
            ty - T[role]["size"] * SP["label_center_factor"],
        ),
    )
    if kind == "plant":
        s = S["facility_size"] / 2
        a(
            f'<path d="M {x},{y-s} L {x+s},{y} L {x},{y+s} L {x-s},{y} Z" '
            f'fill="{C["facility_symbol"]}" stroke="{C["symbol_stroke"]}" '
            f'stroke-width="{S["stroke_width"]}"/>'
        )
    elif kind == "loading":
        a(
            f'<circle cx="{x}" cy="{y}" r="{S["loading_radius"]}" '
            f'fill="{C["ink"]}" stroke="{R["loading"]}" '
            f'stroke-width="{S["loading_width"]}"/>'
        )
    else:
        a(
            f'<circle cx="{x}" cy="{y}" r="{S["port_radius"]}" '
            f'fill="{C["strong"]}" stroke="{C["symbol_stroke"]}" '
            f'stroke-width="{S["stroke_width"]}"/>'
        )
    text(
        tx, ty, label, role,
        C["facility"] if kind == "plant" else C["strong"],
        anchor,
        "port-label halo" if kind != "plant" else "",
    )
    if sub:
        text(
            tx, ty + SP["detail_line_height"], sub, "detail",
            R["loading"] if kind == "loading" else C["detail"], anchor,
        )


a(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{TOP+H+BOT}" '
    f'viewBox="0 0 {W} {TOP+H+BOT}" role="img" aria-labelledby="title desc">'
)
a(
    f'<title id="title">{escape(META["title"])}</title><desc id="desc">'
    'ホルムズ海峡を経由する海路とアブダビ原油パイプライン、'
    'フジャイラ・ソハール・ミナ・アル・ハファル沖の積出区域。'
    '航路は模式表現で当日の通航や施設稼働を示さない。</desc>'
)
a(
    f'<defs><style>{svg_css(DS)}</style><clipPath id="mapclip">'
    f'<rect x="0" y="{TOP}" width="{W}" height="{H}"/></clipPath></defs>'
)
a(f'<rect width="{W}" height="{TOP+H+BOT}" fill="{C["frame"]}"/>')
text(48, 40, META["title"], "title")
text(48, 69, META["subtitle"], "footnote", C["subtitle"])
text(
    W - 48, 40,
    META["as_of"].replace("-", ".")
    + " 基準 ／ "
    + META["route_additions_as_of"][5:].replace("-", ".")
    + " 航路追記",
    "footnote", C["date"], "end",
)
text(W - 48, 69, META["status_label"], "status", C["date"], "end")
a('<g clip-path="url(#mapclip)">')
b64 = base64.b64encode((D / "assets/osm-dark-base.png").read_bytes()).decode()
a(f'<image x="0" y="{TOP}" width="{W}" height="{H}" href="data:image/png;base64,{b64}"/>')
for f in features:
    p = f["properties"]
    name = p["name"]
    cat = p["category"]
    coords = f["geometry"]["coordinates"]
    a(f'<g data-category="{escape(cat)}" data-name="{escape(name)}">')
    if cat == "crude_pipeline" and "ADCOP" in name:
        stroke(
            "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in map(xy, coords)),
            R["pipeline"], L["pipeline_width"],
            cls="route single", arrows=L["pipeline_arrow"],
        )
    elif cat in ("schematic_gulf_shipping", "schematic_das_shuttle"):
        smooth(
            coords, R["gulf"], L["marine_width"],
            arrow_size=L["gulf_arrow"], end_bearing=p.get("display_end_bearing"),
        )
    elif cat in ("schematic_sts_connection", "schematic_fujairah_mina_sts"):
        smooth(
            coords, R["gulf"], L["sts_width"], dash=L["sts_dash"],
            arrow_size=L["sts_arrow"], start_bearing=p.get("display_start_bearing"),
        )
    elif cat == "schematic_export_connection":
        smooth(coords, R["marine"], L["marine_width"], kind=None)
    elif cat == "schematic_subsea_loading":
        stroke(
            "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in map(xy, coords)),
            R["pipeline"], L["pipeline_width"],
        )
    elif cat == "schematic_sbm_shipping":
        smooth(coords, R["marine"], L["marine_width"])
    elif cat == "schematic_shipping" and any(
        k in name for k in ["フジャイラ ↔", "ソハール ↔", "ミナ・アル"]
    ):
        # Outbound lines summarize port/offshore loadings; no mandatory STS implied.
        smooth(coords, R["marine"], L["marine_width"])
    a("</g>")

for p in [[56.64, 25.22], [57.0, 24.51], [58.8, 23.75]]:
    x, y = xy(p)
    a(
        f'<circle cx="{x}" cy="{y}" r="{S["sts_radius"]}" '
        f'fill="{C["ink"]}" stroke="{R["gulf"]}" stroke-width="{S["sts_width"]}"/>'
    )

# Horizontal geographic names use the original serif family without outlines.
for x, y, label, role, col in [
    (1510, 135, "イラン", "country", C["geography"]),
    (230, 570, "サウジアラビア", "country", C["geography"]),
    (810, 835, "アラブ首長国連邦", "country", C["geography"]),
    (1050, 843, "オマーン", "country", C["geography"]),
    (360, 335, "ペルシャ湾", "sea", R["water"]),
    (1688, 506, "オマーン湾", "sea", R["water"]),
]:
    text(x, y, label, role, col, "middle", "geographic-label")

point([50.163, 26.645], "ラス・タヌラ", (130, 230))
point([52.88, 25.15], "ダス島（UAE）", (475, 490), anchor="end")
point([53.6176, 23.8279], "ハブシャン", (735, 765), role="plant", kind="plant")
point(SPM, "フジャイラ", (1340, 385), kind="loading", sub="UAE／原油SBM")
point([56.63, 24.511667], "ソハール", (1370, 565), role="secondary_port")
point(
    [58.533333, 23.65], "ミナ・アル・ハファル沖", (1470, 824),
    role="secondary_port", kind="loading", anchor="end", sub="原油SBM",
)
h = xy([56.45, 26.57])
a(
    f'<circle cx="{h[0]}" cy="{h[1]}" r="{S["passage_radius"]}" '
    f'fill="none" stroke="{R["water"]}" stroke-width="{S["passage_width"]}" '
    f'opacity="{S["passage_opacity"]}"/>'
)
leader(h, (1340, 205), R["water"], S["passage_radius"] + 3)
text(1350, 215, "ホルムズ海峡", "chokepoint", R["water"], css="passage-label halo")
leader(xy([54.82, 24.28]), (910, 540), R["pipeline"])
text(
    900, 550, "アブダビ原油パイプライン", "pipeline", R["pipeline"], "end",
    css="pipeline-label halo",
)
text(610, 250, "シャトル輸送", "gulf_route", R["gulf"], css="halo")
text(1245, 490, "STS", "detail", R["gulf"])
text(1306, 622, "STS", "detail", R["gulf"])
leader(xy([57.8, 23.95]), (1350, 724), R["gulf"], 4)
text(1280, 730, "フジャイラ発", "detail", R["gulf"], "middle")
text(1280, 758, "ミナ沖でSTS", "detail", R["gulf"], "middle")
text(1752, 460, "日本方面と往復", "route", R["marine"], "end", css="halo")

# North arrow and a local Web-Mercator scale, evaluated at 26.5 degrees north.
nx, ny = W - 60, TOP + 48
text(nx, ny, "N", "north", C["north"], "middle")
a(
    f'<path d="M {nx},{ny+15} L {nx-7},{ny+42} L {nx},{ny+37} '
    f'L {nx+7},{ny+42} Z" fill="{C["north"]}"/>'
)
km = 200
scale = km / (111.32 * math.cos(math.radians(26.5))) / (east - west) * W
sx, sy = 64, TOP + H - 33
text(sx, sy - 10, "0", "scale", C["scale_label"])
text(sx + scale, sy - 10, "200 km", "scale", C["scale_label"], "end")
a(
    f'<path d="M {sx},{sy} h {scale/2}" stroke="{C["scale_light"]}" '
    f'stroke-width="{S["scale_height"]}"/>'
    f'<path d="M {sx+scale/2},{sy} h {scale/2}" stroke="{C["scale_dark"]}" '
    f'stroke-width="{S["scale_height"]}"/>'
)
a("</g>")
a(
    f'<path d="M0 {TOP+H} H{W}" stroke="{C["footer_rule"]}" '
    f'stroke-width="{L["footer_rule_width"]}"/>'
)
notes = META["notes"]
for i, note in enumerate(notes):
    text(
        48, TOP + H + 20 + i * SP["compact_footer_line_height"],
        note, "compact_footnote", C["secondary"],
    )
text(
    48, TOP + H + BOT - 13,
    "© OpenStreetMap contributors · OpenFreeMap / © OpenMapTiles",
    "credit", C["credit"],
)
text(W - 48, TOP + H + BOT - 13, META["credit"], "credit", C["credit"], "end")
a("</svg>")

STEM.with_suffix(".svg").write_text("\n".join(svg))
STEM.with_suffix(".design.json").write_text(json.dumps(DS, ensure_ascii=False, indent=2))
print(STEM.with_suffix(".svg"))
STEM.with_suffix(".geojson").write_text(
    json.dumps(
        {"type": "FeatureCollection", "metadata": META, "features": features},
        ensure_ascii=False, indent=2,
    )
    + "\n"
)
