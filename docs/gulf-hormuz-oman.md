# ペルシャ湾・ホルムズ海峡の拡大図

地図ID：`gulf-hormuz-oman`。ペルシャ湾内のシャトル輸送、ムサンダム半島沿いの海路、フジャイラ・ソハール・ミナ・アル・ハファル沖の積載・積替えを整理したWeb用の模式図です。

## 情報の時点と限界

| 項目 | 日付・範囲 |
|---|---|
| 情勢の基準日 | 2026年9月29日 |
| 元図の航路追記 | 2026年10月12日 |
| 拡大図の局所更新 | 2026年10月22日。ダス島、フジャイラSBM、ミナ沖STS接続、海峡周辺の線形・配置 |

10月22日の変更は全面的な情勢再検証ではありません。航路・沖合の輪・分岐点は代表位置を用いた模式表示で、AIS航跡、個別便の実績、輸送量、当日の通航・安全・施設稼働を示しません。

- 海路の対向矢印は船の往復を表します。原油の双方向輸送、個船の往復完了、往復同一経路の確認ではありません。緑の矢印は送油方向です。
- 紫線はシャトル輸送、紫点線はSTSへの接続です。全貨物の積替えや、複数のSTS地点への順次寄港を意味しません。線の交差は接続を示しません。
- STSは船間積替え、SBM（SPM）は沖合ブイからの積載です。ミナ沖では両者を別の代表点で示します。
- フジャイラ発の船によるミナ・アル・ハファル沖STSは**ユーザー提供情報**です。この特定区間を裏づける公開一次資料による独立確認は行えていません。個別船・積載設備・原油種・数量は未確定です。
- ムサンダム沿岸の形状はJMICの2026年6月27日資料を参考にしています。半島北端〜東岸は海域内で丸めた模式曲線で、公表航路の厳密な再現や航海推奨経路ではありません。

## 再生成

リポジトリ直下で実行します。環境の準備は[README](../README.md#手元で地図を再生成する)を参照してください。

```sh
./build.sh gulf-hormuz-oman
./build.sh gulf-hormuz-oman --svg-only
./build.sh gulf-hormuz-oman --output-dir ./dist/review
```

通常は保存済み背景を使い、ネット接続は不要です。`--svg-only`では矢印の最終配置・PNG出力・ブラウザーによる検査を省略します。共有用SVGも通常ビルドで仕上げます。`./build.sh all`の対象は従来の中東図・全球図です。この拡大図は明示して生成します。

## 編集先

| 内容 | ファイル |
|---|---|
| 表題・情報基準日・更新範囲 | `maps/gulf-hormuz-oman/metadata.json` |
| 経路・代表点・出典・限界 | `maps/gulf-hormuz-oman/data/zoom-routes.geojson` |
| 投影・表示範囲 | `maps/gulf-hormuz-oman/data/base-projection.json` |
| 保存済みOSM背景 | `maps/gulf-hormuz-oman/assets/osm-dark-base.png` |
| ラベル・注記・曲線の生成 | `maps/gulf-hormuz-oman/build.py` |
| 矢印・PNG出力・配置検査 | `maps/gulf-hormuz-oman/render.cjs` |
| 紫線と背景の陸地重複検査 | `maps/gulf-hormuz-oman/check-water.cjs` |

色・書体・線は中東図の共通デザイン設定を参照します。下部注記のみ専用の文字役割`compact_footnote`（15 px）を使用します。`user-data/`の追加レイヤーはこの図には未対応です。経路の編集は`zoom-routes.geojson`、ラベルの編集は`build.py`で行います。

変更後はPNGと幅1440 pxの画像、配置・陸地重複の検査結果を確認してください。陸地重複検査は描画後の紫線を中心と両端で背景画像へ照合する補助です。出発港記号内の10 pxを除外し、水深・航行可否や内容の真偽は検証しません。出力SVGだけを直接修正せず、入力から再生成します。

## 主な出典

以下は設備・輸送形態・形状の根拠です。資料の公表日と、図の局所更新日は異なります。

1. [ADNOC Pipelines](https://adnoc.ae/en/adnoc-pipelines/about-us/who-we-are)：アブダビからフジャイラへの原油パイプライン。
2. [ADNOC Petroleum Ports Authority：Das Island](https://ppa.adnoc.ae/en/ports/das-zirku-mubarraz/part-iii---7)：ダス島の原油処理・貯蔵・輸出ターミナル。図の点は施設群の概略位置。
3. [Argus：Gulf of Oman STS Abu Dhabi crude prices](https://www.argusmedia.com/de/about-argus/media-centre/press-releases/argus-gulf-of-oman-sts-abu-dhabi-crude-prices)：2026年8月12日。Das原油等を湾内からオマーン湾へ運ぶSTS取引の説明。個別の日本向け貨物の確認には用いない。
4. [Port of Fujairah：Marine Services](https://fujairahport.ae/business-activities/marine-services/)：陸上施設とADNOC沖合SPMを結ぶ海底管。
5. [Fujairah Terminal Information Booklet](https://fujairahport.ae/wp-content/uploads/2020/02/Attachment-18-Fujairah-Terminal_Info-Booklet-Revised-01.11.2017.pdf)：2017年11月版。SPM-B掲載座標を設備群の代表点に使用。当日の係留・作業状態は示さない。
6. [JMIC Advisory Note 011-26](https://www.ukmto.org/-/media/ukmto/products/jmic-advisory-note-01126-southern-route-widened.pdf)：2026年6月27日。ムサンダム沿岸のOUTBOUND参照点を形状の参考に使用。
7. [OTTCO：Floating storage facility opens at Mina Al Fahal](https://www.ottco.om/news/post/floating-storage-facility-opens-mina-al-fahal)：2015年の浮体貯蔵・STS施設発表。2026年の稼働確認やフジャイラ発の特定区間の裏づけには用いない。

元図の地理情報は[中東図の線形資料](middle-east-geometry.md)と[10月12日の航路追記](route-additions-20261012.md)を参照してください。背景の帰属表示と、作図クレジット「東京大学大学院 渡邉英徳研究室」を保持します。利用条件は[READMEのライセンス案内](../README.md)と[LICENSE](../LICENSE)に従います。

背景を再取得する場合のみ `node maps/gulf-hormuz-oman/render-base.cjs` を実行します。ネット接続が必要です。背景の取得日を情報の基準日に置き換えません。
