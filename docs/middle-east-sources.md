# 中東の原油輸送ルート：公開時の注釈・限界

作成日：2026年9月29日（日本時間）。第6版は、地域図第5版に公開時の留保を加えたものです。背景・施設の位置・パイプライン線形は第5版と同じです。

## 図が示すもの

公開資料から整理した原油の主要な輸送経路と地理的な接続関係です。海上経路は模式線です。実線も、その日に運航・稼働していること、安全に通過できること、輸送量を示しません。作成日はすべての資料・船舶の観測日を意味しません。

対象は原油です。LNG・LPG・石油製品等の輸送網や、地域の全施設・全ルートを網羅した図ではありません。

## 読み違いを避けるための留保

- **赤破線：** ヤンブーから紅海南部を通るサウジ関連船への航行制約を示します。全船の完全封鎖、永久的な閉鎖、将来の通航可否を示しません。S&P Globalは9月17日付で9月9日以降のVLCC通航を確認しなかった一方、他船種は通航していると報じています。観測期間・船種を超えて一般化しません。[S&P Global、9月17日](https://www.spglobal.com/energy/en/news-research/latest-news/shipping/091726-vlccs-avoid-red-sea-strait-as-houthi-threats-boosts-rates-amid-rising-shipping-risks)
- **紫線：** 湾内で積んだ原油をホルムズ海峡の外に運び、船から船への積替え（STS）を行う仕組みです。このシャトル船自体はホルムズを通過します。図の起点をラス・タヌラ付近に置いたのは模式的な配置で、同港発の特定便を確認したものではありません。起点・積替地点・経路は個船の実航跡ではありません。[Seatrade Maritime、9月17日](https://www.seatrade-maritime.com/tankers/hormuz-shuttle-tankers-an-evolving-trend-amid-the-iran-war)
- **「日本方面」：** 目的地方向を表します。個別の船、積荷、出発日、荷揚げ港、最終仕向地を検証した線ではありません。日本向けに限定された輸送網でもありません。
- **SUMEDとスエズ：** 船型・喫水等で利用・組合せが異なります。SUMEDで部分荷揚げし、船はスエズを通り、シディ・ケリルで再積載する運用もあります。第6版は、スエズ線を地中海の西航線へ直接合流させ、すべての船がシディ・ケリルへ寄港するような表現を避けています。両者が排他的な二択という意味ではありません。[SUMED運営会社](https://sumed.org/crude/)
- **設備と線形：** OSMやGEM等の公開地理資料による概略です。SUMEDの未収録区間約17.5 kmは補間しています。施工図や測量図ではなく、稼働率・能力・損傷状況を線の形や太さから読み取ることはできません。

## 稼働状況の補足

9月28日のBloomberg配信は、サウジの東西原油パイプライン経由の輸出再開、通油量約350万バレル／日を報じました。情報源は匿名関係者で、記事時点ではAramcoとサウジ政府は回答していません。全面復旧や今後の安定稼働の確認とは扱いません。地図の実線・矢印も、この運用状態を保証する記号ではありません。[Bloomberg／Rigzone、9月28日](https://www.rigzone.com/news/wire/saudi_arabias_key_oil_pipeline_starts_exports-28-sep-2026-184718-article/)

通航制約、設備の稼働、保険、港湾・積替え能力は変化します。本図は航行判断用の資料ではありません。

## 地理データと背景

各設備・港の座標と線形の個別出典は[第5版の出典・精度資料](middle-east-geometry.md)に記載しています。第6版でもNGLラインは含めず、紅海・ペルシャ湾のラベルは水平です。

背景：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)、[OpenFreeMap](https://openfreemap.org/)、© [OpenMapTiles](https://openmaptiles.org/)。

## 公開用ファイル

- `dist/middle-east.png`：3600 × 2608 px
- `dist/middle-east.svg`：背景を内包した編集用SVG
- `dist/middle-east.geojson`：概略経路と位置、精度・出典情報
- [X投稿文案](middle-east-x-post-draft.md)：本文と返信2件

2026年9月29日時点の完成品は `examples/2026-09-29/middle-east-oil-routes-v6.*` に保存しています。
