"""日本向け原油輸送ルートの SVG と GeoJSON を生成する。

同じディレクトリの metadata.json と保存済みの OSM 背景画像を読み込み、
標準ライブラリだけで静的な図を組み立てる。背景画像は SVG に埋め込む。
PNG への変換は、このスクリプトとは別の共通描画処理が担当する。

航路・地点の入力座標は [経度, 緯度] の順。注記の位置は SVG 上のピクセル値で、
地理座標とは区別する。海上線は代表経由地を結んだ模式図で、AIS 航跡ではない。
実行時に日付を更新せず、図の基準日と追記日は metadata.json の値を使う。

実行例: python3 maps/global/build.py --output-dir dist
"""

import argparse
import base64
import datetime
import html
import json
import math
import sys
from pathlib import Path


# --- 入出力と図の設定 --------------------------------------------------------

D = Path(__file__).resolve().parent
# 両図で共通の独自データ検査・描画処理。実行時の作業フォルダーに依存しない。
sys.path.insert(0, str(D.parents[1] / 'scripts'))
from user_layers import load_layer, render_layer
from design_system import load_design, svg_css
from map_language import MapLanguage, LANGUAGES

parser = argparse.ArgumentParser(
    description="Generate the map SVG and representative route geometry"
)
parser.add_argument("--output-dir", type=Path)
parser.add_argument("--lang", choices=LANGUAGES, default="ja")
parser.add_argument("--data-file", type=Path, default=D.parents[1] / "user-data/global.geojson")
args = parser.parse_args()
L10N = MapLanguage("global", args.lang)
LANG_ATTRIBUTE = ' lang="en"' if args.lang == "en" else ""
if args.output_dir is None:
    args.output_dir = D.parents[1] / "dist" / ("en" if args.lang == "en" else "")
if not args.data_file.is_file():
    parser.error(f"独自データがありません: {args.data_file}")
try:
    USER_LAYER = load_layer(args.data_file, 'global')
except (ValueError, OSError) as error:
    parser.error(str(error))
OUT = args.output_dir.resolve()
if (OUT / 'global.geojson').resolve() == args.data_file.resolve():
    parser.error("入力GeoJSONと出力先を別の場所にしてください。")
OUT.mkdir(parents=True, exist_ok=True)

META = json.loads((D / "metadata.json").read_text())
AS_OF = datetime.date.fromisoformat(META["as_of"])
ADDED = datetime.date.fromisoformat(META["route_additions_as_of"])
LOCAL_ADDED = datetime.date.fromisoformat(META["local_revision_as_of"])
LAYOUT_UPDATED = datetime.date.fromisoformat(META["layout_updated_at"])
# 基準日・一部追記・作図更新を混同せず、保存済みメタデータから表示する。
DATE_LABEL = (f"{AS_OF:%Y.%m.%d} 基準 ／ {ADDED:%m.%d} 航路追記" if args.lang == "ja"
              else f"Baseline {AS_OF:%Y.%m.%d} / routes added {ADDED:%m.%d}")
UPDATE_LABEL = (
    f"{LOCAL_ADDED:%m.%d} 湾岸追記・作図更新"
    if LOCAL_ADDED == LAYOUT_UPDATED
    else f"{LOCAL_ADDED:%m.%d} 湾岸追記 ／ {LAYOUT_UPDATED:%m.%d} 作図更新"
)
if args.lang == "en":
    UPDATE_LABEL = (
        f"{LOCAL_ADDED:%m.%d} Gulf additions / layout update"
        if LOCAL_ADDED == LAYOUT_UPDATED
        else f"Gulf additions {LOCAL_ADDED:%m.%d} / layout {LAYOUT_UPDATED:%m.%d}"
    )

# 幅、地図本体の高さ、上部余白、図全体の高さ（いずれも SVG のピクセル単位）。
W, MH, TOP, H = 2400, 1120, 112, 1310
# 色・字級・線・記号は両図で共有する基盤と、この図の表示プロファイルから取得。
# 地理座標や配置座標はこのスクリプト、見た目の規則は design/ に分ける。
DS = L10N.design(load_design('global'))
TYPE = {role: (style['size'], style['weight']) for role, style in DS['typography'].items()}
COL = DS['routes']
C = DS['colors']
L = DS['lines']
SYMBOL = DS['symbols']
SPACE = DS['spacing']
if USER_LAYER['features']:
    H += SPACE['footer_user_data_height']  # 追加データの日付を下部の専用帯に表示。


