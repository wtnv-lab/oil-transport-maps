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

parser = argparse.ArgumentParser(
    description="Generate the map SVG and representative route geometry"
)
parser.add_argument("--output-dir", type=Path, default=D.parents[1] / "dist")
parser.add_argument("--data-file", type=Path, default=D.parents[1] / "user-data/global.geojson")
args = parser.parse_args()
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

# 幅、地図本体の高さ、上部余白、図全体の高さ（いずれも SVG のピクセル単位）。
W, MH, TOP, H = 2400, 1120, 145, 1365
if USER_LAYER['features']:
    H += 36  # 追加データの日付は元図の基準日と分け、下部の専用帯に表示。
COL = {
    '1': '#70e49d',
    '2': '#ff727b',
    '3': '#ffbd62',
    '4': '#d19bff',
    '5': '#4edce7',
    '6': '#70aaff',
    'S': '#e6dcae',
    'common': '#dce7ee',
}

# PCで縮小して見る際も、目的地→発着地→通過点→補足の順に読める字級。
# 大陸・大洋は地理的な親として大きくするが、細い字と控えめな色で背景に置く。
# 各役割の値は (font-size, font-weight)。航路色・地理座標とは独立して管理する。
TYPE = {
    'destination': (36, 700),
    'port': (26, 600),
    'passage': (23, 500),
    'loading_area': (25, 600),
    'detail': (19, 400),
    'continent': (30, 400),
    'ocean': (31, 400),
    'local_sea': (21, 400),
    'callout_title': (28, 600),
    'callout_status': (19, 400),
    'callout_body': (21, 400),
}


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
    x, y, s, size=22, color='#eef4f8', weight=500, anchor='start', halo=True,
    css='',
):
    """文字列をエスケープして追加する。y は文字のベースライン位置。"""
    classes = ' '.join(name for name in ('halo' if halo else '', css) if name)
    add(
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}" text-anchor="{anchor}"'
        + (f' class="{classes}"' if classes else '')
        + '>' + html.escape(s) + '</text>'
    )


def path(ps):
    return 'M ' + ' L '.join(f'{x:.2f},{y:.2f}' for x, y in ps)


def line(ps, color, width=4, dash=None, under=True, opacity=1):
    """直線の点列を追加する。注記の引出線や凡例にも使う。"""
    d = path(ps)
    if under:
        add(
            f'<path d="{d}" fill="none" stroke="#071925" '
            f'stroke-width="{width + 4}" opacity=".9"/>'
        )
    add(
        f'<path d="{d}" fill="none" stroke="{color}" '
        f'stroke-width="{width}" opacity="{opacity}"'
        + (f' stroke-dasharray="{dash}"' if dash else '')
        + '/>'
    )


# --- 航路の補間・経度の連続化・進行方向 -------------------------------------

def arrow(ps, col, at=0.6, size=8, reverse=False):
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
                f'L {-size * 1.75} {-size * 0.62} '
                f'L {-size * 1.75} {size * 0.62} Z" fill="{col}" '
                f'transform="translate({x + offset:.2f} {y:.2f}) '
                f'rotate({ang:.2f})"/>'
            )


