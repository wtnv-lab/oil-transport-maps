# Pipeline geodata collected 2026-09-29 JST

## このリポジトリの収録範囲

以下は作図時の調査記録です。文中の旧ファイル名には、調査用の一時資料も含まれます。このリポジトリでは再作図に使用する抽出済みデータを `maps/middle-east/data/` に同梱しています。GEMの採用データは `gem_selected_pipelines.geojson`、東西原油線は `petroline-osm.geojson`、SUMEDは `sumed_onshore_with_gap.geojson`、スエズは `suez-canal-main.geojson` です。未同梱の原資料には下記の出典URLからアクセスできます。NGLラインは完成図には描画しません。

## Ready-to-use files

- `sumed_onshore_with_gap.geojson`: preferred SUMED depiction. Three features: OSM east section, explicitly interpolated 17.54 km gap, OSM west section. East-to-west onshore alignment totals approximately 318.27 km, consistent with official 320 km. Full original OSM relation and all its offshore branches are `osm_sumed_relation_full.json` and `osm_sumed.geojson`.
- `gem_four_pipeline_routes.geojson`: 2024 GEM public map snapshot for ADCOP, East-West crude, Abqaiq-Yanbu NGL, SUMED. Use its 28-point ADCOP route. Saudi pipelines are only four points each; parent team has more detailed OSM route. GEM SUMED has only six points and an inaccurate western endpoint, so use OSM SUMED instead.
- `osm_sidi_kerir_terminal.json`: OSM tanker facility way 93602398 footprint, approximately 29.67409 E, 31.04791 N. The pipeline's final mapped land point is 29.6824996 E, 31.0510105 N. Facility identification has an OSM note saying tentative; its connection to the SUMED relation corroborates it.

## Sources and methods

### GEM 2024 snapshot
https://github.com/GlobalEnergyMonitor/goit-tracker-greeninfo-map
https://raw.githubusercontent.com/GlobalEnergyMonitor/goit-tracker-greeninfo-map/main/docs/static/data/Oil%20Infrastructure%20-%20map%20data%202024-06-12_1934.geojson

The full file is `gem_oil_20240612.geojson`. It is an old public map snapshot, NOT current operating status, capacity, ownership, or infrastructure damage evidence. Do not use its capacity/status fields as current claims.

GEM methodology explicitly says routes may be approximated from endpoints or traced from public maps, with varying accuracy:
https://globalenergymonitor.org/projects/global-oil-infrastructure-tracker
https://www.gem.wiki/Help:Mapping_a_pipeline

ADCOP original feature is a MultiLineString with a tiny 4-point self-loop at the join 55.7524990295 E, 24.7547757766 N. In `gem_four_pipeline_routes.geojson` only that tiny self-loop was removed and contiguous main parts merged, preserving 28 main points. Endpoint coordinates: Habshan 53.6176 E, 23.8279 N; Fujairah 56.3413 E, 25.2128 N. This is a general route, not a surveyed alignment.

### OSM SUMED
https://www.openstreetmap.org/relation/11088523
https://www.openstreetmap.org/api/0.6/relation/11088523/full.json

The relation itself says `fixme=route incomplete`. Its component ways contain imagery-source caveats. Main route order:
97801692 (93 points) → 802304836 (40 points) → 107701168 (24 points) → 293024229 (11 points) → 802304835 (42 points) → [missing 17.54 km] → 97808606 reversed (38 points).

Missing span: [29.8726523,30.8461817] to [29.7536371,30.966451]. If shown, style as an inferred or approximate connection. Offshore branches are ways 802491218, 802491219, 802491220; these have `fixme=route`, so do not present their precise geometry as verified.

Onshore tank farm:
https://www.openstreetmap.org/way/93602398

Sidi Kerir gazetteer point 29.5914 E,31.0892 N is an offshore port representative point, not the onshore pipeline terminus:
https://www.getty.edu/vow/TGNFullDisplay?english=Y&find=&nation=&place=&subjectid=7526419

### Corroboration of SUMED topology
Official operator facilities page (downloaded locally as `sumed_facilities.html`) describes twin 42-inch 320 km pipelines from Ain Sukhna through Dahshour booster station to Sidi Kerir:
https://www.sumed.org/?p=facilities

A 2015 primary academic case study based on interviews with pipeline operators shows the route and crossing south of Cairo (PDF printed pages 15–16; zero-based 14–15). Local file `sumed_marlog2015.pdf`:
https://marlog.aast.edu/archive/2015/Proc/papers/53103201510001015.pdf

## Recommended map language

地図中の線は公開資料・OSMに基づく概略経路。SUMEDの一部未登録区間は補間。実測の埋設位置・航海用航路ではありません。

For OSM attribution: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright .
