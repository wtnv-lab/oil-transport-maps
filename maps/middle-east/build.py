"""公開資料と保存済みの背景地図から、中東の原油輸送ルートを作図する。

入力はこのファイルと同じディレクトリの metadata.json、data/、assets/。
経路と施設の地理座標は GeoJSON と同じ [経度, 緯度] の順序で扱う。
背景地図に合わせた SVG と、描いた経路・代表点の GeoJSON を出力する。
海上経路は模式線であり、個船の実航跡や当日の運航状況を示すものではない。
Python の標準ライブラリのみを使用し、PNG への変換は別の工程で行う。
"""

import argparse
import base64
import datetime
import html
import json
import math
import sys
from pathlib import Path


# 入出力と作図基準日。日付・タイトルは metadata.json に集約する。
D = Path(__file__).resolve().parent
# 両図で共通の独自データ検査・描画処理。実行時の作業フォルダーに依存しない。
sys.path.insert(0, str(D.parents[1] / "scripts"))
from user_layers import load_layer, render_layer
from design_system import load_design, svg_css

# 共通の色・書体と、地域図の縮尺に合わせた寸法を分離する。
DS = load_design("middle-east")
COLORS, LINES, SYMBOLS = DS["colors"], DS["lines"], DS["symbols"]
SPACING = DS["spacing"]

parser = argparse.ArgumentParser(
    description="Generate the map SVG and representative route geometry"
)
parser.add_argument("--output-dir", type=Path, default=D.parents[1] / "dist")
parser.add_argument("--data-file", type=Path, default=D.parents[1] / "user-data/middle-east.geojson")
args = parser.parse_args()
if not args.data_file.is_file():
    parser.error(f"独自データがありません: {args.data_file}")
try:
    USER_LAYER = load_layer(args.data_file, "middle-east")
except (ValueError, OSError) as error:
    parser.error(str(error))
OUT = args.output_dir.resolve()
if (OUT / "middle-east.geojson").resolve() == args.data_file.resolve():
    parser.error("入力GeoJSONと出力先を別の場所にしてください。")
OUT.mkdir(parents=True, exist_ok=True)
META = json.loads((D / "metadata.json").read_text())
AS_OF = datetime.date.fromisoformat(META["as_of"])
ADDED = datetime.date.fromisoformat(META["route_additions_as_of"])

# W/H は地図本体、TOP/BOT は上下の見出し・注記のための余白。
W, H, TOP, BOT = 1800, 1080, 84, 140
if USER_LAYER["features"]:
    BOT += SPACING["user_data_footer_height"]  # 元図の基準日と区別した追加データの更新表示。
m = json.loads((D / "data/base-projection.json").read_text())
(west, south), (east, north) = m["bounds"]


# 背景画像は Web Mercator。経度は線形、緯度はメルカトル式で投影する。
def M(a):
    return math.log(math.tan(math.pi / 4 + math.radians(a) / 2))


def xy(p):
    """[経度, 緯度] を地図左上原点の SVG 座標へ変換する。"""
    return (
        (p[0] - west) / (east - west) * W,
        (M(north) - M(p[1])) / (M(north) - M(south)) * H,
    )


def path(coords):
    """地理座標列から SVG の折れ線パスを作る。"""
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in map(xy, coords))


def screenpath(coords):
    """配置済みの画面座標列から、再投影せずにパスを作る。"""
    return "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in coords)


# SVG 要素は追加順に重なる。背景、経路、施設、凡例の順で描画する。
svg = []

# ラベルは役割で階層化する。発着港・幹線を先に読み、設備と荷役説明を
# その下位に読む設計。国・海域は広がりを示す大きさと控えめな太さを使う。
# 国・海域には縁なしの明朝、港・経路には細縁の角ゴシックを使い分ける。
TYPE = {role: spec["size"] for role, spec in DS["typography"].items()}
WEIGHT = {role: spec["weight"] for role, spec in DS["typography"].items()}
AREA_SIZE_OFFSETS = DS["geographic_size_offsets"]


def add(s):
    svg.append(s)


def txt(
    x,
    y,
    t,
    size=TYPE["label"],
    color=COLORS["primary"],
    weight=WEIGHT["label"],
    anchor="start",
    halo=True,
    extra="",
    css="",
):
    classes = " ".join(name for name in ("halo" if halo else "", css) if name)
    add(
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}" text-anchor="{anchor}" '
        f'class="{classes}" {extra}>{html.escape(t)}</text>'
    )


def geo(lon, lat, t, **kw):
    txt(*xy([lon, lat]), t, **kw)


def line(
    coords,
    color,
    width=LINES["default_width"],
    dash=None,
    opacity=1,
    screen=False,
    under=True,
    css="",
):
    d = screenpath(coords) if screen else path(coords)
    if under:
        add(
            f'<path d="{d}" fill="none" stroke="{COLORS["route_casing"]}" '
            f'stroke-width="{width + LINES["route_casing_extra"]}" opacity="{LINES["route_casing_opacity"]}"/>'
        )
    add(
        f'<path class="{css}" d="{d}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" opacity="{opacity}"'
        + (f' stroke-dasharray="{dash}"' if dash else "")
        + "/>"
    )