def roundtrip_arrows(ps, col, at=0.6, size=8):
    """同じ線上に反対向きの矢頭を置く。積荷の流向ではなく船の往復を表す。"""
    length = sum(math.dist(a, b) for a, b in zip(ps, ps[1:]))
    if length < 12:
        return  # 全球縮尺で極端に短い接続は、往復の凡例に従い矢頭を省略。
    size = min(size, length / 8)
    half_span = size * 2.2
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
    name, coords, key, dash=None, width=4.6, arrows=(0.58,), wrapped=False,
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
    width = min(width, 3.5)
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
        roundtrip_arrows(samples, COL[key], at, size=8 if arrows else 4)
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
    p, label=None, at=None, color='#f5f8fa', size=5.4, anchor='start',
    role='port',
):
    """地理座標 p に点を置き、ピクセル座標 at に水平なラベルを配置する。"""
    font, weight = TYPE[role]
    x, y = xy(p)
    if label and at:
        tx, ty = at
        end = (tx - 12 if anchor == 'start' else tx + 12, ty - font * 0.42)
        distance = math.dist((x, y), end)
        if distance > 26:
            # 点の外周から文字の12px手前まで。暗い縁で国境・航路から分離する。
            start = (
                x + (end[0] - x) * (size + 3) / distance,
                y + (end[1] - y) * (size + 3) / distance,
            )
            d = path([start, end])
            add(f'<path d="{d}" fill="none" stroke="#0b1c2b" stroke-width="4.5"/>')
            add(
                f'<path class="label-leader" d="{d}" fill="none" '
                'stroke="#c4d2dc" stroke-width="1.7"/>'
            )
    add(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="{color}" '
        f'stroke="#0b1c2b" stroke-width="2.5"/>'
    )
    if label and at:
        text(tx, ty, label, font, '#f3f7fa', weight, anchor, css='place-label')


def badge(x, y, s, key, r=16):
    """航路のそばに、枠付き注記と対応する番号を置く。"""
    text(x, y + 6, s, 20, COL[key], 500, 'middle')


def bubble(x, y, w, title, key, rows, tail, status=None):
    """長方形の注記を置き、矢印のない直線で対象の航路へ結ぶ。"""
    start, end = tail[0], tail[-1]
    if key in route_samples:
        # 引出線の先端が曲線から浮かないよう、補間後の最近傍点へ合わせる。
        end = min(route_samples[key], key=lambda p: math.dist(p, end))
    add(
        f'<path class="callout-leader" d="{path([start, end])}" fill="none" '
        f'stroke="#a7b4bd" stroke-width="1.1" opacity=".8"/>'
    )

    # 本文は36pxの行送り。本文2行＋状況1行の枠高は168pxになる。
    height = 96 + max(0, len(rows) - 1) * 36 + (36 if status else 0)
    add(
        f'<rect class="callout-box" x="{x}" y="{y}" width="{w}" '
        f'height="{height}" fill="#111e27" fill-opacity=".97" '
        f'stroke="#71808b" stroke-opacity=".7" stroke-width=".9"/>'
    )
    text(x + 21, y + 38, key, 25, COL[key], 600, halo=False)
    text(x + 55, y + 38, title, TYPE['callout_title'][0], '#e5ebef', TYPE['callout_title'][1], halo=False)
    yy = y + 78
    if status:
        text(x + 21, yy, status, TYPE['callout_status'][0], '#aebecb', TYPE['callout_status'][1], halo=False)
        yy += 36
    for row in rows:
        text(x + 21, yy, row, TYPE['callout_body'][0], '#dce5ec', TYPE['callout_body'][1], halo=False)
        yy += 36
    return height


# --- SVG の枠・見出し・背景画像 ----------------------------------------------

