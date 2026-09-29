# 原油輸送ルート地図

中東の地域図と、日本向け輸送ルートの全球図を再作成するローカルリポジトリです。航路・ラベル・注記はSVGとして描き、保存済みのOpenStreetMap系ダーク背景に重ねます。背景画像を含めたSVGと、高解像度PNGを出力できます。

**収録内容の基準日は2026年9月29日です。実行しても、通航状況・設備の稼働・費用・リスクが現在の情報に自動更新されることはありません。** 現状に合わせる場合は、出典を確認し、地図の記載と基準日を一緒に更新してください。

2026年9月29日に再検証し、中東図第7版・全球図第4版へ更新しました。ホルムズ通航回復と湾内発の直航・湾外積替えの併存、パナマ運河の9月28日喫水緩和と10月15日増枠予定を反映しています。カナダ直航の費用を一律に割高とする表現を改め、インド西岸を日本向け原油の確立した積替え拠点とする表示は外しました。根拠と確認限界は各図の出典資料に記載しています。

## 最初の準備

PNGも作成する場合は、次の環境を使います。

- Python 3.9以降
- Node.js 20以降とnpm
- Google Chrome、またはPlaywrightのChromium
- 日本語フォント。macOSではヒラギノを使用し、ほかの環境ではNoto Sans CJK JP等を用意してください。

このフォルダーで、最初に一度実行します。依存パッケージの取得にはネット接続が必要です。

```sh
npm ci
```

macOSでは標準の場所にあるGoogle Chromeを自動で利用します。ほかの環境やChromeがない場合は、Playwrightのブラウザーを取得して指定します。

```sh
npx playwright install chromium
CHROME_CHANNEL=chromium ./build.sh all
```

Playwright 1.62.1とMapLibre GL JS 5.6.1を固定しています。依存環境を変更する場合は、両方の地図を再描画して確認してください。

## 地図を作る

```sh
./build.sh                 # 両方の地図
./build.sh middle-east     # 中東の地域図
./build.sh global          # 日本向け輸送ルートの全球図
```

macOSでは、`build.command`をダブルクリックして両方を作成することもできます。通常の再作図は保存済み背景を使用するため、初期準備後はネット接続が不要です。

npmからの呼び出しも同じ処理です。

```sh
npm run build
npm run middle-east
npm run global
```

出力は毎回、次のファイルに更新されます。残しておきたい成果物は、再実行前に別名で保存してください。

| 出力 | 中東の地域図 | 全球図 |
|---|---|---|
| 投稿・配布用PNG | `dist/middle-east.png` | `dist/global.png` |
| 編集用SVG | `dist/middle-east.svg` | `dist/global.svg` |
| 代表座標・経路GeoJSON | `dist/middle-east.geojson` | `dist/global.geojson` |
| 描画確認用JSON | `dist/middle-east.qa.json` | `dist/global.qa.json` |

GeoJSONは概略位置や模式航路の代表経由点を保存したもので、個船の航跡や航海用データではありません。描画確認用JSONも、地理や記述内容の正しさを保証するものではありません。

### PythonだけでSVGを作る

```sh
./build.sh all --svg-only
./build.sh middle-east --svg-only
./build.sh global --svg-only
```

このモードはPythonのみでSVGとGeoJSONを作成します。Node.jsやブラウザー、`npm ci`は不要です。PNGとブラウザーによる描画確認は行いません。既存のPNG・描画確認用JSONが残っている場合、それらは今回のSVGに対応するとは限りません。

## 内容を更新する

| 変更したいもの | 編集する場所 |
|---|---|
| 航路、施設、ラベル、注記、配色、配置 | `maps/middle-east/build.py`、`maps/global/build.py` |
| 基準日、タイトル、全球図の作図クレジット | 各地図の`metadata.json` |
| 出典、根拠、情報の限界 | `docs/`内の関連Markdown |
| OSM系背景 | 任意の背景再取得コマンドで更新 |

基本の流れは「出典確認 → 地図と説明を編集 → 再作図 → PNGを目視確認」です。詳細は[更新・点検の手順](docs/MAINTENANCE.md)にまとめています。

背景を取得し直すときだけ、次を実行します。ネット接続が必要です。背景の更新によって、航路や注記の情勢が更新されるわけではありません。

```sh
npm run refresh-basemap -- all
# 片方だけの場合
npm run refresh-basemap -- middle-east
npm run refresh-basemap -- global
./build.sh all
```

必要に応じて環境変数を指定できます。

```sh
PYTHON=/path/to/python3 ./build.sh all
CHROME_PATH=/path/to/chrome ./build.sh all
```

`CHROME_PATH`にはChromeまたはChromiumの実行ファイルを指定します。`CHROME_CHANNEL=chromium`はPlaywrightで取得したChromiumを使う指定です。通常は環境変数を設定する必要はありません。

出力を別の場所に残す場合は、保存先を指定できます。

```sh
./build.sh all --output-dir ./dist/review
```

## 出典と保存版

- [中東図の注釈・限界](docs/middle-east-sources.md)
- [中東図の地理データ・精度](docs/middle-east-geometry.md)
- [全球図の出典・コストの読み方](docs/global-sources-and-costs.md)
- `examples/2026-09-29/`：中東図第6版・全球図第3版の完成品を保存。日常の再作図では上書きしません。
- `examples/2026-09-29-revalidated/`：再検証後の中東図第7版・全球図第4版、代表経路データと描画確認結果。
- [編集者・作業エージェント向けの方針](AGENTS.md)

対象は原油です。線の形・太さ・色から、当日の輸送実績、輸送量、安全な通航、全面的な封鎖や設備の稼働を判断しないでください。費用の注記は発生・回避要因を示しており、同条件の日本着運賃や総調達費のランキングではありません。

地図背景の帰属表示は、© OpenStreetMap contributors、OpenFreeMap、© OpenMapTilesです。編集・配布時にも表示を残してください。出典データの利用条件は各提供元に従います。全球図の作図クレジットは「東京大学大学院 渡邉英徳研究室」です。