def arrow(coords, color, at=0.7, size=LINES["pipeline_arrow"], screen=False):
    """投影後の線長に対する割合 at の位置に進行方向の矢印を置く。"""
    ps = coords if screen else list(map(xy, coords))
    lengths = [math.dist(a, b) for a, b in zip(ps, ps[1:])]
    target = sum(lengths) * at
    for a, b, segment_length in zip(ps, ps[1:], lengths):
        if target <= segment_length:
            t = target / segment_length
            x = a[0] + t * (b[0] - a[0])
            y = a[1] + t * (b[1] - a[1])
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            break
        target -= segment_length
    add(
        f'<path d="M 0 0 L {-size * SYMBOLS["arrow_length_factor"]} {-size * SYMBOLS["arrow_half_width_factor"]} '
        f'L {-size * SYMBOLS["arrow_notch_factor"]} 0 L {-size * SYMBOLS["arrow_length_factor"]} {size * SYMBOLS["arrow_half_width_factor"]} Z" '
        f'fill="{color}" transform="translate({x:.2f} {y:.2f}) '
        f'rotate({ang:.2f})"/>'
    )


def roundtrip_arrows(coords, color, at=0.5, size=LINES["marine_arrow"], screen=False):
    """1本の海上線に、接線方向が反対の矢頭を隣り合わせで置く。

    船の往復を示す模式表現。原油の流れや、同一船・同一路線での復航実績を
    表すものではない。短い積替え接続は矢頭と間隔を縮め、端点を隠さない。
    """
    points = coords if screen else list(map(xy, coords))
    length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
    if length <= 0:
        return
    size = min(size, length / 9)
    gap = min(LINES["paired_arrow_gap"], length * 0.2)
    margin = gap + size * 1.8
    center = min(max(length * at, margin), length - margin)
    before, after = (center - gap) / length, (center + gap) / length
    add('<g class="sea-roundtrip-arrows">')
    arrow(points[::-1], color, 1 - before, size, screen=True)
    arrow(points, color, after, size, screen=True)
    add('</g>')


def label_leader(coords, color=COLORS["leader"]):
    """細い暗色の縁で地形・航路から分離した、地名専用の直線。"""
    d = screenpath(coords)
    add(
        f'<path d="{d}" fill="none" stroke="{COLORS["leader_casing"]}" '
        f'stroke-width="{LINES["leader_casing_width"]}" opacity="{LINES["leader_casing_opacity"]}"/>'
    )
    add(
        f'<path class="label-leader" d="{d}" fill="none" stroke="{color}" '
        f'stroke-width="{LINES["leader_width"]}"/>'
    )


def point(p, label, lx, ly, sub=None, kind="port", anchor="start", *, leader_end=None, role=None):
    """施設代表点と地名を結ぶ。文字・マーカー双方に線の余白を取る。"""
    x, y = xy(p)
    font = TYPE[role or kind]
    weight = WEIGHT[role or kind]
    color = COLORS["facility"] if kind == "plant" else COLORS["strong"]
    # 地名を施設の右に置くなら start、左なら end にそろえる。
    # 行の反対側へ線を回さず、近い文字端から10px外側・文字高さの中央へ。
    destx = lx - SPACING["label_gap"] if anchor == "start" else lx + SPACING["label_gap"]
    desty = ly - font * SPACING["label_center_factor"]
    # 真下に置く地名などは、文字の上辺へ結ぶ終点を画面座標で指定できる。
    if leader_end is not None:
        destx, desty = leader_end
    distance = math.dist((x, y), (destx, desty))
    if distance > SPACING["leader_min_length"]:
        # 線をマーカーの縁から出し、文字の手前で止める。
        start = (
            x + (destx - x) * SPACING["leader_marker_gap"] / distance,
            y + (desty - y) * SPACING["leader_marker_gap"] / distance,
        )
        label_leader([start, (destx, desty)])
    if kind == "plant":
        add(
            f'<rect x="{x - SYMBOLS["facility_size"] / 2}" y="{y - SYMBOLS["facility_size"] / 2}" '
            f'width="{SYMBOLS["facility_size"]}" height="{SYMBOLS["facility_size"]}" '
            f'rx="{SYMBOLS["facility_corner"]}" transform="rotate(45 {x} {y})" fill="{COLORS["facility_symbol"]}" '
            f'stroke="{COLORS["symbol_stroke"]}" stroke-width="{SYMBOLS["stroke_width"]}"/>'
        )
    else:
        add(
            f'<circle cx="{x}" cy="{y}" r="{SYMBOLS["port_radius"]}" fill="{COLORS["strong"]}" '
            f'stroke="{COLORS["symbol_stroke"]}" stroke-width="{SYMBOLS["stroke_width"]}"/>'
        )
    # 地形と重なる主要港は細い縁で分離。内陸設備は縁なしで一段控えめに。
    txt(lx, ly, label, font, color, weight, anchor,
        halo=kind != "plant", css="port-label" if kind != "plant" else "facility-label")
    if sub:
        txt(lx, ly + SPACING["detail_line_height"], sub, TYPE["detail"], COLORS["detail"], WEIGHT["detail"], anchor, halo=False)