add(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" '
    f'viewBox="0 0 {W} {H}">'
)
add(
    '<defs><style>'
    'text{font-family:"Hiragino Kaku Gothic ProN","Hiragino Sans",'
    '"Noto Sans CJK JP",sans-serif}'
    '.halo{paint-order:stroke;stroke:#0b1c2b;stroke-width:3px;stroke-linejoin:round}'
    '.place-label{stroke-width:4.5px}'
    'path{stroke-linecap:round;stroke-linejoin:round}'
    '</style><clipPath id="map">'
    '<rect y="145" width="2400" height="1120"/></clipPath></defs>'
)
add(f'<rect width="{W}" height="{H}" fill="#0b1721"/>')
text(48, 62, META['title'], 39, weight=600, halo=False)
text(48, 111, '中東・北米との往復航路と、日本向け調達のコスト・リスク', 22, '#b8c9d7', 400, halo=False)
text(
    2352,
    59,
    f'{AS_OF.year}年{AS_OF.month}月{AS_OF.day}日 基準 ／ {ADDED.month}月{ADDED.day}日 航路追記',
    23,
    '#d4dfe7',
    400,
    'end',
    False,
)
text(2352, 104, '公開情報による模式図  ｜  線の太さは輸送量を示さない', 19, '#a5bacb', 400, 'end', False)
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
    width=2.6,
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
    width=4.5,
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
gulf = [
    [50.33, 26.8],
    [51.5, 27.05],
    [53.6, 26.6],
    [55.5, 26.55],
    [56.1, 26.6],
    [56.45, 26.58],
    [56.7, 26.43],
    [56.77, 26.1],
    [56.75, 25.78],
    [57.2, 25.3],
]
route('湾内発 → ホルムズ海峡 → アジア方面（直航・積替えの共通区間）', gulf, '1', width=2.7, arrows=())
route(
    'フジャイラ沖の積替え接続（模式）',
    [[56.75, 25.78], [56.6, 25.3], fuj],
    '1',
    dash='3 5',
    width=2.7,
    arrows=(),
)
route(
    'ソハール沖の積替え接続（模式）',
    [[56.75, 25.78], [57.0, 25.2], [57.0, 24.7], [58.0, 24.4], [59.5, 23.8]],
    '1',
    dash='3 5',
    width=2.7,
    arrows=(),
)

# この代表点は STS と原油 SBM の区域をまとめたもの。個別ブイの位置ではない。

fahal = [58.533333, 23.65]
route(
    'ミナ・アル・ハファル沖 STS／原油SBM積載 → 日本方面（模式）',
    [fahal, [59.2, 23.78], [59.65, 23.4], [61.5, 21]],
    '1',
    width=2.7,
    arrows=(),
)
features[-1]['properties'].update(
    {
        'source_notes': 'docs/route-additions-20261012.md',
        'accuracy': '区域代表点。STSとSBMは別方式。最新の個船・日本仕向けはユーザー提供観測で、船別実績は独立検証していない。',
    },
)

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
    dash='10 8',
    width=4.3,
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
route('中東・喜望峰方面の日本向け共通区間', asian, 'common', width=5, arrows=(0.63,), start_dir=(1, 0))

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
    (287, -4, '南アメリカ'),
]:
    text(*xy((lon, lat)), label, TYPE['continent'][0], '#8b9eab', TYPE['continent'][1], 'middle')
for lon, lat, label in [
    (79, -22, 'インド洋'),
    (185, 23, '太平洋'),
    (-28, 21, '大西洋'),
]:
    text(*xy((lon, lat)), label, TYPE['ocean'][0], '#587c95', TYPE['ocean'][1], 'middle')
dot(japan, '日本', (1314, 537), size=9, anchor='start', role='destination')
dot(us, '米国メキシコ湾岸', (2110, 594), anchor='end')
dot(canada[0], 'バンクーバー', (2020, 434))
dot(yanbu, 'ヤンブー', (581, 690), anchor='end')
dot(sidi, 'シディ・ケリル', (546, 505), anchor='end')
text(546, 535, '沖合SBMで原油積載', TYPE['detail'][0], COL['S'], TYPE['detail'][1], 'end')
sx, sy = xy(sidi)
add(
    f'<circle cx="{sx}" cy="{sy}" r="10" fill="none" '
    f'stroke="{COL["S"]}" stroke-width="2"/>'
)
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
# 湾岸の3本の引出線を上下へ分け、隣接する文字の前を横切らせない。
dot(fuj, 'フジャイラ／ソハール', (824, 651))
dot(fahal, 'ミナ・アル・ハファル沖', (815, 701))
text(815, 731, 'STS／原油SBM（模式）', TYPE['detail'][0], '#e6dcae', TYPE['detail'][1])
fx, fy = xy(fahal)
add(
    f'<circle cx="{fx}" cy="{fy}" r="9" fill="none" '
    f'stroke="{COL["S"]}" stroke-width="1.8"/>'
)
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
dot([-79.8, 9.15], 'パナマ運河', (2265, 795), role='passage')
dot([20, -34.8], '喜望峰周辺', (540, 1008), role='passage')
dot([43.4, 12.6], 'バブ・エル・マンデブ海峡', (630, 799), anchor='end', role='passage')
dot([56.3, 26.45], 'ホルムズ海峡', (815, 600), role='passage')
dot([-5.6, 35.9], 'ジブラルタル海峡', (303, 539), anchor='end', role='passage')
text(609, 631, '紅海', TYPE['local_sea'][0], '#95c4d8', TYPE['local_sea'][1], 'middle')
text(677, 603, 'ペルシャ湾', TYPE['local_sea'][0], '#95c4d8', TYPE['local_sea'][1], 'middle')
text(1105, 822, 'マラッカ海峡', TYPE['passage'][0], '#b5cfde', TYPE['passage'][1])

