"""共通設定からオフラインの見本帳HTMLを生成する。PNGはpreview.cjsで作る。"""
import html

from design_system import ROOT, font_stack, load_design, svg_css


def esc(value):
    return html.escape(str(value))


def type_sample(design, text, role, y, color=None, css="", halo=False, note=""):
    spec = design["typography"][role]
    classes = ("halo " if halo else "") + css
    return (f'<text x="0" y="{y}" font-size="{spec["size"]}" font-weight="{spec["weight"]}" '
            f'fill="{color or design["colors"]["primary"]}" class="{classes}">{esc(text)}</text>'
            f'<text x="398" y="{y}" text-anchor="end" font-size="12" fill="{design["colors"]["muted"]}">{esc(note)}</text>')


def svg_open(design, width, height, label):
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}"><style>{svg_css(design)}</style>'


def typography_specimen(region, world):
    c = region["colors"]
    samples = [svg_open(region, 408, 338, "ラベルの書体と階層の見本")]
    samples.append(type_sample(world, "日本", "destination", 39, css="port-label", halo=True, note=f'{world["typography"]["destination"]["size"]} / {world["typography"]["destination"]["weight"]}・縁あり'))
    samples.append(type_sample(region, "サウジアラビア", "country", 101, c["geography"], "area-label", note="明朝・縁なし"))
    samples.append(type_sample(region, "ラス・タヌラ", "port", 163, c["strong"], "port-label", True, f'{region["typography"]["port"]["size"]} / {region["typography"]["port"]["weight"]}・{region["halo"]["port"]}px'))
    samples.append(type_sample(region, "ホルムズ海峡", "chokepoint", 220, c["water"], "passage-label", True, f'{region["typography"]["chokepoint"]["size"]} / {region["typography"]["chokepoint"]["weight"]}・{region["halo"]["passage"]}px'))
    samples.append(type_sample(region, "アブカイク", "plant", 272, c["facility"], note=f'{region["typography"]["plant"]["size"]} / {region["typography"]["plant"]["weight"]}・縁なし'))
    samples.append(type_sample(region, "SBMで原油積載", "detail", 320, c["loading"], note=f'{region["typography"]["detail"]["size"]} / {region["typography"]["detail"]["weight"]}・縁なし'))
    return "".join(samples) + "</svg>"


def symbol_specimen(d):
    r, c, line, sym = d["routes"], d["colors"], d["lines"], d["symbols"]
    parts = [svg_open(d, 408, 338, "海上経路・制約・パイプライン・積替え・地点記号")]
    for y, label, color, dash, width, bidirectional in [
        (25, "海上経路・船の往復", r["marine"], None, line["marine_width"], True),
        (85, "原油パイプライン・送油方向", r["pipeline"], None, line["pipeline_width"], False),
        (145, "航行制約・回避", r["marine"], line["restricted_dash"], line["marine_width"], True),
        (205, "積替え接続・代表位置", r["gulf"], line["sts_dash"], line["sts_width"], True),
    ]:
        dashattr = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<path d="M 4 {y} H 122" fill="none" stroke="{color}" stroke-width="{width}"{dashattr}/>')
        # 見本は直線上の同じ矢頭。実航路は各builderが接線に合わせて配置する。
        if bidirectional:
            parts.append(f'<path d="M 43 {y} l 12 -5 v 10 z M 84 {y} l -12 -5 v 10 z" fill="{color}"/>')
        else:
            parts.append(f'<path d="M 49 {y} l 13 -6 v 12 z" fill="{color}"/>')
        parts.append(f'<text x="140" y="{y+6}" font-size="17" fill="{c["primary"]}">{label}</text>')
    parts.append(f'<path d="M 0 250 H 408" stroke="{c["panel_border"]}" stroke-width=".6"/>')
    parts.append(f'<circle cx="18" cy="286" r="{sym["port_radius"]}" fill="{c["strong"]}"/>')
    parts.append(f'<rect x="139" y="280" width="{sym["facility_size"]}" height="{sym["facility_size"]}" transform="rotate(45 145 286)" fill="{c["strong"]}"/>')
    parts.append(f'<circle cx="273" cy="286" r="{sym["loading_radius"]}" stroke="{r["loading"]}" stroke-width="{sym["loading_width"]}" fill="none"/>')
    for x, label in ((35,"港"),(164,"設備"),(292,"STS / SBM")):
        parts.append(f'<text x="{x}" y="292" font-size="17" fill="{c["primary"]}">{label}</text>')
    parts.append(f'<text x="0" y="330" font-size="13" fill="{c["muted"]}">識別要素：色・線種・形・番号・文字</text>')
    return "".join(parts) + "</svg>"