def chokepoint(p, label, dx, dy):
    x, y = xy(p)
    add(
        f'<circle cx="{x}" cy="{y}" r="{SYMBOLS["passage_radius"]}" stroke="{C}" '
        f'stroke-width="{SYMBOLS["passage_width"]}" fill="none" opacity="{SYMBOLS["passage_opacity"]}"/>'
    )
    direction = -1 if dx < 0 else 1
    # 引き出し線は文字の手前で止め、字形と重ならない間隔を取る。
    label_leader(
        [
            (x + direction * SPACING["passage_leader_start"], y - SPACING["passage_leader_start"]),
            (x + dx - direction * SPACING["passage_leader_gap"],
             y + dy - TYPE["chokepoint"] * SPACING["label_center_factor"]),
        ],
        C,
    )
    txt(
        x + dx,
        y + dy,
        label,
        TYPE["chokepoint"],
        C,
        weight=WEIGHT["chokepoint"],
        anchor="end" if dx < 0 else "start",
        css="passage-label",
    )


# 色分け：パイプライン、海上経路、水域、湾内〜湾外の海路、積載区域。
G = DS["routes"]["pipeline"]
R = DS["routes"]["marine"]
C = DS["routes"]["water"]
SH = DS["routes"]["gulf"]
LOAD = DS["routes"]["loading"]

# 文書枠と背景地図。画像は埋め込み、SVG 単体で表示できるようにする。
add(
    '<svg xmlns="http://www.w3.org/2000/svg" '
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    f'width="{W}" height="{H + TOP + BOT}" '
    f'viewBox="0 0 {W} {H + TOP + BOT}" role="img" aria-labelledby="title desc">'
)
add(
    '<title id="title">中東の原油輸送ルート</title><desc id="desc">'
    '公開資料による原油輸送経路の概念図。ヤンブー南航はサウジ関連船への航行制約を示す赤破線で、全船の完全封鎖ではない。'
    '湾内発はホルムズを通過し、直航と湾外積替えの両方がある。'
    'シディ・ケリルでは陸上タンクから沖合のSBMを経て原油を積載する。'
    '海路・積替地点は模式的な代表位置で、当日の稼働・輸送量・個別貨物の日本向け実績を示さない。'
    '双方向矢印は船の往復を模式化し、日本からの原油輸出や同一航路の往復実績を意味しない。LNGなどは対象外。</desc>'
)
add(
    f'<defs><style>{svg_css(DS)}</style>'
    '<clipPath id="mapclip"><rect width="1800" height="1080"/></clipPath></defs>'
)
add(f'<rect width="{W}" height="{H + TOP + BOT}" fill="{COLORS["frame"]}"/>')
txt(SPACING["frame_inset"], 41, META["title"], TYPE["title"], weight=WEIGHT["title"], halo=False)
txt(
    SPACING["frame_inset"],
    70,
    "公開資料による主要経路の整理 ｜ 当日の運航・稼働・輸送量を示す図ではありません",
    TYPE["status"],
    COLORS["subtitle"],
    WEIGHT["status"],
    halo=False,
)
txt(
    W - SPACING["frame_inset"],
    42,
    f"{AS_OF:%Y.%m.%d} 基準 ／ {ADDED:%m.%d} 航路追記",
    TYPE["status"],
    COLORS["date"],
    WEIGHT["status"],
    "end",
    False,
)
add(f'<g transform="translate(0 {TOP})" clip-path="url(#mapclip)">')
b64 = base64.b64encode((D / "assets/osm-dark-base.png").read_bytes()).decode()
add(f'<image width="1800" height="1080" href="data:image/png;base64,{b64}"/>')

# 地名・水域名は背景画像とは別の編集可能な文字として重ねる。
# 水域名は水平。表示面積ごとの字級差はプロファイルの差分値として管理し、
# country / sea の基準サイズを変更すると、同じ階層の全ラベルへ反映する。
for lon, lat, t in [
    (29.3, 25.7, "エジプト"),
    (44.5, 21.8, "サウジアラビア"),
    (44.2, 31, "イラク"),
    (55.4, 30, "イラン"),
    (57.7, 19.6, "オマーン"),
    (47, 16, "イエメン"),
    (29.9, 20.0, "スーダン"),
    (37.2, 15.8, "エリトリア"),
    (42.7, 11.8, "ジブチ"),
    (53.45, 22.70, "アラブ首長国連邦"),
]:
    geo(
        lon, lat, t, size=TYPE["country"] + AREA_SIZE_OFFSETS.get(t, 0),
        color=COLORS["geography"], weight=WEIGHT["country"], anchor="middle",
        halo=False, css="area-label",
    )