# 積替え区域の代表位置。全貨物に必須の経由地を示すものではない。

for p in [[56.7, 25.1], [101.95, 2.4]]:
    x, y = xy(p)
    add(
        f'<circle cx="{x}" cy="{y}" r="10" fill="none" '
        f'stroke="{COL["S"]}" stroke-width="2"/>'
    )
dot([101.95, 2.4], 'マラッカ沖（リンギ等）', (1105, 873), role='loading_area')
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

# 航路に添える番号。注記内の番号と対応する。
for x, y, key in [
    (891, 762, '1'),
    (753, 795, '2'),
    (318, 719, '3'),
    (240, 991, '4'),
    (1835, 646, '5'),
    (1710, 509, '6'),
]:
    badge(x, y, key, key)
text(712, 1085, '3・4  喜望峰経由・日本と往復', 21, '#c1ced7', 400)
text(1211, 717, '1–4', 20, '#c1ced7', 400)

# --- コスト・リスク等の注記 --------------------------------------------------
# 注記の矩形・引出線は画面上の座標で配置する。tail の末尾だけ地理座標から投影。

bubble(
    40,
    193,
    520,
    '地中海・喜望峰経由',
    '3',
    ['コスト：紅海南下比で航海が３週間以上増', 'リスク：設備への再攻撃・積替え接続の遅れ'],
    [(540, 361), xy([29.7, 31.1])],
    'ヤンブー発／9/28 再開報道・全面復旧は未確認',
)
bubble(
    628,
    198,
    578,
    '中東・インド洋経由',
    '1',
    ['コスト：保険・船腹。積替え便は追加費用', 'リスク：攻撃・混雑。湾内発はホルムズ通過'],
    [(668, 366), xy([57.2, 25.3])],
    '湾外積み＋湾内発の直航・STS／9月の通航回復',
)
bubble(
    1452,
    192,
    548,
    'カナダ西岸・太平洋経由',
    '6',
    ['コスト：直航で運河料・洋上積替費を回避', 'リスク：積出量・船型制約、油種の適合'],
    [(1806, 360), xy([-137, 46.35])],
    'Aframax級で直航／8月に日本着の実績',
)
bubble(
    752,
    388,
    536,
    '紅海南下',
    '2',
    ['コスト：短距離だが保険・通航条件が不安定', 'リスク：フーシ派の攻撃・拿捕'],
    [(752, 556), xy([47.5, 13])],
    'ヤンブー発／大型原油船の回避・全船閉鎖ではない',
)
bubble(
    1798,
    881,
    554,
    '米湾岸・パナマ経由',
    '5',
    ['コスト：運河・予約料金、積載量の制約', 'リスク：予約待ち・水位変動による制約'],
    [(2100, 881), xy([-103, 13.6])],
    '中型船による補完輸送／日本着実績あり・VLCC不可',
)
bubble(
    1778,
    1080,
    574,
    '米湾岸・喜望峰経由',
    '4',
    ['コスト：長距離で燃料・用船日数が増加', 'リスク：船腹不足、荒天・納期の長期化'],
    [(2352, 1130), xy([-56, 17.3])],
    'VLCC（大型原油タンカー）の主な代替経路',
)
bubble(
    1136,
    997,
    574,
    'マラッカ沖：日本向けSTS',
    'S',
    ['コスト：接続船・荷役・待機の費用', 'リスク：接続の遅れ、混雑・荒天'],
    [(1161, 997), xy([101.95, 2.4])],
    '中東原油を日本行きのタンカーへ／6月報道',
)
# --- 凡例・留保・クレジット --------------------------------------------------