def callout_specimen(d):
    co, c, t = d["callout"], d["colors"], d["typography"]
    x, y, width = 10, 12, 552
    height = co["base_height"] + 2 * co["line_height"]
    parts = [svg_open(d, 582, 360, "直線の引出線を持つ長方形バルーンの構造見本")]
    parts.append(f'<path d="M 190 {y+height} L 430 267" stroke="{c["muted"]}" stroke-width="{co["leader_width"]}" fill="none"/>')
    parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{c["panel"]}" stroke="{c["panel_border"]}" stroke-width="{co["border_width"]}"/>')
    for tx, ty, content, role, color in [
        (x+co["padding_x"],y+co["title_y"],"1","callout_key",d["routes"]["1"]),
        (x+co["title_x"],y+co["title_y"],"経路名","callout_title",c["primary"]),
        (x+co["padding_x"],y+co["body_y"],"状況・対象・確認時点","callout_status",c["muted"]),
        (x+co["padding_x"],y+co["body_y"]+co["line_height"],"コスト：条件・増減要因","callout_body",c["secondary"]),
        (x+co["padding_x"],y+co["body_y"]+co["line_height"]*2,"リスク：通航・設備・接続","callout_body",c["secondary"]),
    ]:
        parts.append(f'<text x="{tx}" y="{ty}" fill="{color}" font-size="{t[role]["size"]}" font-weight="{t[role]["weight"]}">{content}</text>')
    parts.append(f'<path d="M 20 267 H 562" stroke="{d["routes"]["1"]}" stroke-width="{d["lines"]["route_width"]}"/>')
    parts.append(f'<path d="M 240 267 l 14 -5 v 10 z M 283 267 l -14 -5 v 10 z" fill="{d["routes"]["1"]}"/>')
    parts.append(f'<text x="20" y="312" fill="{c["muted"]}" font-size="18">本文 {t["callout_body"]["size"]}px ／ 行送り {co["line_height"]}px ／ 左右余白 {co["padding_x"]}px</text>')
    parts.append(f'<text x="20" y="345" fill="{c["muted"]}" font-size="18">引出線：直線・矢印なし ／ 枠：長方形・影なし</text>')
    return "".join(parts) + "</svg>"


def swatches(design, labels):
    return "".join(f'<div class="swatch"><i style="background:{design["routes"][key]}"></i><b>{esc(name)}</b><code>{design["routes"][key]}</code></div>' for key,name in labels)


def table(design):
    rows = "".join(f'<tr><th scope="row"><code>{esc(role)}</code></th><td>{spec["size"]}</td><td>{spec["weight"]}</td></tr>' for role,spec in design["typography"].items())
    return '<table><thead><tr><th>役割</th><th>SVG px</th><th>太さ</th></tr></thead><tbody>'+rows+'</tbody></table>'


