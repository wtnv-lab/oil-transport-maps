# 中東の石油輸送ルート 改訂版 — 出典と精度

作成日：2026年9月29日（日本時間）。依頼の3画像は参照資料として扱い、画像内のニュース見出しや記述を現在の事実として採用していません。

## 表示修正（第5版）

- NGLライン、名称ラベル、凡例のNGL項目を削除。NGL専用のシェドガム代表点も削除。
- 他のパイプライン、海上ルートと水平の海域ラベルは維持。

## 表示修正（第4版）

- 「紅海」「ペルシャ湾」のラベルを水平にし、海域内で航路・地名との間隔を確保する位置へ調整。

## 表示修正（第3版）

- バブ・エル・マンデブ海峡の引き出し線は、文字の右側に12pxの余白を残して接続し、文字を横切らない配置へ変更。
- 当時表示していたNGLの黄色破線の下にあった連続した濃紺の下地線を削除。NGL表示は第5版で削除。
- シャトル船の模式線起点を東経50.33°・北緯26.80°のラス・タヌラ沖付近へ移動。ユーザー指定の表示位置であり、同港からの個別の運航実績を断定するものではない。

## 前回の改訂

- ヤンブーからバブ・エル・マンデブ、アデン湾を経て日本方面へ進むルートを赤破線へ変更。地図では短く「航行制約のあるルート」と表記。
- シディ・ケリルから地中海を西航し、ジブラルタル海峡・喜望峰を経て日本方面へ向かうルートの**表示範囲内の部分**を追加。喜望峰自体は図外。
- 湾内からホルムズ海峡を通りフジャイラ沖へ至るシャトル船を紫色で模式表示。第3版ではユーザー指定により起点をラス・タヌラ沖付近へ移した。終点の小さな輪は沖合の船間積替を表し、個別船の実際の積替座標ではない。
- 港の細かな説明、パイプラインの補足、長い脚注を地図から削除し、この資料へ集約。地図上は主要ラベル、簡潔な凡例、帰属表示を残した。

### 航行制約・シャトル船の追加出典