for lon, lat, t in [
    (33.8, 32.1, "地中海"),
    (38.1, 20.3, "紅海"),
    (53.3, 25.1, "ペルシャ湾"),
    (61.1, 24.9, "オマーン湾"),
    (59, 17.8, "アラビア海"),
    (47.65, 13.8, "アデン湾"),
]:
    x, y = xy([lon, lat])
    txt(
        x,
        y,
        t,
        TYPE["sea"] + AREA_SIZE_OFFSETS.get(t, 0),
        C,
        WEIGHT["sea"],
        "middle",
        halo=False,
        extra=f'transform="rotate(0 {x} {y})"',
        css="area-label",
    )

# GeoJSON には投影前の地理座標を保存し、出典・精度の説明を添える。
features = []


def feat(name, coords, kind, source, note):
    sea_route = kind in {
        "schematic_shipping", "restricted_schematic_shipping",
        "schematic_gulf_shipping", "schematic_sts_connection",
    }
    features.append(
        {
            "type": "Feature",
            "properties": {
                "name": name,
                "category": kind,
                "source": source,
                "accuracy": note,
                **({
                    "direction": "bidirectional",
                    "display_note": "船の往復を模式化。日本からの原油輸出、積荷、同一航路での往復実績、安全を示さない。",
                } if sea_route else {}),
            },
            "geometry": {"type": "LineString", "coordinates": coords},
        }
    )


# パイプライン：Petroline は保存済み OSM 線形、ADCOP は GEM の公開線形。
# 地理座標の出典と精度の注記は、各経路と一緒に GeoJSON へ書き出す。
crude = json.loads((D / "data/petroline-osm.geojson").read_text())["features"][0][
    "geometry"
]["coordinates"]
line(crude, G, LINES["pipeline_width"])
arrow(crude, G, 0.51, LINES["pipeline_arrow"])
arrow(crude, G, 0.83, LINES["pipeline_arrow"])
feat(
    "東西原油パイプライン（Petroline）",
    crude,
    "crude_pipeline",
    "https://www.openstreetmap.org/way/54729631 ; https://www.openstreetmap.org/way/1044430260",
    "公開OSM線形。測量精度を保証しない。港湾支線を含まない。",
)
txt(841, 401, "東西原油パイプライン", TYPE["pipeline"], G, WEIGHT["pipeline"], "middle", css="pipeline-label")
txt(841, 370, "9/28 輸出再開報道", TYPE["detail"], COLORS["pipeline_status"], WEIGHT["detail"], "middle", halo=False)

gem = json.loads((D / "data/gem_selected_pipelines.geojson").read_text())["features"]
adc = next(f for f in gem if "Bab-Habshan" in f["properties"]["project"])
ac = adc["geometry"]["coordinates"][0] + adc["geometry"]["coordinates"][2][1:]
line(ac, G, LINES["pipeline_width"])
arrow(ac, G, 0.61, LINES["pipeline_arrow"])
feat(
    "ハブシャン—フジャイラ原油パイプライン（ADCOP）",
    ac,
    "crude_pipeline",
    "Global Energy Monitor, public map dataset 2024-06-12",
    "公開資料に基づく概略線形。",
)
txt(1234, 574, "アブダビ原油パイプライン", TYPE["pipeline"], G, WEIGHT["pipeline"], css="pipeline-label")
line(
    [xy([54.82, 24.28]), (1415, 541), (1402, 548)],
    G,
    LINES["detail_leader_width"],
    screen=True,
    under=False,
    opacity=0.8,
)

# SUMED は確認済み線形と未収録区間の補間を読み込み、補間だけを破線にする。
sumedfile = D / "data/sumed_onshore_with_gap.geojson"
sf = json.loads(sumedfile.read_text())["features"]
sd = []
for f in sf:
    c = f["geometry"]["coordinates"]
    sd += c
    line(c, G, LINES["sumed_width"], LINES["interpolated_dash"] if f["properties"]["is_interpolated"] else None)
    feat(
        "SUMEDパイプライン"
        + ("（未収録区間の補間）" if f["properties"]["is_interpolated"] else ""),
        c,
        "crude_pipeline",
        f["properties"]["source"],
        f["properties"]["accuracy"],
    )
arrow(sd, G, 0.7, LINES["pipeline_arrow"])
txt(75, 250, "SUMEDパイプライン", TYPE["pipeline"], G, WEIGHT["pipeline"], css="pipeline-label")
line([xy([31.23, 29.72]), (283, 215), (283, 225)], G, LINES["detail_leader_width"], screen=True, under=False)