# --- 投影と SVG の基本要素 ---------------------------------------------------

def M(lat):
    """緯度（度）を球面メルカトルの無次元の縦座標へ変換する。"""
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def xy(p):
    """[経度, 緯度] を、保存済み背景地図と同じ SVG 座標へ投影する。"""
    lon, lat = p
    # 背景は東経125度を中心とした世界一周分。表示範囲に経度を折り返す。
    while lon < -55:
        lon += 360
    while lon > 305:
        lon -= 360
    # 中心緯度は18度。SVG の y 軸は下向きなので、投影値を中心から引く。
    return (
        (lon + 55) / 360 * W,
        TOP + MH / 2 + (M(18) - M(lat)) * W / (2 * math.pi),
    )


svg = []


def add(s):
    """SVG の要素を描画順に蓄積する。後の要素ほど手前に描かれる。"""
    svg.append(s)


def text(
    x, y, s, size=TYPE['label'][0], color=C['primary'],
    weight=TYPE['label'][1], anchor='start', halo=True, css='', role=None,
):
    """文字列をエスケープして追加する。y は文字のベースライン位置。"""
    if role:
        size, weight = TYPE[role]
    s, x, y, size, anchor = L10N.text(s, x, y, size, anchor)
    classes = ' '.join(name for name in ('halo' if halo else '', css) if name)
    add(
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"'
        + (f' class="{classes}"' if classes else '')
        + '>' + html.escape(s) + '</text>'
    )


def path(ps):
    return 'M ' + ' L '.join(f'{x:.2f},{y:.2f}' for x, y in ps)


def line(ps, color, width=L['default_width'], dash=None, under=True, opacity=1):
    """直線の点列を追加する。注記の引出線や凡例にも使う。"""
    d = path(ps)
    if under:
        add(
            f'<path d="{d}" fill="none" stroke="{C["line_underlay"]}" '
            f'stroke-width="{width + L["underlay_extra"]}" opacity="{L["underlay_opacity"]}"/>'
        )
    add(
        f'<path d="{d}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" opacity="{opacity}"'
        + (f' stroke-dasharray="{dash}"' if dash else '')
        + '/>'
    )


# --- 航路の補間・経度の連続化・進行方向 -------------------------------------

def arrow(ps, col, at=0.6, size=SYMBOL['arrow_size'], reverse=False):
    """補間後の点列の長さ比 at の位置に、接線方向の矢印を置く。"""
    lens = [math.dist(a, b) for a, b in zip(ps, ps[1:])]
    target = sum(lens) * at
    for a, b, length in zip(ps, ps[1:], lens):
        if target <= length:
            t = target / length
            x = a[0] + t * (b[0] - a[0])
            y = a[1] + t * (b[1] - a[1])
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            if reverse:
                ang += 180
            break
        target -= length
    # 左右に続く世界地図上で、表示範囲内の矢印だけを複製する。
    for offset in (-W, 0, W):
        if 12 < x + offset < W - 12:
            add(
                f'<path class="route-arrow" data-direction="{"reverse" if reverse else "forward"}" d="M 0 0 '
                f'L {-size * SYMBOL["arrow_length_factor"]} {-size * SYMBOL["arrow_half_width_factor"]} '
                f'L {-size * SYMBOL["arrow_length_factor"]} {size * SYMBOL["arrow_half_width_factor"]} Z" fill="{col}" '
                f'transform="translate({x + offset:.2f} {y:.2f}) '
                f'rotate({ang:.2f})"/>'
            )