1. [EIA 2026年9月 Short-Term Energy Outlook、PDF p.5](https://www.eia.gov/outlooks/steo/pdf/steo_full.pdf?stream=top)：バブ・エル・マンデブでのサウジ輸出への攻撃、ヤンブー輸出減、スエズ経由増加。リンク先は最新版に更新されるため、本図が参照したのは2026年9月版。
2. [The National, 2026-09-12（9月13日更新）](https://www.thenationalnews.com/business/energy/2026/09/12/ship-traffic-in-bab-al-mandeb-strait-halves-as-houthis-seize-control-of-key-island/)：サウジ関連船を対象とする禁輸・攻撃、スエズとアフリカ回りへの迂回を報道。一方で海峡通航自体は続いており、全船の一律封鎖ではない。
3. [Seatrade Maritime, 2026-09-17](https://www.seatrade-maritime.com/tankers/hormuz-shuttle-tankers-an-evolving-trend-amid-the-iran-war)：船舶データに基づき、湾内からホルムズ海峡を通じたフジャイラ沖の船間積替（STS）へのシャトル輸送を解説。

## 成果物

以下の名称は第5版作成時の記録です。このリポジトリで再生成する第6版の出力は `dist/middle-east.png`（3600 × 2608 px）、`dist/middle-east.svg`、`dist/middle-east.geojson` です。[第6版の注釈・限界](middle-east-sources.md)も参照してください。

- `middle-east-oil-routes-v5.png`：3600 × 2412 pxの高解像度地図。
- `middle-east-oil-routes-v5.svg`：背景画像を内包したSVG。日本語ラベル、線、凡例を編集できます。
- `data/map-features-v5.geojson`：地図に使ったパイプライン線、港・施設の代表点、概略海上ルート。各線に出典・精度属性付き。
- 第5版のPNG・SVG・GeoJSONにはNGLラインとシェドガム代表点を含めていません。

## 元図から修正した点

1. 東西原油パイプライン（Petroline）の起点を**ラス・タヌラではなくアブカイク**に修正。ラス・タヌラは別の湾岸輸出港として表示。
2. NGLラインは第5版で削除。
3. 東西原油線はOSM収録経路を採用。
4. ハブシャン—フジャイラ線はGEMの公開線形で内陸の屈曲を再現。ソハールは別の港として示し、ADCOPとは接続していません。
5. SUMEDはアイン・スフナ—ダハシュール—シディ・ケリルを結ぶ陸上線、スエズ運河は別の水路として表示。
6. 日本方面の矢印は目的地方向を示す地理的な概略線です。紅海南航の赤破線はサウジ関連船への航行制約を表します。全船種・全船籍の一律の完全封鎖を表すものではありません。個別船の運航実績・実航跡も示していません。

## 背景地図

[OpenFreeMap](https://openfreemap.org/)のOSM由来ベクトルタイルを使用。[Darkスタイル](https://tiles.openfreemap.org/styles/dark)の陸地・海・国境を配色調整し、一般地名ラベルと海上の行政境界線を省いて日本語ラベルを追加しました。

帰属：© [OpenStreetMap contributors](https://www.openstreetmap.org/copyright)（ODbL）、[OpenFreeMap](https://openfreemap.org/)、© [OpenMapTiles](https://openmaptiles.org/)。

Web Mercator、北が上、傾きなし。表示範囲は概ね東経25.102–63.898°、北緯11.400–32.800°。縮尺バーは北緯23°を基準としています。

## パイプライン・運河の根拠

| 対象 | 地理データ | 接続関係・施設の一次資料 | 地図での扱い |
|---|---|---|---|
| 東西原油線 | OSM [way 1044430260](https://www.openstreetmap.org/way/1044430260)＋[way 54729631](https://www.openstreetmap.org/way/54729631)、589点 | [米EIA サウジアラビア背景資料](https://www.eia.gov/international/content/analysis/countries_long/Saudi_Arabia/saudi_arabia_background.pdf) | アブカイク処理施設→ヤンブー貯油施設。公開OSM線形。積出桟橋への枝線は省略 |
| ADCOP | [GEM公式公開マップデータ（2024-06-12）](https://github.com/GlobalEnergyMonitor/goit-tracker-greeninfo-map)、28点 | [ADNOC Pipelines](https://adnoc.ae/en/adnoc-pipelines/about-us/who-we-are)、[ADNOC 2012 Sustainability Report p64](https://www.adnoc.ae/-/media/adnoc/files/publications/adnocsustainabilityreport2012_english.ashx) | ハブシャン—フジャイラ。現行企業紹介の長さは約406km。微小な自己ループを除き連続線に統合。資料に基づく概略 |
| SUMED | [OSM relation 11088523](https://www.openstreetmap.org/relation/11088523) | [SUMED施設説明](https://www.sumed.org/?p=facilities)、[SUMED Crude Oil](https://sumed.org/crude/) | ダハシュール経由。並行2線を1線で表現。公式は各320km、採用形状は補間を含め約318km |
| スエズ運河 | OSM [way 5038117](https://www.openstreetmap.org/way/5038117)＋[way 925360882](https://www.openstreetmap.org/way/925360882)、92点 | [Suez Canal Authority](https://www.suezcanal.gov.eg/English/Navigation/Pages/NavigationSystem.aspx) | ポートサイド—スエズの主要旧主線・湖区の代表経路。新運河など並行水路は省略 |

SUMEDのOSMデータには未完成の注記があります。東経29.8726523°・北緯30.8461817°から東経29.7536371°・北緯30.966451°までの約17.54kmは直線で補間し、**緑の短い破線**で区別しました。GEM旧データの西端は陸上タンク群から離れていたため採用せず、OSM経路の西端を採用しています。

[GEMの方法論](https://globalenergymonitor.org/projects/global-oil-infrastructure-tracker/)では、線形は公開地図からのトレースや端点・中間点による近似を含みます。OSMも共同編集データです。いずれも埋設位置を示す施工図・測量図の精度を保証しません。GEMの2024年データは線形にのみ利用し、現在の容量、所有者、稼働状況の根拠にはしていません。

## 港・施設の代表点（経度、緯度）

| 地点 | 経度 | 緯度 | 根拠・意味 |
|---|---:|---:|---|
| シディ・ケリル | 29.682500 | 31.051011 | SUMED OSM陸上経路終端。沖合積出しブイそのものではない |
| アイン・スフナ | 32.321402 | 29.606988 | SUMED OSM陸上経路起点。港代表点は[エジプト海運省](https://www.mts.gov.eg/ar/port/ميناء-سوميد-بالعين-السخنة/)とも照合 |
| ヤンブー | 38.268778 | 23.979310 | OSM東西線の貯油施設終端 |
| アブカイク | 49.685535 | 25.922357 | OSM東西線の処理施設起点 |
| ラス・タヌラ | 50.163000 | 26.645000 | 港地区の概略代表点。[Aramco港湾資料](https://www.aramco.com/en/what-we-do/operations/ports-and-terminals)を参照 |
| ハブシャン | 53.617600 | 23.827900 | GEM ADCOP線の起点。地域・工場全体の中心とは異なる |
| フジャイラ | 56.358639 | 25.187944 | [IADC施工事例](https://www.iadc-dredging.com/wp-content/uploads/2016/09/iadc-book-beyond-sand-and-sea-low-res.pdf)の港代表点。ADCOPの陸上線末端・沖合設備とは区別 |
| ソハール | 56.630000 | 24.511667 | [SOHAR Port Information Guide p19](https://soharportandfreezone.om/wp-content/uploads/2025/04/SOHAR-Port-Information-Guide.pdf)の港口座標 |

フジャイラのADNOC積出設備は沖合SPMです。[港公開ターミナル案内](https://fujairahport.ae/wp-content/uploads/2020/02/Attachment-18-Fujairah-Terminal_Info-Booklet-Revised-01.11.2017.pdf)を参照。広域地図では港の代表点を使用しました。ソハールはホルムズ海峡の外側に位置する独立した港湾拠点で、ADCOPに接続しているとは表示していません。

SUMEDの部分荷揚げ、船のスエズ運河北上、シディ・ケリルでの再積込みは[運営会社が説明する仕組み](https://sumed.org/crude/)に基づきます。この地図では具体的な船や輸送日の運航実績は示していません。