# 海上経路：海域内の代表点を結ぶ模式線で、観測された AIS 航跡ではない。
# 双方向矢印は船の往復を模式化する。パイプラインの送油方向とは区別する。
yanbu = [38.235, 23.935]
northsea = [
    yanbu,
    [37.85, 24.05],
    [37.05, 25.1],
    [36.3, 25.9],
    [35.4, 26.7],
    [34.7, 27.35],
    [34.05, 27.85],
    [33.7, 28.15],
    [33.33, 28.7],
    [32.79, 29.25],
    [32.43, 29.55],
    [32.338333, 29.598333],
]
line(northsea, R, LINES["marine_width"])
roundtrip_arrows(northsea, R, 0.36, LINES["marine_arrow"])
roundtrip_arrows(northsea, R, 0.78, LINES["marine_arrow"])
feat(
    "ヤンブー ↔ アイン・スフナ（海上・往復模式）",
    northsea,
    "schematic_shipping",
    "作図用の海域内代表点",
    "概略航路。実航跡・現在の運航を示さない。",
)

# スエズ運河の保存済み線形を北向きにそろえ、南北の海路へ接続する。
# ファイルがない場合だけ、明示的な代表点列にフォールバックする。
canalfile = D / "data/suez-canal-main.geojson"
if canalfile.exists():
    cc = json.loads(canalfile.read_text())["features"][0]["geometry"]["coordinates"]
    if cc[0][1] > cc[-1][1]:
        cc = cc[::-1]
else:
    cc = [
        [32.572, 29.932],
        [32.566, 30.10],
        [32.508, 30.24],
        [32.39, 30.44],
        [32.326, 30.574],
        [32.346, 30.735],
        [32.31, 31.0],
        [32.31, 31.27],
    ]
suez = (
    [[32.43, 29.64]]
    + cc
    + [
        [32.34, 31.48],
        [31.8, 31.60],
        [30.85, 31.58],
        [30.0, 31.48],
        [29.30, 31.40],
    ]
)
line(suez, R, LINES["canal_width"])
roundtrip_arrows(suez, R, 0.67, LINES["canal_arrow"])
feat(
    "スエズ運河 ↔ 地中海（海上・往復模式）",
    suez,
    "schematic_shipping",
    "Suez Canal Authority; OSM; SUMED; cartographic route",
    "運河北上後に地中海西航へ合流する概念線。全船のシディ・ケリル寄港を示さない。SUMED利用・再積載との組合せは船型・喫水等で異なる。",
)

# 喜望峰回りは地中海西航の区間だけを描く。ジブラルタル・喜望峰は図外。
cape = [
    [29.6824996, 31.0510105],
    [29.60, 31.20],
    [29.30, 31.40],
    [28.70, 31.55],
    [27.80, 31.68],
    [26.60, 31.85],
    [25.22, 31.99],
]
line(cape, R, LINES["marine_width"])
roundtrip_arrows(cape, R, 0.70, LINES["marine_arrow"])
txt(45, 165, "喜望峰経由 ↔ 日本方面", TYPE["route_edge"], R, WEIGHT["route_edge"], halo=False)
feat(
    "シディ・ケリル ↔ 地中海・ジブラルタル・喜望峰 ↔ 日本方面（表示範囲内のみ）",
    cape,
    "schematic_shipping",
    "ユーザー指定の迂回ルート。The National 2026-09-12",
    "地中海西航の一部のみ描画。ジブラルタル・喜望峰は図外。実航跡ではない。",
)

# ヤンブーからの南航は航行制約を示す破線とし、意味を注記にも残す。
southsea = [
    yanbu,
    [37.98, 23.7],
    [38.1, 22.5],
    [38.75, 20.8],
    [39.6, 18.9],
    [40.5, 17.15],
    [41.5, 15.5],
    [42.4, 14.0],
    [43.08, 12.75],
    [43.25, 12.55],
    [43.7, 12.23],
    [44.3, 12.03],
    [45.4, 12.10],
    [47.3, 12.6],
    [49.6, 13.0],
    [52.4, 13.65],
]
line(southsea, R, LINES["marine_width"], LINES["restricted_dash"])
roundtrip_arrows(southsea, R, 0.20, LINES["marine_arrow"])
roundtrip_arrows(southsea, R, 0.48, LINES["marine_arrow"])
roundtrip_arrows(southsea, R, 0.91, LINES["marine_arrow"])
feat(
    "ヤンブー ↔ バブ・エル・マンデブ ↔ 日本方面（往復模式・航行制約の破線）",
    southsea,
    "restricted_schematic_shipping",
    "ユーザー指定の破線。EIA September 2026 STEO; The National 2026-09-12",
    "サウジ関連船への航行制約を示す。全船の一律完全封鎖とは断定しない。実航跡ではない。",
)