def roundtrip_arrows(ps, col, at=0.6, size=SYMBOL['arrow_size']):
    """同じ線上に反対向きの矢頭を置く。積荷の流向ではなく船の往復を表す。"""
    length = sum(math.dist(a, b) for a, b in zip(ps, ps[1:]))
    if length < 12:
        return  # 全球縮尺で極端に短い接続は、往復の凡例に従い矢頭を省略。
    size = min(size, length / 8)
    half_span = size * SYMBOL['arrow_pair_half_span_factor']
    center = min(length - half_span - 1, max(half_span + 1, length * at))
    arrow(ps, col, (center - half_span) / length, size, reverse=True)
    arrow(ps, col, (center + half_span) / length, size)


def smooth(ps, start_dir=None, end_dir=None):
    """経由点を通る三次ベジェ曲線と、曲線上の密な標本点列を返す。

    各点の接線は前後の点から求め、制御点の距離は隣接区間の短い方で制限する。
    沿岸の短い区間で過度に膨らまず、沖合の長い区間を滑らかに結ぶための処理。
    start_dir / end_dir は分岐・合流点で向きをそろえる単位ベクトル。
    標本点列は矢印の向きと、注記の引出線の接続位置にも使う。
    """
    ps = [p for i, p in enumerate(ps) if i == 0 or math.dist(p, ps[i - 1]) > 0.01]
    tang = []
    for i, p in enumerate(ps):
        a = ps[max(i - 1, 0)]
        b = ps[min(i + 1, len(ps) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        tang.append((dx / length, dy / length))
    if start_dir:
        tang[0] = start_dir
    if end_dir:
        tang[-1] = end_dir

    d = f'M {ps[0][0]:.3f},{ps[0][1]:.3f}'
    samples = [ps[0]]
    for i, (p, q) in enumerate(zip(ps, ps[1:])):
        dist = math.dist(p, q)
        a = min(dist, math.dist(ps[i - 1], p) if i else dist) * 0.29
        b = min(dist, math.dist(q, ps[i + 2]) if i + 2 < len(ps) else dist) * 0.29
        c1 = (p[0] + tang[i][0] * a, p[1] + tang[i][1] * a)
        c2 = (q[0] - tang[i + 1][0] * b, q[1] - tang[i + 1][1] * b)
        d += (
            f' C {c1[0]:.3f},{c1[1]:.3f} {c2[0]:.3f},{c2[1]:.3f} '
            f'{q[0]:.3f},{q[1]:.3f}'
        )
        steps = max(8, math.ceil(dist / 1.5))
        for j in range(1, steps + 1):
            t = j / steps
            u = 1 - t
            samples.append(
                tuple(
                    u * u * u * p[k]
                    + 3 * u * u * t * c1[k]
                    + 3 * u * t * t * c2[k]
                    + t * t * t * q[k]
                    for k in (0, 1)
                )
            )
    return d, samples


features = []
route_samples = {}


def route(
    name, coords, key, dash=None, width=L['route_width'], arrows=(0.58,), wrapped=False,
    start_dir=None, end_dir=None,
):
    """模式航路を描き、補間前の代表経由点を GeoJSON 用に保存する。"""
    ps = []
    for xx, yy in map(xy, coords):
        if ps:
            # 日付変更線や図の左右端で線が逆走しないよう、隣の世界へ座標を移す。
            # wrapped 引数は既存の呼び出しを維持するために残しているが、
            # この連続化は全航路に適用する。補間してから図の枠で切り抜く。
            while xx - ps[-1][0] > W / 2:
                xx -= W
            while xx - ps[-1][0] < -W / 2:
                xx += W
        ps.append((xx, yy))

    d, samples = smooth(ps, start_dir, end_dir)
    width = min(width, L['route_width'])
    for offset in (-W, 0, W):
        if (
            max(x for x, y in samples) + offset < 0
            or min(x for x, y in samples) + offset > W
        ):
            continue
        add(
            f'<path class="sea-route" d="{d}" transform="translate({offset} 0)" '
            f'fill="none" stroke="{COL[key]}" stroke-width="{width}"'
            + (f' stroke-dasharray="{dash}"' if dash else '')
            + '/>'
        )
        route_samples.setdefault(key, []).extend(
            [(x + offset, y) for x, y in samples if -10 < x + offset < W + 10]
        )
    for at in arrows or (0.5,):
        roundtrip_arrows(samples, COL[key], at, size=SYMBOL['arrow_size'] if arrows else SYMBOL['connection_arrow_size'])
    features.append({
        'type': 'Feature',
        'properties': {
            'name': name.replace(' → ', ' ↔ '),
            'route': key,
            'direction': 'bidirectional',
            'display_note': '船の往復を模式化。原油の逆向き輸送、個船の往復完了、往復で同じ航路を使うことを確認した表示ではない。',
            'geometry_note': '公表された経由地を結ぶ模式航路。AIS航跡ではない。',
        },
        'geometry': {'type': 'LineString', 'coordinates': coords},
    })
    return ps


# --- 地点表示と注記の配置 ----------------------------------------------------

def dot(
    p, label=None, at=None, color=C['strong'], size=SYMBOL['port_radius'], anchor='start',
    role='port',
):
    """地理座標 p に点を置き、ピクセル座標 at に水平なラベルを配置する。"""
    font, weight = TYPE[role]
    x, y = xy(p)
    if label and at:
        tx, ty = at
        label, tx, ty, font, anchor = L10N.text(label, tx, ty, font, anchor)
        gap = SPACE['label_gap']
        end = (tx - gap if anchor == 'start' else tx + gap, ty - font * SPACE['label_baseline_factor'])
        distance = math.dist((x, y), end)
        if distance > SPACE['label_leader_min_distance']:
            # 点の外周から文字の12px手前まで。暗い縁で国境・航路から分離する。
            start = (
                x + (end[0] - x) * (size + SPACE['label_symbol_gap']) / distance,
                y + (end[1] - y) * (size + SPACE['label_symbol_gap']) / distance,
            )
            d = path([start, end])
            add(f'<path d="{d}" fill="none" stroke="{C["ink"]}" stroke-width="{L["label_leader_underlay_width"]}"/>')
            add(
                f'<path class="label-leader" d="{d}" fill="none" '
                f'stroke="{C["secondary"]}" stroke-width="{L["label_leader_width"]}"/>'
            )
    add(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="{color}" '
        f'stroke="{C["ink"]}" stroke-width="{SYMBOL["port_border_width"]}"/>'
    )
    if label and at:
        text(
            tx, ty, label, font, C['strong'], weight, anchor,
            css='passage-label' if role == 'passage' else 'place-label',
        )


def risk_bubble(x, y, width, title, key, risk, tail, condition=None):
    """経路名と1行のリスクを示し、対象線へ直線で結ぶ。"""
    style = DS['callout']
    height = style['base_height'] + (style['line_height'] if condition else 0)
    start, target = tail
    # 引出線が航路から浮かないよう、描画後の曲線の標本点へ合わせる。
    endpoint = min(route_samples[key], key=lambda point: math.dist(point, target))
    add(
        f'<path class="callout-leader" d="{path([start, endpoint])}" '
        f'fill="none" stroke="{C["muted"]}" stroke-width="{style["leader_width"]}" '
        f'opacity="{style["leader_opacity"]}"/>'
    )
    add(f'<g class="callout" data-key="{key}">')
    add(
        f'<rect class="callout-box" x="{x}" y="{y}" width="{width}" height="{height}" '
        f'fill="{C["panel"]}" fill-opacity="{style["fill_opacity"]}" '
        f'stroke="{C["panel_border"]}" stroke-opacity="{style["border_opacity"]}" '
        f'stroke-width="{style["border_width"]}"/>'
    )
    left = x + style['padding_x']
    text(left, y + style['title_y'], title, color=COL[key], halo=False, role='callout_title')
    text(left, y + style['body_y'], risk, color=C['secondary'], halo=False, role='callout_body')
    if condition:
        text(left, y + style['body_y'] + style['line_height'], condition,
             color=C['muted'], halo=False, role='overview_condition')
    add('</g>')


# --- SVG の枠・見出し・背景画像 ----------------------------------------------

add(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}"{LANG_ATTRIBUTE}>'
)
add(
    '<defs><style>' + svg_css(DS)
    + 'path{stroke-linecap:round;stroke-linejoin:round}'
    + '</style><clipPath id="map">'
    + f'<rect y="{TOP}" width="{W}" height="{MH}"/></clipPath></defs>'
)
add(f'<rect width="{W}" height="{H}" fill="{C["frame"]}"/>')
text(SPACE['frame_inset'],53,META['title'],halo=False,role='title')
text(SPACE['frame_inset'],92,'主要航路と主なリスク・制約',color=C['secondary'],halo=False,role='subtitle')
text(W-SPACE['frame_inset'],53,DATE_LABEL,color=C['secondary'],anchor='end',halo=False,role='date')
text(W-SPACE['frame_inset'],92,UPDATE_LABEL,color=C['muted'],anchor='end',halo=False,role='header_note')

img = base64.b64encode((D / 'assets/osm-dark-world.png').read_bytes()).decode()
add(
    f'<image x="0" y="{TOP}" width="2400" height="1120" href="data:image/png;base64,{img}"/>',
)
add('<g clip-path="url(#map)">')

# --- 航路の代表経由地（各点は [経度, 緯度]） --------------------------------
# 色が重なる箇所では、後に追加した航路が手前に表示される。

yanbu = [38.2, 24.0]
sidi = [29.7, 31.1]
fuj = [56.4, 25.2]
japan = [139.7, 35.1]
us = [-94.1, 28.5]
cape = [18, -38]
malacca = [103.65, 1.2]
med = [
    yanbu,
    [37.7, 24.1],
    [36.4, 25.5],
    [34.8, 27.2],
    [33.4, 28],
    [32.4, 29.6],
    sidi,
    [28.6, 32],
    [26, 33],
    [21, 34.2],
    [16, 34.6],
    [12, 36.4],
    [11.5, 37],
    [11, 37.4],
    [10, 38],
    [2, 37],
    [-5.6, 35.9],
    [-10, 34],
    [-16, 25],
    [-19, 13],
    [-15, -3],
    [-4, -21],
    [8, -33],
    cape,
]
route('ヤンブー → SUMED → 地中海 → 喜望峰', med, '3', arrows=(0.38, 0.77), end_dir=(1, 0))
features[-1]['properties'].update({
    'direction': 'bidirectional_at_sea',
    'display_note': '双方向矢印は海上区間の船の往復を模式化。SUMEDの逆送や個別船の往復実績を示さない。',
})

# SUMED の陸送とは別の接続として、スエズ運河経由も示す。
route(
    'スエズ運河経由の代替接続',
    [
        [32.4, 29.6],
        [32.55, 29.9],
        [32.57, 30.7],
        [32.31, 31.27],
        [31.2, 31.6],
        [28.6, 32],
    ],
    '3',
    width=L['canal_width'],
    arrows=(),
)

# 米国メキシコ湾岸から大西洋・喜望峰を経由する航路。

cape_us = [
    us,
    [-89, 26.8],
    [-85, 24.3],
    [-81, 23.7],
    [-78, 26],
    [-72, 27],
    [-60, 21],
    [-48, 10],
    [-31, -7],
    [-15, -23],
    [0, -35],
    cape,
]
route(
    '米湾岸 → 大西洋 → 喜望峰',
    cape_us,
    '4',
    arrows=(0.26, 0.77),
    wrapped=True,
    end_dir=(1, 0),
)

# 喜望峰以東で複数の輸送経路が共有する区間。

common_cape = [
    cape,
    [27, -37],
    [40, -33],
    [56, -22],
    [68, -10],
    [82, 0],
    [92, 5.5],
    [96, 5.7],
    [99, 4.8],
    [101, 3],
    [103.65, 1.2],
]
route(
    '喜望峰 → インド洋 → マラッカ海峡',
    common_cape,
    'common',
    width=L['route_width'],
    arrows=(0.44,),
    start_dir=(1, 0),
    end_dir=(1, 0),
)

# 湾外からの積出しと、湾内からホルムズ海峡を通る輸送の接続。

oman = [
    fuj,
    [57.2, 25.3],
    [59.5, 23.8],
    [61.5, 21],
    [65, 16],
    [72, 9],
    [79, 5.2],
    [86, 5],
    [92, 5.5],
    [96, 5.7],
    [99, 4.8],
    [101, 3],
    malacca,
]
route('オマーン湾側 → マラッカ海峡', oman, '1', arrows=(0.47,), end_dir=(1, 0))
# 10月22日の拡大図から採用した線形の保存版。拡大図の更新を自動転記しない。
gulf_data=json.loads((D/'data/gulf-routes.geojson').read_text())['features']
def gulf_feature(category):
    return next(f for f in gulf_data if f['properties']['category']==category)
trunk=gulf_feature('schematic_gulf_shipping')
route('湾内発 → ホルムズ海峡 → 湾外',trunk['geometry']['coordinates'],'1',width=L['connection_width'],arrows=())
features[-1]['properties'].update(trunk['properties'])
das=gulf_feature('schematic_das_shuttle')
route('ダス島発のシャトル接続',das['geometry']['coordinates'],'1',width=L['connection_width'],arrows=())
features[-1]['properties'].update(das['properties'])
# 全球縮尺では積載地点を区域にまとめ、個別ブイの位置差は再現しない。
route('湾内とオマーン湾側の海上輸送接続',[[56.6,25.85],[57.2,25.3]],'1',width=L['connection_width'],arrows=())
for category in ['schematic_sts_connection','schematic_fujairah_mina_sts']:
    for f in [f for f in gulf_data if f['properties']['category']==category]:
        route(f['properties']['name'],f['geometry']['coordinates'],'1',dash=L['connection_dash'],width=L['connection_width'],arrows=())
        features[-1]['properties'].update(f['properties'])
fahal=[58.533333,23.65]
route('ミナ・アル・ハファル沖の積載 → 日本方面',[fahal,[59.2,23.78],[59.65,23.4],[61.5,21]],'1',width=L['connection_width'],arrows=())
features[-1]['properties'].update(source_notes='docs/gulf-hormuz-oman.md',accuracy='STS・SBMを区域として集約。個別荷役・貨物・運航の実績を示さない。')

# 紅海南下の制約付き航路と、日本へ向かう共通区間。

south = [
    yanbu,
    [37.7, 23.8],
    [38.4, 21.9],
    [39.8, 19.1],
    [41.15, 16.4],
    [42.7, 14.3],
    [43.4, 12.6],
    [45.5, 12],
    [50.4, 13.4],
    [54, 12.9],
    [61, 9],
    [68, 6],
    [78, 4.1],
    [86, 5],
]
route(
    'ヤンブー → バブ・エル・マンデブ → 日本方面（航行制約）',
    south,
    '2',
    dash=L['restricted_dash'],
    width=L['route_width'],
    arrows=(0.5,),
    end_dir=(1, 0),
)
asian = [
    malacca,
    [104.6, 1.1],
    [106, 2.5],
    [110, 8],
    [115, 15],
    [120, 20],
    [122, 21.4],
    [126, 26],
    [130, 29],
    [134, 31.3],
    [138.8, 34.1],
    japan,
]
route('中東・喜望峰方面の日本向け共通区間', asian, 'common', width=L['route_width'], arrows=(0.63,), start_dir=(1, 0))

# 北米から太平洋を横断する航路。

panama = [
    us,
    [-91, 26],
    [-86, 23],
    [-85.5, 21.5],
    [-83.5, 18],
    [-80, 12],
    [-79.92, 9.36],
    [-79.7, 9.1],
    [-79.57, 8.95],
    [-80, 7],
    [-83, 6],
    [-92, 9],
    [-104, 14],
    [-117, 22],
    [-135, 30],
    [-156, 35],
    [-177, 36],
    [165, 35],
    [152, 34.5],
    [143, 34.5],
    [141, 34.3],
    [140, 34.6],
    [139.85, 34.85],
    japan,
]
route('米湾岸 → パナマ運河 → 太平洋 → 日本（中型船による補完輸送・VLCC不可）', panama, '5', arrows=(0.52, 0.78))
canada = [
    [-123.1, 49.3],
    [-123.45, 49.2],
    [-123.5, 48.7],
    [-123.3, 48.3],
    [-124.7, 48.3],
    [-126, 48],
    [-133, 46.5],
    [-147, 46],
    [-163, 45],
    [-179, 43],
    [166, 40],
    [153, 37],
    [144, 35.6],
    [141, 34.3],
    [140, 34.6],
    [139.85, 34.85],
    japan,
]
route('カナダ西岸 → 北太平洋 → 日本', canada, '6', arrows=(0.39, 0.7))

# 配船専用の別線は置かず、各海上経路の往復矢印へ統合する。

# --- 地名・海域名・積替え区域 ------------------------------------------------
# 地名の位置は見やすさを優先して指定し、文字はすべて水平に置く。

for lon, lat, label in [
    (15, 10, 'アフリカ'),
    (262, 43, '北アメリカ'),
]:
    text(
        *xy((lon, lat)), label, TYPE['continent'][0], C['geography'],
        TYPE['continent'][1], 'middle', halo=False, css='geographic-label',
    )
for lon, lat, label in [
    (79, -22, 'インド洋'),
    (185, -7, '太平洋'),
    (-28, 21, '大西洋'),
]:
    text(
        *xy((lon, lat)), label, TYPE['ocean'][0], C['ocean'],
        TYPE['ocean'][1], 'middle', halo=False, css='geographic-label',
    )
dot(japan, '日本', (1314, 504), size=SYMBOL['destination_radius'], anchor='start', role='destination')
dot(us, '米国メキシコ湾岸', (2110, 561), anchor='end')
dot(canada[0], 'バンクーバー', (2020, 401))
dot(yanbu, 'ヤンブー', (581, 657), anchor='end')
dot(sidi, 'シディ・ケリル', (546, 520), anchor='end')
# 荷役方式の詳細はデータと出典に保持し、全体図では港名だけを表示する。
features.append({
    'type': 'Feature',
    'properties': {
        'name': 'シディ・ケリル沖（原油SBM積載）',
        'category': 'loading_area',
        'loading_method': 'SBM',
        'source': 'https://www.sumed.org/?p=facilities',
        'source_notes': 'docs/route-additions-20261012.md',
        'accuracy': '既存のターミナル代表点で区域を表示。個別ブイ座標や当日の稼働・個船の荷役実績を示さない。',
    },
    'geometry': {'type': 'Point', 'coordinates': sidi},
})
# 湾外の発着地をまとめ、個別のSTS・SBM注記は拡大図へ分担する。
dot(fuj, 'フジャイラなど', (815, 628))
features.append(
    {
        'type': 'Feature',
        'properties': {
            'name': 'ミナ・アル・ハファル沖（STS／原油SBM）',
            'category': 'loading_area',
            'source_notes': 'docs/route-additions-20261012.md',
            'accuracy': '区域代表点。個別ブイ・積替船の精密座標ではない。',
        },
        'geometry': {'type': 'Point', 'coordinates': fahal},
    },
)
dot([-79.8, 9.15], 'パナマ運河', (2180, 761), anchor='end', role='passage')
text(2290,812,'南アメリカ',color=C['geography'],anchor='middle',halo=False,css='geographic-label',role='continent')
dot([20, -34.8], '喜望峰周辺', (540, 975), role='passage')
dot([56.3, 26.45], 'ホルムズ海峡', (815, 574), role='passage')

# 積替え区域の代表位置。全貨物に必須の経由地を示すものではない。

for p in [[101.95, 2.4]]:
    x, y = xy(p)
    add(
        f'<circle cx="{x}" cy="{y}" r="{SYMBOL["loading_radius"]}" fill="none" '
        f'stroke="{COL["S"]}" stroke-width="{SYMBOL["loading_border_width"]}"/>'
    )
dot([101.95, 2.4], 'マラッカ沖 STS', (1105, 820), role='loading_area')
features.append({
    'type': 'Feature',
    'properties': {
        'name': 'マラッカ沖（リンギ等）：中東原油の日本向けSTS',
        'category': 'loading_area',
        'loading_method': 'STS',
        'source': 'https://www.spglobal.com/energy/en/news-research/latest-news/shipping/060926-japan-refiners-deploy-vlccs-for-ship-transfers-us-crude-amid-hormuz-disruptions',
        'source_notes': 'docs/route-additions-20261012.md',
        'reported_on': '2026-06-09',
        'accuracy': 'リンギ付近の区域代表点。報道されたリンギ・タンジュンブルアス等の船間積替えを模式化。全貨物の必須経由地、10月時点の継続・輸送量、個船の作業位置を示さない。',
    },
    'geometry': {'type': 'Point', 'coordinates': [101.95, 2.4]},
})

# --- 主要リスクを1行ずつ示す説明枠 -----------------------------------------
# 費用・荷役の詳細は戻さず、経路名とリスクだけをまとめる。
# パナマだけ船型条件を添え、VLCCが通航できるという誤読を防ぐ。
risk_bubble(64, 200, 500, '地中海・喜望峰', '3',
            '送油設備への攻撃、接続の遅れ', [(544, 306), xy(sidi)])
risk_bubble(650, 200, 540, '中東・インド洋', '1',
            '海峡・港湾への攻撃、積替え待ち', [(710, 306), xy([57.2, 25.3])])
risk_bubble(1480, 200, 540, 'カナダ西岸・太平洋', '6',
            '積出港の喫水制限、油種の制約', [(1800, 306), xy([-137, 46.35])])
risk_bubble(790, 385, 450, '紅海南下（航行制約）', '2',
            'フーシ派の攻撃・拿捕', [(790, 491), xy([39.8, 19.1])])
risk_bubble(1770, 835, 565, '米湾岸・パナマ', '5',
            '予約待ち・水位による通航制限', [(1770, 835), xy([-103, 13.6])],
            condition='中型船／VLCC不可')
risk_bubble(64, 1085, 540, '米湾岸・喜望峰', '4',
            '荒天・船腹不足による遅れ', [(230, 1085), xy([-22, -29])])

if USER_LAYER['features']:
    try:
        svg.extend(render_layer(USER_LAYER, xy, W, TOP + MH, wrap=True, top=TOP, lang=args.lang))
    except ValueError as error:
        parser.error(f"{args.data_file}: {error}")
add('</g>')
add(f'<path d="M 0 {TOP+MH} H {W}" stroke="{C["separator"]}" stroke-width="{L["separator_width"]}"/>')
# 単独で共有されても矢印と制約の意味が分かる、1行の注記を残す。
text(SPACE['frame_inset'],1264,
    '航路は模式線。矢印は船の往復で、原油の流向・個船の実績・安全を示さない。赤破線は一部船舶の航行制約。白線は共通区間。',
    color=C['secondary'],halo=False,role='footer_note')
text(SPACE['frame_inset'],1293,
    '© OpenStreetMap contributors · OpenFreeMap / © OpenMapTiles',
    color=C['muted'],halo=False,role='attribution')
text(W/2,1293,'資料：Reuters・S&P Global・GME・NGA・公開AIS・パナマ運河庁ほか',
    color=C['muted'],anchor='middle',halo=False,role='attribution')
text(W-SPACE['frame_inset'],1293,'作図：'+META['credit'],
    color=C['secondary'],anchor='end',halo=False,role='credit')
if USER_LAYER['features']:
    text(SPACE['frame_inset'],H-12,
         (f"利用者データ更新：{USER_LAYER['updated_at']} ｜ 追加{len(USER_LAYER['features'])}件" if args.lang == "ja"
          else f"User data updated: {USER_LAYER['updated_at']} / {len(USER_LAYER['features'])} features"),
         color=C['secondary'],halo=False,role='user_update')
add('</svg>')
(OUT/'global.svg').write_text('\n'.join(svg))
(OUT/'global.geojson').write_text(json.dumps({
    'type':'FeatureCollection',
    'language':args.lang,
    'as_of':META['as_of'],
    'revalidated_at':META.get('revalidated_at'),
    'route_additions_as_of':META.get('route_additions_as_of'),
    'layout_updated_at':META['layout_updated_at'],
    'local_revision_as_of':META['local_revision_as_of'],
    'source_notes':'docs/global-sources-and-costs.md',
    'features':features+USER_LAYER['features'],
    **({'user_data': {
        'updated_at': USER_LAYER['updated_at'],
        'feature_ids': [feature['id'] for feature in USER_LAYER['features']],
    }} if USER_LAYER['features'] else {}),
},ensure_ascii=False,indent=2))
print('Wrote global.svg and global.geojson')