def main():
    region, world = load_design("middle-east"), load_design("global")
    c = region["colors"]
    updated_at = max(region['updated_at'], world['updated_at'])
    # 見本帳の枠組みはHTML。地図のスタイル見本・一覧は実設定から生成する。
    css = f'''*{{box-sizing:border-box}}html{{color-scheme:dark}}body{{margin:0;background:{c['frame']};color:{c['primary']};font-family:{font_stack(region['fonts']['sans'])};font-size:15px;line-height:1.8}}a{{color:{c['water']};text-underline-offset:4px}}#specimen{{padding:38px 46px 24px;max-width:1440px;margin:auto;background:{c['frame']}}}header{{border-bottom:1px solid {c['panel_border']};padding-bottom:23px;display:flex;justify-content:space-between;gap:20px}}h1{{font-size:35px;line-height:1.35;font-weight:600;margin:4px 0 10px;letter-spacing:.015em}}p{{margin:0}}.eyebrow{{font-size:12px;letter-spacing:.18em;color:{c['muted']}}}.version{{text-align:right;white-space:nowrap;font-size:13px;color:{c['muted']};padding-top:7px}}.intro{{color:{c['secondary']};font-size:15px}}.columns{{display:grid;grid-template-columns:1fr 1fr 1.08fr;gap:30px;margin-top:27px}}h2{{font-size:18px;font-weight:600;margin:0 0 9px;line-height:1.5}}h2 span{{font-size:12px;color:{c['muted']};font-weight:400;margin-right:10px}}.caption{{font-size:13px;color:{c['muted']};line-height:1.7;margin-bottom:13px;min-height:45px}}svg{{width:100%;height:auto;display:block}}.palette{{border-top:1px solid {c['panel_border']};margin-top:27px;padding-top:22px}}.palette-heading{{display:flex;align-items:baseline;gap:22px}}.palette-heading p{{font-size:13px;color:{c['muted']}}}.swatches{{display:grid;grid-template-columns:repeat(8,1fr);gap:22px;margin-top:14px}}.swatch i{{display:block;height:4px;margin-bottom:10px}}.swatch b{{display:block;font-size:13px;font-weight:500;white-space:nowrap}}code{{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:{c['muted']}}}.regional{{margin-top:20px;display:flex;gap:25px;font-size:13px;color:{c['secondary']};align-items:center;flex-wrap:wrap}}.regional em{{font-style:normal;border-left:18px solid;padding-left:8px}}.rules{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:30px;border-top:1px solid {c['panel_border']};margin-top:24px;padding-top:20px}}.rules b{{font-size:14px;font-weight:600}}.rules p{{font-size:13px;color:{c['secondary']};line-height:1.8;margin-top:5px}}footer{{font-size:11px;color:{c['muted']};display:flex;justify-content:space-between;gap:20px;margin-top:24px}}.details{{max-width:1348px;margin:25px auto 70px;padding:28px 0;border-top:1px solid {c['panel_border']}}}.details h2{{margin-top:24px}}.tables{{display:grid;grid-template-columns:1fr 1fr;gap:45px}}table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{text-align:left;padding:7px 12px;border-bottom:1px solid {c['panel_border']};font-weight:400}}pre{{overflow:auto;background:{c['panel']};padding:16px;font-size:13px;line-height:1.7}}.links{{display:flex;gap:24px;flex-wrap:wrap}}@media(max-width:950px){{#specimen{{padding:25px}}.columns,.rules,.tables{{grid-template-columns:1fr}}.swatches{{grid-template-columns:repeat(4,1fr)}}.details{{margin:25px;padding:0}}.caption{{min-height:0}}.columns svg{{max-width:580px}}header{{display:block}}.version{{text-align:left}}footer{{display:block}}}}'''
    palette = swatches(world,[("1","1 中東・インド洋"),("2","2 紅海南下"),("3","3 地中海・喜望峰"),("4","4 米湾岸・喜望峰"),("5","5 米湾岸・パナマ"),("6","6 カナダ・太平洋"),("S","S 積載区域"),("common","共通区間")])
    regional = "".join(f'<em style="border-color:{region["routes"][key]}">{label}</em>' for key,label in [("pipeline","原油パイプライン"),("marine","海上経路"),("gulf","湾内・湾外"),("loading","積載区域")])
    page = f'''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>原油輸送マップ｜デザインシステム</title><style>{css}</style><main>
<div id="specimen"><header><div><div class="eyebrow">OIL TRANSPORT MAPS / DESIGN SYSTEM</div><h1>原油輸送マップ デザイン仕様</h1><p class="intro">文字・配色・線・記号・注記の共通仕様</p></div><div class="version">DESIGN SYSTEM {region['version']}<br>中東図・全球図 共通<br>{updated_at.replace("-", ".")}</div></header>
<div class="columns"><section><h2><span>01</span>文字の階層</h2><p class="caption">地理：明朝体 ／ 輸送：角ゴシック<br>主要地物：細縁</p>{typography_specimen(region,world)}</section><section><h2><span>02</span>線と地点記号</h2><p class="caption">背景：暗色 ／ 航路：鮮明色<br>方向・制約：矢印・線種</p>{symbol_specimen(region)}</section><section><h2><span>03</span>注記と引出線</h2><p class="caption">見出し → 状況 → コスト → リスク<br>引出線：対象線に接続 ／ 文字との重なりなし</p>{callout_specimen(world)}</section></div>
<section class="palette"><div class="palette-heading"><h2><span>04</span>航路のパレット</h2><p>全球図：番号・経由地 ／ 中東図：輸送手段 ／ 色の意味：各図の凡例</p></div><div class="swatches">{palette}</div><div class="regional"><b>中東図</b>{regional}</div></section>
<div class="rules"><section><b>余白と密度</b><p>地名：地域面積に応じた配置<br>密集箇所：ラベル移動・引出線</p></section><section><b>情報表現</b><p>実線 ≠ 安全保証 ／ 破線 ≠ 全船封鎖<br>情報基準日・追記日・版番号：別管理</p></section><section><b>表示の検査</b><p>原寸・1440px幅 ／ 重なり・視認性<br>本文コントラスト目標：4.5:1（単色面）</p></section></div>
<footer><span>設定：design/ ／ 寸法：SVG座標（px）</span><span>東京大学大学院 渡邉英徳研究室 / CC BY 4.0</span></footer></div>
<div class="details"><nav class="links"><a href="DESIGN_SYSTEM.md">設計・更新ガイド</a><a href="../design/foundations.json">共通設定</a><a href="../design/profiles/middle-east.json">中東図の設定</a><a href="../design/profiles/global.json">全球図の設定</a></nav>
<h2>設定の正本</h2><p>意匠：design/ のJSON ／ 座標・注記：各図の作図コード<br>出力：生成HTML・PNG</p><pre>python3 scripts/check_design.py
python3 scripts/build_design_guide.py
node scripts/preview.cjs docs/design-system.html docs/design-system.png --selector '#specimen'
./build.sh all</pre><div class="tables"><section><h2>中東図の文字設定</h2>{table(region)}</section><section><h2>全球図の文字設定</h2>{table(world)}</section></div>
<h2>参照と適用範囲</h2><p>地図設計：<a href="https://github.com/OrdnanceSurvey/GeoDataViz-Toolkit/blob/master/Cartographic%20Design%20Principles/README.md">Ordnance Survey</a><br>色・文字：<a href="https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html">W3C 色の使用</a> ／ <a href="https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html">文字コントラスト</a><br>検査対象：設定値・単色面の文字・描画配置<br>認証対象外：地図全体のWCAG適合・色覚特性別の識別性・航路と記述の正確性</p></div></main></html>'''
    output = ROOT / "docs/design-system.html"
    output.write_text(page)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