# フジャイラ・ソハールと日本方面を結ぶ船の往復の、図内の区間。
fuj = [
    [56.358639, 25.187944],
    [56.60, 25.22],
    [57.18, 25.10],
    [58.2, 24.87],
    [59.4, 24.20],
    [60.55, 23.53],
    [61.7, 23.20],
    [63.15, 23.12],
]
soh = [
    [56.63, 24.511667],
    [57.0, 24.51],
    [57.55, 24.46],
    [58.2, 24.1],
    [59.4, 23.5],
    [60.6, 22.91],
    [61.7, 22.66],
    [63.15, 22.63],
]
for name, route in [("フジャイラ ↔ 日本方面", fuj), ("ソハール ↔ 日本方面", soh)]:
    line(route, R, LINES["marine_width"])
    roundtrip_arrows(route, R, 0.89, LINES["marine_arrow"])
    feat(
        name,
        route,
        "schematic_shipping",
        "作図用の海域内代表点",
        "日本方面を示す模式的な線。運航実績は未検証。",
    )

# ミナ・アル・ハファル沖は区域の代表点。STS と SBM は別の積載方式。
# この縮尺では共通マーカーを用い、個別ブイの正確な位置を表さない。
fahal = [58.533333, 23.65]
fahal_out = [
    fahal,
    [59.05, 23.70],
    [59.6, 23.35],
    [60.4, 22.85],
    [61.5, 22.3],
    [63.15, 22.1],
]
line(fahal_out, R, LINES["marine_width"])
roundtrip_arrows(fahal_out, R, 0.85, LINES["marine_arrow"])
feat(
    "ミナ・アル・ハファル沖 STS／原油SBM積載区域 ↔ 日本方面",
    fahal_out,
    "schematic_shipping",
    "docs/route-additions-20261012.md",
    "原油積載区域を代表点で表示。STSとSBMは別の積載方式。個別ブイ位置・接続船・日本向け貨物は未確定。",
)
fx, fy = xy(fahal)
add(
    f'<circle cx="{fx}" cy="{fy}" r="{SYMBOLS["loading_radius"]}" fill="{COLORS["frame"]}" '
    f'stroke="{LOAD}" stroke-width="{SYMBOLS["loading_width"]}"/>'
)
label_leader([(fx + 5, fy + 10), (1592, 578)], LOAD)
txt(1752, 610, "ミナ・アル・ハファル沖", TYPE["secondary_port"], weight=WEIGHT["secondary_port"], anchor="end", css="port-label")
txt(1752, 638, "STS／原油SBM（模式）", TYPE["detail"], LOAD, WEIGHT["detail"], "end", halo=False)
features.append(
    {
        "type": "Feature",
        "properties": {
            "name": "ミナ・アル・ハファル沖（STS／原油SBM）",
            "category": "loading_area",
            "source": "docs/route-additions-20261012.md",
            "accuracy": "NGA水路誌の港域代表点。個別SBMやSTS船の正確な位置ではない。",
        },
        "geometry": {"type": "Point", "coordinates": fahal},
    }
)

# 湾内発は直航と湾外 STS に共通する区間を描き、積替え接続だけを点線にする。
# ラス・タヌラの輸出とソハールの STS に関する資料を参照した模式線。
gulf = [
    [50.33, 26.80],
    [50.75, 27.00],
    [51.5, 27.05],
    [52.5, 26.9],
    [53.6, 26.6],
    [54.6, 26.55],
    [55.5, 26.55],
    [56.1, 26.60],
    [56.45, 26.58],
    [56.70, 26.43],
    [56.77, 26.10],
    [56.75, 25.78],
    [56.90, 25.48],
    [57.18, 25.10],
]
line(gulf, SH, LINES["marine_width"])
roundtrip_arrows(gulf, SH, 0.28, LINES["gulf_arrow"])
roundtrip_arrows(gulf, SH, 0.70, LINES["gulf_arrow"])
gulf_source = (
    "https://energynow.com/2026/09/"
    "gulf-of-oman-ship-to-ship-oil-transfers-reach-limit-as-saudi-exports-surge/"
)
feat(
    "ラス・タヌラ付近 ↔ ホルムズ海峡 ↔ 湾外（直航・積替えの共通区間）",
    gulf,
    "schematic_gulf_shipping",
    gulf_source,
    "湾内発の直航と湾外STSの併存を模式化。個船の実航跡・日本仕向け実績を示さない。",
)
for name, branch in [
    ("フジャイラ沖", [[56.75, 25.78], [56.70, 25.47], [56.64, 25.22]]),
    (
        "ソハール沖",
        [[56.90, 25.48], [56.96, 25.10], [57.02, 24.78], [57.0, 24.51]],
    ),
]:
    line(branch, SH, LINES["sts_width"], LINES["sts_dash"])
    roundtrip_arrows(branch, SH, 0.60, LINES["sts_arrow"])
    sx, sy = xy(branch[-1])
    add(
        f'<circle cx="{sx}" cy="{sy}" r="{SYMBOLS["sts_radius"]}" fill="{COLORS["ink"]}" '
        f'stroke="{SH}" stroke-width="{SYMBOLS["sts_width"]}"/>'
    )
    feat(
        "湾内航路 ↔ " + name + "の積替え接続（往復模式）",
        branch,
        "schematic_sts_connection",
        gulf_source,
        "沖合積替えの代表位置。全便の寄港・積替え、特定のラス・タヌラ発シャトル便を示すものではない。",
    )