line([(65, 1172), (135, 1172)], '#dce7ee', 3, under=False)
roundtrip_arrows([(65, 1172), (135, 1172)], '#dce7ee', at=0.5, size=7)
text(152, 1180, '海上経路（往復・模式）', 19, '#cbd8e2', halo=False)
line([(65, 1210), (135, 1210)], COL['2'], 4.5, '11 10', under=False)
text(152, 1218, '航行制約・回避', 19, '#cbd8e2', halo=False)
line([(482, 1172), (552, 1172)], COL['1'], 3.4, '3 5', under=False)
text(568, 1180, '湾外での積替え接続', 19, '#cbd8e2', halo=False)
add(
    f'<circle cx="494" cy="1210" r="9" fill="none" '
    f'stroke="{COL["S"]}" stroke-width="2"/>'
)
text(518, 1218, 'STS／SBM区域', 19, '#cbd8e2', halo=False)
text(945, 1247, '白線：複数ルートの共通区間', 18, '#a7bdcd', anchor='end', halo=False)
text(1136, 1210, 'STS＝船間積替え ／ SBM＝沖合ブイ経由の積載', 18, '#aebecb', halo=False)
if USER_LAYER['features']:
    try:
        svg.extend(render_layer(USER_LAYER, xy, W, TOP + MH, wrap=True, top=TOP))
    except ValueError as error:
        parser.error(f"{args.data_file}: {error}")
add('</g>')
add('<path d="M 0 1265 H 2400" stroke="#354a59" stroke-width="1"/>')
text(
    48,
    1300,
    '双方向矢印は船の往復（模式）。積荷・同じ経路での往復実績・安全を示しません。費用は同条件の運賃比較ではありません。',
    18,
    '#b5c5d1',
    400,
    halo=False,
)
text(2352, 1300, '作図：' + META['credit'], 20, '#d5dfe5', 400, 'end', False)
text(
    48,
    1338,
    '© OpenStreetMap contributors  ·  OpenFreeMap / © OpenMapTiles',
    16,
    '#91a8ba',
    halo=False,
)
text(
    2352,
    1338,
    '資料：Reuters・S&P Global・GME・NGA・公開AIS・パナマ運河庁ほか',
    16,
    '#91a8ba',
    anchor='end',
    halo=False,
)
if USER_LAYER['features']:
    text(
        48, H - 12,
        f"利用者データ更新：{USER_LAYER['updated_at']} ｜ 追加{len(USER_LAYER['features'])}件（元図の情報基準日は上記）",
        16, '#cbd8e2', 400, halo=False,
    )
add('</svg>')

# --- 成果物の保存 ------------------------------------------------------------
# SVG は背景画像を含む完成図、GeoJSON は補間前の代表点と出典上の留保を保存する。

(OUT / 'global.svg').write_text('\n'.join(svg))
(OUT / 'global.geojson').write_text(
    json.dumps(
        {
            'type': 'FeatureCollection',
            'as_of': META['as_of'],
            'revalidated_at': META.get('revalidated_at'),
            'route_additions_as_of': META.get('route_additions_as_of'),
            'source_notes': 'docs/global-sources-and-costs.md',
            'features': features + USER_LAYER['features'],
            **({'user_data': {
                'updated_at': USER_LAYER['updated_at'],
                'feature_ids': [feature['id'] for feature in USER_LAYER['features']],
            }} if USER_LAYER['features'] else {}),
        },
        ensure_ascii=False,
        indent=2,
    ),
)
print('Wrote map SVG and route geometry')
