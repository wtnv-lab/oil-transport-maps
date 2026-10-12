# 独自データの入力仕様・手動編集リファレンス

生成AIに作業を依頼する手順は[生成AIで独自データを追加・更新する](USER_DATA.md)を参照してください。このページは、AIが生成したファイルの点検や、手動で編集する場合の参照資料です。

港・注記・航路・パイプラインを、**Pythonコードを変更せず、GeoJSONファイルの編集で追加**できます。追加データは既存の地図に重ねて描画され、ラベルや長方形の注記枠も設定できます。

この仕組みは利用者が調べたデータを表示するものです。ニュースやAISを自動取得したり、出典の内容を自動検証したりする機能ではありません。既存の航路や説明を置き換える場合は、末尾の「既存の地図そのものを更新する」を参照してください。

## 1. 描画例で試す

[READMEの実行環境の準備](../README.md#手元で地図を再生成する)を済ませ、リポジトリの直下で実行します。

```sh
# ファイルの形式・必須項目を確認。Pythonだけで実行でき、図は生成しません。
./build.sh all --data-dir examples/user-data --check-data

# 描画例を重ね、通常の出力と分けて保存します。
./build.sh all --data-dir examples/user-data --output-dir dist/tutorial
```

`dist/tutorial/middle-east.png` と `dist/tutorial/global.png` を開きます。SVG、GeoJSON、描画確認用の `*.qa.json` も同じ場所に出力されます。**`examples/user-data/` は架空の描画例です。実際の航路・港湾の運用・通航状況を示しません。**

完成イメージ：[中東図](../examples/user-data/middle-east-preview.png) · [全球図](../examples/user-data/global-preview.png)。入力例：[中東図のGeoJSON](../examples/user-data/middle-east.geojson) · [全球図のGeoJSON](../examples/user-data/global.geojson)。

ChromeではなくPlaywrightのChromiumを使う環境では、描画コマンドの先頭に `CHROME_CHANNEL=chromium` を付けてください。Windowsでは、`./build.sh` を `py -3 scripts/build.py` に置き換えます。

## 2. 自分用のデータを用意する

別のフォルダーで作業する場合は、既定の2ファイルをコピーします。すでに追加項目があれば、そのデータも引き継ぎます。コピー先に同名のファイルがないことを確認してから実行してください。

```sh
mkdir -p my-data
cp user-data/global.geojson my-data/global.geojson
cp user-data/middle-east.geojson my-data/middle-east.geojson
```

`my-data/` のファイルをテキストエディターで開きます。リポジトリ取得直後のファイルでは `features` が空です。すでに項目がある場合は保持し、下記の例を参考に追加して、確認・描画を実行します。編集対象はこの入力ファイルです。`dist/` に出るGeoJSONは既存の地図情報も含む記録用の出力で、独自データの入力ひな形ではありません。

```sh
./build.sh all --data-dir my-data --check-data
./build.sh all --data-dir my-data --output-dir dist/my-map
```

中東図だけを扱う場合は、`all` を `middle-east` に置き換えれば、`middle-east.geojson` だけで実行できます。全球図だけなら `global` です。**選択した地図に対応するファイルがない場合はエラーになります。** `all` には2ファイルとも必要です。

普段使うデータを `user-data/global.geojson` と `user-data/middle-east.geojson` に保存すれば、通常の `./build.sh all` で読み込まれます。`--data-dir` は、その実行で読むフォルダーを切り替える指定です。複数フォルダーのデータを同時に合成する指定ではありません。

## 3. データを書く

ファイル名と `map` を一致させます。`global.geojson` は `"map": "global"`、`middle-east.geojson` は `"map": "middle-east"` です。

次は、中東図に注記を1つ追加する**架空の記入例**です。座標は地図上の配置を試すための地点で、輸送や荷役の実績を示しません。

```json
{
  "type": "FeatureCollection",
  "map": "middle-east",
  "updated_at": "2026-10-12",
  "features": [
    {
      "type": "Feature",
      "id": "my-note-001",
      "geometry": {
        "type": "Point",
        "coordinates": [37.0, 29.2]
      },
      "properties": {
        "name": "描画例：注記",
        "kind": "note",
        "source": "記入方法を説明するための架空データ",
        "observed_on": "2026-10-12",
        "status": "hypothetical",
        "note": "実際の輸送・荷役を示さない。",
        "color": "#ffcb66",
        "callout": {
          "offset": [60, 0],
          "width": 360,
          "title": "描画例（架空）",
          "lines": [
            "実在の港・航路ではありません。"
          ]
        }
      }
    }
  ]
}
```

航路を追加する場合は、`features` に次の項目を加えます。これも**実際の輸送を表さない架空例**です。複数の項目はカンマで区切り、最後の項目の後ろにはカンマを付けません。

```json
{
  "type": "Feature",
  "id": "my-route-001",
  "geometry": {
    "type": "LineString",
    "coordinates": [[60.5, 15.8], [61.0, 14.6], [62.0, 13.8]]
  },
  "properties": {
    "name": "模式線の例",
    "kind": "route",
    "source": "記入方法を説明するための架空データ",
    "observed_on": "2026-10-12",
    "status": "hypothetical",
    "color": "#ffcb66",
    "line_style": "dashed",
    "width": 4,
    "arrows": true,
    "label": {
      "offset": [-25, -20],
      "font_size": 18,
      "anchor": "end"
    }
  }
}
```

### 必須項目

| 場所・項目 | 書く内容 |
|---|---|
| ファイルの `type` | `FeatureCollection` |
| `map` | `global` または `middle-east`。ファイル名・作図対象と一致させます |
| `updated_at` | この追加データを更新した日。`YYYY-MM-DD` 形式。空の `features` では `null` にできます |
| `features` | 追加する項目の配列。追加しない場合は `[]` |
| 項目の `type` | `Feature` |
| `id` | 同じファイル内で重複しない識別名。更新時も同じ値を使います |
| `geometry` | `Point` または `LineString` と、その座標 |
| `properties.name` | 地図に表示する短い名称 |
| `properties.kind` | `port`（港）、`note`（地点への注記）、`route`（航路）、`pipeline`（パイプライン） |
| `properties.source` | 根拠にしたURL、資料名、該当ページなどの出典メモ |
| `properties.observed_on` | 記述の根拠となる観測・確認日。`YYYY-MM-DD` 形式 |
| `properties.status` | `confirmed`（確認）、`reported`（報道）、`hypothetical`（仮定）のいずれか |

`port` と `note` は `Point`、`route` と `pipeline` は `LineString` を使います。`LineString` には2点以上必要です。

座標は **WGS84の `[経度, 緯度]`、単位は度**です。`[緯度, 経度]` ではありません。たとえば `[37.0, 29.2]` は東経37度・北緯29.2度です。この作図では経度−180〜180度、緯度−85〜85度を受け付けます。GeoJSONの高度・時刻などを座標の3番目以降に追加せず、必要な説明は `note` に記録してください。線では同じ座標を連続させないようにします。

### 任意項目

以下は `properties` 内に記載します。

| 項目 | 用途 |
|---|---|
| `note` | 詳細な留保・観測条件。出力GeoJSONに保存され、図には自動表示されません |
| `color` | `#ffcb66` のような6桁の16進カラー |
| `line_style` | `solid`（実線）、`dashed`（破線）、`dotted`（点線）、`dashdot`（一点鎖線） |
| `width` | 線の太さ。1〜8 px。省略時は3.5 px |
| `arrows` | `true` なら線に方向矢印を付けます。座標列の先頭から末尾の方向です。省略時は航路のみ矢印付き |
| `label.offset` | ラベル位置を `[横の移動量, 縦の移動量]` で指定。各値−5000〜5000 px |
| `label.font_size` | ラベルの文字サイズ。18〜30 px |
| `label.anchor` | `start` は文字の左端、`end` は右端を指定位置に合わせます |
| `callout.offset` | 長方形の注記枠の左上位置を `[横の移動量, 縦の移動量]` で指定。各値−5000〜5000 px |
| `callout.width` | 注記枠の幅。200〜800 px |
| `callout.title` | 注記枠の見出し |
| `callout.lines` | 本文を1〜4要素の文字列配列で指定。各要素から新しい行を始め、長い文は枠幅に合わせて折り返します |

`callout` を使う場合は、`offset`・`width`・`title`・`lines` の4項目がすべて必要です。線の設定は `LineString` に適用されます。色の省略時は港が白、航路が水色、パイプラインが緑、注記地点が淡い黄色です。線種は省略すると実線になります。

文字列は空にせず、改行を入れずに記述します。複数行の本文は `callout.lines` に分け、詳しい資料は別のMarkdownに記録してください。座標や項目の詳細な制約は [JSON Schema](user-data.schema.json) と `--check-data` で確認できます。未定義の項目名は、書き間違いを見逃さないようエラーになります。

## 4. ラベル・注記を読みやすくする

追加データは、既存の地名やバルーンに合わせて自動的に場所を空けるものではありません。まず描画し、PNGを見ながら `offset` や本文を調整します。

- **位置の基準：** `Point` は指定地点、`LineString` は表示範囲内の描画線の中央です。`offset` の正の値は右・下、負の値は左・上に動かします。
- **単位：** `offset` や文字サイズはSVG内の座標単位です。元のSVGは全球図2400 × 1365、中東図1800 × 1304で、独自データがある場合は説明帯として高さを36追加します。PNGはSVGの2倍の寸法で出力するため、たとえば横方向の `offset` を20変えると、等倍PNGでは40 px移動します。
- **ラベルだけの場合：** `name` と確認状態が表示されます。`label` を省略したときは、右18 px・上18 px、文字サイズ22 px、左揃えです。
- **注記枠を付ける場合：** `callout` に見出し・本文・位置を指定します。枠には「追加データ」と確認状態・日付が自動表示されます。`label` を省略すると、同じ名称を重ねて表示しません。ラベルも必要なら `label` を指定します。
- **本文の改行：** `callout.lines` を短い文ごとに分けます。長文は図に詰めず、`note` や別のMarkdownに記録します。`note` と `source` は本文として自動表示されません。

引出線は直線、注記枠は長方形です。線や文字が密集する場所では注記枠を海上の空いた場所に移し、引出線が別の地点や文字を横切らないようにします。重要な留保は、画像だけで共有されても伝わるよう `callout.lines` に含めてください。

`route` は滑らかな模式曲線、`pipeline` は指定座標を結ぶ折れ線として描きます。日付変更線付近などの経度のまたぎは、短い方向に連続するよう処理します。意図した方向に進むよう、必要に応じて途中の座標を追加してください。**GeoJSONの代表座標と、曲線補間後の描画線は同一ではありません。** 海岸・海峡・島を意図せず横切っていないかPNGで確認します。

## 5. 更新・削除する

すでに追加した項目を修正するときは、同じ `id` の `Feature` を編集します。名前・座標・本文・出典・確認状態を必要に応じて変更し、根拠を確認した日とファイルの更新日を記録します。異なる `id` で追加し直すと、古い項目も残って2つ描画されます。

削除するときは、その `Feature` 全体を `features` から取り除きます。すべて外す場合は `features` を `[]` にします。生成済みSVGから文字や線を消しても、次の実行で戻るため、元のGeoJSONを編集してください。

```sh
# 編集後に毎回実行します。
./build.sh all --data-dir my-data --check-data
./build.sh all --data-dir my-data --output-dir dist/my-map
```

同じ出力先のファイルは上書きされます。比較したい場合は `--output-dir dist/my-map-v2` のように新しい場所へ生成し、使用したGeoJSONと根拠資料も一緒に保存してください。リポジトリの既存の保存版は上書きしません。

入力フォルダーと出力先は分けます。入力GeoJSONと生成先が同じファイルになる指定は、元データを上書きしないようエラーにします。生成したGeoJSONには元図の地物も含まれるため、それを独自データの入力ファイルとして戻さず、自分で管理している元の入力ファイルを編集してください。

### 元の地図に戻す

追加したファイルを別の場所へ保存したうえで、各ファイルを次の空の状態に戻し、再生成します。全球図では `map` を `global` に変えます。

```json
{
  "type": "FeatureCollection",
  "map": "middle-east",
  "updated_at": null,
  "features": []
}
```

独自データを `--data-dir my-data` だけで使い、既定の `user-data/` を空のまま残している場合は、単に `./build.sh all` を実行すれば追加前の内容を再生成できます。ファイル自体を削除すると読み込みエラーになるため、空のファイルを残します。

## 6. 共有する前の確認

`--check-data` はJSON構造、必須項目、座標、日付などを検査します。出典の真偽、船の荷役、設備の稼働、航路の安全性は確認しません。図の `*.qa.json` も描画上の問題を見つける補助です。

1. **内容：** 出典がその主張を支えているか確認します。寄港・目的地表示だけで積荷やSTS／SBMでの荷役が確定したとは扱わず、確認・報道・仮定を分けます。
2. **日付：** `observed_on` は観測・確認の時点、`updated_at` は追加データの更新日です。記事の公表日と出来事の発生日が違う場合は、`note` や出典資料に両方を記録します。
3. **地理：** 経度と緯度の順序、海峡の通過位置、曲線と陸地の関係、矢印の方向を確かめます。模式線を実際のAIS航跡や推奨航路として説明しないでください。
4. **読みやすさ：** PNGの縮小表示と等倍表示で、文字の重なり・注記枠のはみ出し・引出線の指す先を確認します。
5. **共有物：** 画像の背景帰属表示・作図クレジットを維持します。画像だけで伝わらない出典や限界は、GeoJSON・Markdown・投稿文などにも添えます。外部データの利用条件は提供元の記載に従います。

図には独自データを加えたこととその日付が表示され、出力GeoJSONにも出典・確認状態が保存されます。**追加データの日付を新しくしても、既存の地図全体の情報基準日は更新されません。** 元の情勢・コスト評価は2026年9月29日、既存航路の追記は2026年10月12日です。古い評価と新しい観測が併存することを、読む人が判断できるようにしてください。

PNGも確認するには通常の描画を実行します。`--svg-only` ではSVG・GeoJSONまでを作り、PNGと描画確認結果は更新しません。

## よくあるエラー

| 状況 | 直し方 |
|---|---|
| 選択した地図のファイルがない | `--data-dir` のフォルダーに、`global.geojson` または `middle-east.geojson` を置きます。`all` では両方必要です |
| JSONを読めない | ダブルクォート、カンマ、括弧の対応を確認します。JSONにはコメントを書けません |
| `map` が一致しない | ファイル名と地図名を一致させます。ファイルのコピー後に変更し忘れないようにします |
| `id` が重複している | 新しい項目に固有の `id` を付けます。更新なら既存の項目そのものを編集します |
| 出典・日付・確認状態が足りない | `source`、`observed_on`、`status` を埋めます。仮定の場合も、その旨を記録します |
| 未定義の項目がある | [スキーマ](user-data.schema.json)で綴りを確認します。独自の説明は `note` に記載します |
| 点・線の指定が合わない | `port`／`note` は `Point`、`route`／`pipeline` は2点以上の `LineString` にします |
| 地点・経路が描画範囲外と表示される | `[経度, 緯度]` と対象地図を確認します。地点や経路全体が描画範囲に入らない場合は描画時にエラーになります |
| 注記枠が地図の範囲をはみ出す | `callout.offset`・枠幅・本文の長さを調整し、再生成します |
| 図は出るが文字が重なる | `label.offset`、`callout.offset`、本文の長さ・枠幅を調整し、PNGとQA JSONを再確認します |
| 独自ラベルが図外にはみ出す | PNGの確認結果 `userDataTextOutsideMap` に出たラベルの `offset` を内側へ調整します |

## 既存の地図そのものを更新する

独自GeoJSONは**追加用の層**です。同じ名前・同じ `id` を書いても、元からある航路・地名・注記を上書きする仕組みではありません。既存の通航状況や費用評価を更新したり、既存の線を消したりするときは、次を編集します。

| 対象 | 編集する場所 |
|---|---|
| 既存の航路・地名・注記・配置 | `maps/middle-east/build.py` または `maps/global/build.py` |
| 情報基準日・部分追記日・表題・版番号 | 同じ地図フォルダーの `metadata.json` |
| 更新の根拠・情報源・確認できない点 | `docs/` 内の対応する出典Markdown |

手順は [更新・点検の手順](MAINTENANCE.md)を参照してください。基準日を変更する場合は、その日に関連情報をどこまで再確認したかを記録します。一部の追加を、地図全体の全面的な再検証とみなさないようにしてください。