txt(1200, 308, "湾内 ↔ 湾外", TYPE["gulf_route"], SH, WEIGHT["gulf_route"])
txt(1240, 276, "9月の通航回復／危険は継続", TYPE["status"], COLORS["gulf_status"], WEIGHT["status"], halo=False)
txt(1735, 472, "日本方面と往復", TYPE["route"], R, WEIGHT["route"], "end", halo=False)
txt(1356, 953, "日本方面と往復", TYPE["route_compact"], R, WEIGHT["route_compact"], halo=False)

# 海峡・運河と施設名。引き出し線の終点や文字位置は画面座標で調整する。
# 地理座標を動かさずに注記だけを配置し、狭い海域の重なりを避ける。
chokepoint([56.45, 26.57], "ホルムズ海峡", 64, -46)
chokepoint([43.31, 12.58], "バブ・エル・マンデブ海峡", -70, -45)
x, y = xy([32.43, 30.5])
label_leader([(x, y), (453, 127)], C)
txt(465, 137, "スエズ運河", TYPE["chokepoint"], C, WEIGHT["chokepoint"], css="passage-label")

# 各行は、名称・代表点・文字の x/y・補足・種別・文字の基準位置。
points = [
    (
        "シディ・ケリル",
        [29.6824996, 31.0510105],
        345,
        67,
        "SUMED北端・陸上タンクからSBMを経て原油積載",
        "port",
        "start",
    ),
    (
        "アイン・スフナ",
        [32.3214022, 29.6069879],
        371,
        219,
        "SUMED南端・荷揚げ",
        "port",
        "start",
    ),
    (
        "ヤンブー",
        [38.2687784, 23.9793099],
        542,
        551,
        "紅海側の輸出拠点",
        "port",
        "end",
    ),
    (
        "ラス・タヌラ",
        [50.163, 26.645],
        1110,
        285,
        "ペルシャ湾側の輸出港",
        "port",
        "end",
    ),
    (
        "アブカイク",
        [49.6855348, 25.922357],
        1202,
        365,
        "東西原油ライン起点",
        "plant",
        "start",
    ),
    ("ハブシャン", [53.6176, 23.8279], 1268, 500, None, "plant", "end"),
    ("フジャイラ", [56.358639, 25.187944], 1515, 377, None, "port", "start"),
    (
        "ソハール",
        [56.630, 24.511667],
        1512,
        523,
        "独立した港湾拠点",
        "port",
        "end",
    ),
]
for name, p, lx, ly, sub, kind, anchor in points:
    # 荷役方式の補足は短い1行に限定し、スエズ運河の引出線との余白を取る。
    # 施設代表点は既存位置のままとし、個別の沖合ブイ座標には置き換えない。
    # ソハールは港のほぼ真下。右端へ線を回さず、文字の上辺へ垂直に結ぶ。
    role = "secondary_port" if name == "ソハール" else kind
    leader_end = (xy(p)[0], ly - TYPE[role] - SPACING["label_gap"]) if name == "ソハール" else None
    point(p, name, lx, ly, None, kind, anchor, leader_end=leader_end, role=role)
    sidi = name == "シディ・ケリル"
    if sidi:
        txt(lx, ly + SPACING["detail_line_height"], "SBMで原油積載", TYPE["detail"], LOAD, WEIGHT["detail"], anchor, halo=False)
    features.append(
        {
            "type": "Feature",
            "properties": {
                "name": name,
                "category": kind,
                "accuracy": "施設・港の代表点。積出しブイや個別設備の正確な位置ではない。",
                **({
                    "handling_method": "SBM",
                    "loading_flow": "陸上タンクから沖合のSBMを経てタンカーへ原油を積載。船間積替え（STS）とは異なる。",
                    "source": "https://www.sumed.org/?p=facilities",
                    "facility_note": "SUMED公式のSidi Kerir節は原油積載用の5基のSBMを説明。図は代表点であり、個別ブイ位置や当日の稼働・日本向け積載実績は示さない。",
                } if sidi else {}),
            },
            "geometry": {"type": "Point", "coordinates": p},
        }
    )

# 凡例は注記の少ない陸域に配置する。
add(
    f'<rect x="46" y="718" width="431" height="195" fill="{COLORS["legend_fill"]}" '
    f'opacity="{LINES["legend_opacity"]}" stroke="{COLORS["legend_border"]}" stroke-width="{LINES["legend_border_width"]}"/>'
)
txt(68, 752, "凡例", TYPE["legend_heading"], weight=WEIGHT["legend_heading"], halo=False)
for y, col, dash, t in [
    (786, G, None, "原油パイプライン（概略・一部補間）"),
    (821, R, None, "海上経路（船の往復・模式）"),
    (856, R, LINES["restricted_dash"], "南航に制約（サウジ関連船）"),
    (891, SH, None, "湾内・湾外／紫点線は積替え接続"),
]:
    line([(70, y - 6), (122, y - 6)], col, LINES["legend_width"], dash, screen=True, under=False)
    if col != G:
        roundtrip_arrows([(70, y - 6), (122, y - 6)], col, size=LINES["legend_arrow"], screen=True)
    txt(138, y, t, TYPE["legend"], weight=WEIGHT["legend"], halo=False)

# 縮尺は北緯 23 度の経度 1 度当たりの距離に基づく。方位記号は北を示す。
kmdeg = 111.32 * math.cos(math.radians(23))
length = 500 / kmdeg / (east - west) * W
xx, yy = 62, 1022
for i in range(2):
    add(
        f'<rect x="{xx + i * length / 2:.2f}" y="{yy}" '
        f'width="{length / 2:.2f}" height="{SYMBOLS["scale_height"]}" '
        f'fill="{[COLORS["scale_light"], COLORS["scale_dark"]][i]}"/>'
    )
txt(xx, yy - 10, "0", TYPE["scale"], COLORS["scale_label"], WEIGHT["scale"], halo=False)
txt(xx + length, yy - 10, "500 km", TYPE["scale"], COLORS["scale_label"], WEIGHT["scale"], "end", False)
add(f'<path d="M 1739 59 L 1731 89 L 1739 83 L 1747 89 Z" fill="{COLORS["north"]}"/>')
txt(1739, 45, "N", TYPE["north"], COLORS["north"], WEIGHT["north"], "middle", False)
if USER_LAYER["features"]:
    try:
        svg.extend(render_layer(USER_LAYER, xy, W, H))
    except ValueError as error:
        parser.error(f"{args.data_file}: {error}")
add("</g>")

# 下部の注記と帰属表示は地図のクリップ領域外に置く。
fy = TOP + H
add(f'<path d="M 0 {fy} H 1800" stroke="{COLORS["footer_rule"]}" stroke-width="{LINES["footer_rule_width"]}"/>')
txt(
    SPACING["frame_inset"],
    fy + SPACING["footer_line_height"],
    "海上の双方向矢印は船の往復を模式化。積荷・同一航路での往復実績・安全を示さず、日本からの原油輸出を意味しません。",
    TYPE["footnote"],
    COLORS["secondary"],
    WEIGHT["footnote"],
    halo=False,
)
txt(
    SPACING["frame_inset"],
    fy + 2 * SPACING["footer_line_height"],
    "赤破線は全船の完全封鎖を意味しません。湾内発はホルムズを通過。直航・湾外積替えがあり、起点・積替地点は代表位置です。",
    TYPE["footnote"],
    COLORS["secondary"],
    WEIGHT["footnote"],
    halo=False,
)
txt(
    SPACING["frame_inset"],
    fy + 3 * SPACING["footer_line_height"],
    "STS＝船間積替え、SBM＝沖合ブイ経由の積載。パイプラインの矢印は送油方向です。既存の情勢注記は9/29基準です。",
    TYPE["footnote"],
    COLORS["secondary"],
    WEIGHT["footnote"],
    halo=False,
)
add('<a href="https://www.openstreetmap.org/copyright">')
txt(
    SPACING["frame_inset"],
    fy + 122,
    "© OpenStreetMap contributors  ·  OpenFreeMap / © OpenMapTiles",
    TYPE["credit"],
    COLORS["credit"],
    WEIGHT["credit"],
    halo=False,
)
add("</a>")
txt(
    W - SPACING["frame_inset"],
    fy + 122,
    "資料：OSM・GEM・SUMED・Reuters・GME・NGA・公開AISほか",
    TYPE["source"],
    COLORS["credit"],
    WEIGHT["source"],
    "end",
    False,
)
if USER_LAYER["features"]:
    txt(
        SPACING["frame_inset"], H + TOP + BOT - 12,
        f"利用者データ更新：{USER_LAYER['updated_at']} ｜ 追加{len(USER_LAYER['features'])}件（元図の情報基準日は上記）",
        TYPE["user_data"], COLORS["user_data"], WEIGHT["user_data"], halo=False,
    )
add("</svg>")

# 出力は SVG と GeoJSON。要素・属性の順序を維持し、再生成時に比較できる形にする。
(OUT / "middle-east.svg").write_text("\n".join(svg))
(OUT / "middle-east.geojson").write_text(
    json.dumps(
        {
            "type": "FeatureCollection",
            "as_of": META["as_of"],
            "revalidated_at": META.get("revalidated_at"),
            "route_additions_as_of": META.get("route_additions_as_of"),
            "source_notes": "docs/middle-east-sources.md",
            "features": features + USER_LAYER["features"],
            **({"user_data": {
                "updated_at": USER_LAYER["updated_at"],
                "feature_ids": [feature["id"] for feature in USER_LAYER["features"]],
            }} if USER_LAYER["features"] else {}),
        },
        ensure_ascii=False,
        indent=2,
    )
)
print("Wrote SVG and feature collection")
