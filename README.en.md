# Crude Oil Transport Route Maps

[日本語](README.md) · **English**

Scripts, geographic data, and source notes for three maps: the Middle East, crude oil supply routes to Japan, and a close-up of the Persian Gulf and Strait of Hormuz. The maps overlay **schematic routes** on dark basemaps derived from OpenStreetMap. You can use the finished images, reproduce them locally, or edit the data and layout with an AI coding agent.

Map design: **東京大学大学院 渡邉英徳研究室 (Watanave Laboratory, The University of Tokyo)**. Code was developed and refined with Codex.

## View the English maps

No setup is needed to view these images. Click a preview for its full-resolution PNG.

| Middle East | Routes to Japan |
|---|---|
| [![Middle East crude oil transport routes](examples/2026-10-22-english/middle-east-pc1440.png?v=en-c9bc46d94c2a)](examples/2026-10-22-english/middle-east.png?v=en-749943feb373) | [![Global crude oil transport routes to Japan](examples/2026-10-22-english/global-pc1440.png?v=en-adc6a451d6c0)](examples/2026-10-22-english/global.png?v=en-2678e1462989) |
| [PNG](examples/2026-10-22-english/middle-east.png?v=en-749943feb373) · [SVG](examples/2026-10-22-english/middle-east.svg?v=en-2cd3c45a0a24) · [GeoJSON](examples/2026-10-22-english/middle-east.geojson?v=en-2ca651e2edc4) | [PNG](examples/2026-10-22-english/global.png?v=en-2678e1462989) · [SVG](examples/2026-10-22-english/global.svg?v=en-9b0087626b3b) · [GeoJSON](examples/2026-10-22-english/global.geojson?v=en-c09c4c1e2863) |

The global overview shows six route families, major locations, and one short risk callout per route. Earlier detailed and callout-free versions remain in [`examples/`](examples/).

### Persian Gulf, Hormuz, and Omani loading locations

[![Persian Gulf, Strait of Hormuz, and Omani loading locations](examples/2026-10-22-english/gulf-hormuz-oman-pc1440.png?v=en-88bede6d5c4b)](examples/2026-10-22-english/gulf-hormuz-oman.png?v=en-0bd5da2c94b7)

[PNG](examples/2026-10-22-english/gulf-hormuz-oman.png?v=en-0bd5da2c94b7) · [SVG](examples/2026-10-22-english/gulf-hormuz-oman.svg?v=en-400f195cd146) · [GeoJSON](examples/2026-10-22-english/gulf-hormuz-oman.geojson?v=en-2b093ae4a535)

This close-up distinguishes Gulf shuttle connections, offshore STS, and SBM loading. The **Fujairah → offshore Mina al Fahal STS connection is based on user-provided information and has not been independently verified through public primary sources**. Facility descriptions do not establish that a particular transfer occurred.

## Dates and limitations

**An updated drawing is not an updated operational assessment.**

| Record | Date and scope |
|---|---|
| Situation and cost assessment | 29 September 2026 |
| Route additions | 12 October 2026 |
| Local Gulf additions and layout updates | 22 October 2026, global and Gulf close-up maps |
| English edition | 22 October 2026; translation and layout adaptation |

The October additions and English edition are **not a comprehensive revalidation** of the September assessment. Rebuilding the maps or refreshing their basemaps does not fetch current news, AIS, or operating conditions.

- Sea routes connect representative locations. They are not AIS tracks, sailing directions, proof of individual voyages, transport volumes, or safe passage.
- Paired sea-route arrows represent vessels travelling in both directions. They do not mean that crude oil is exported from Japan, that crude moves both ways, or that a vessel completed the same route in both directions. Pipeline arrows indicate the direction of crude flow.
- The red dashed route indicates restrictions, not a complete closure to every vessel. Purple dashed links indicate offshore transfer connections. Solid lines do not guarantee availability or safety.
- The Panama route is a supplementary route for smaller tankers. **VLCCs cannot transit the Panama Canal.**
- STS means ship-to-ship transfer; SBM means loading through an offshore single-buoy mooring. They are different operations. The maps cover crude oil, not the full LNG, LPG, or refined-product transport network.
- Cost discussions in the source notes describe contributing factors, not comparable freight quotes or a ranking of total procurement costs.

Detailed sources and verification limits are in the [Middle East notes](docs/middle-east-sources.md), [global sources and costs](docs/global-sources-and-costs.md), [12 October additions](docs/route-additions-20261012.md), and [Gulf close-up guide](docs/gulf-hormuz-oman.md). These documents are currently **in Japanese**.

## Reproduce the maps

### Requirements

- Python 3.9+; SVG and GeoJSON generation uses only the standard library.
- Node.js 20+, npm, and Chrome or Playwright Chromium for PNG rendering and layout checks.
- Fonts available on your system. Fonts are not bundled. Rendering has been checked on macOS; other font, browser, and OS combinations may change text widths and placement. Japanese output or Japanese custom labels also need Japanese fonts, such as Hiragino or Noto CJK.

On macOS or Linux:

```sh
git clone https://github.com/wtnv-lab/oil-transport-maps.git
cd oil-transport-maps
npm ci
npx playwright install chromium
CHROME_CHANNEL=chromium ./build.sh all --lang en
CHROME_CHANNEL=chromium ./build.sh gulf-hormuz-oman --lang en
```

The initial dependency and browser downloads need an internet connection. Normal builds use saved basemaps and can run offline. If Google Chrome is installed on macOS, it is detected automatically; you can omit the Chromium installation and `CHROME_CHANNEL=chromium` prefix.

`all` means **Middle East and global**, preserving the original behavior. Build the Gulf close-up separately.

```sh
./build.sh middle-east --lang en
./build.sh global --lang en
./build.sh gulf-hormuz-oman --lang en
./build.sh all                         # Japanese is the default
python3 scripts/build.py all --lang en --svg-only
```

On Windows, replace `./build.sh` with `py -3 scripts/build.py` after installing Node.js, dependencies, and Chromium. Windows rendering has not been verified.

### Outputs

English builds default to `dist/en/`; Japanese builds retain `dist/`. For each map, a normal build produces `{map-id}.png`, `.svg`, `.geojson`, and `.qa.json`. The Gulf close-up also produces its PC preview. A 1440 px preview of either overview can be created with:

```sh
node scripts/preview.cjs dist/en/global.svg dist/en/global-pc1440.png
node scripts/preview.cjs dist/en/middle-east.svg dist/en/middle-east-pc1440.png
```

SVGs embed their basemap image. GeoJSON records schematic locations and routes; original source notes and provenance fields retain their source language. QA JSON helps detect layout problems; it does not verify geography, claims, or navigational safety. `--svg-only` updates neither PNG nor browser QA, so old PNGs may remain in the output folder.

`dist/` is ignored by Git, and repeated builds overwrite files with the same names. An explicit output directory receives files **directly**, without an automatic language subfolder:

```sh
./build.sh all --lang en --output-dir ./dist/english-review
```

## Edit with an AI coding agent

Open the repository folder in an agent that can read and edit files, run commands, and inspect images. Alternatively, provide the repository URL or a downloaded ZIP to an AI that can actually retrieve or unpack it. A URL alone does not guarantee access to every file.

Start with this prompt:

```text
Read this repository so we can edit its maps through conversation:
https://github.com/wtnv-lab/oil-transport-maps
Use the local folder or attached ZIP if available.

Read README.en.md, AGENTS.md, and docs/AI_WORKFLOW.md first.
Then inspect the relevant map builder, input data, metadata, design profile,
and source notes. Most detailed guides are in Japanese; read them as needed.

Briefly report the files you could access, the maps and their information dates,
and whether you can edit files, execute builds, inspect PNGs, and search the web.
Do not modify anything yet; wait for my editing request.
```

Then give a concrete request, for example:

> Add the transfer location documented in the attached source to the English global map. Record the source and observation date, distinguish reported plans from completed transfers, preserve existing data, and show the rendered PNG. Keep labels short and avoid overlapping routes or callouts.

The [AI workflow](docs/AI_WORKFLOW.md), [custom-data guide](docs/USER_DATA.md), and [input reference](docs/USER_DATA_REFERENCE.md) are in Japanese. Custom layers are supported for the Middle East and global maps, using `user-data/middle-east.geojson` and `user-data/global.geojson`. **User-supplied labels and notes retain their original wording; `--lang en` does not translate custom data.** Supply English wording if you want an entirely English map. The Gulf close-up uses its own built-in GeoJSON and does not support these custom layers.

English custom-data examples are provided in `examples/user-data-en/`:

```sh
./build.sh all --lang en --data-dir examples/user-data-en --output-dir dist/en/tutorial
```

These are rendering demonstrations, not observations of real transport routes.

## Where to make changes

| Change | Files |
|---|---|
| Add or update custom points, routes, or callouts | `user-data/*.geojson`; see [schema](docs/user-data.schema.json) |
| Edit an existing map's routes, text, or label positions | `maps/<map-id>/build.py` |
| Edit Gulf close-up routes | `maps/gulf-hormuz-oman/data/zoom-routes.geojson` |
| Edit the Gulf geometry snapshot used by the global map | `maps/global/data/gulf-routes.geojson`; it is not synchronized automatically |
| Translate built-in labels and adjust English text placement | `maps/<map-id>/locales/en.json`; common loader: `scripts/map_language.py` |
| Edit shared typography, colors, and spacing | `design/foundations.json`, `design/profiles/*.json` |
| Edit titles, dates, edition numbers, and credits | Each map's `metadata.json` |
| Record evidence and unresolved claims | Corresponding source notes in `docs/` |

Coordinates use WGS84 **`[longitude, latitude]` in degrees**. Layout positions may use SVG pixels. Edit the source code or input data rather than only the generated SVG. Keep information dates separate from translation, layout, and partial-addition dates.

After editing, validate supported custom layers and render the affected maps:

```sh
./build.sh all --check-data
./build.sh all --lang en
./build.sh gulf-hormuz-oman --lang en
```

Inspect the PNGs at full resolution and at PC preview width, together with QA results. Check coastlines, arrows, leader endpoints, text spacing, and consistency with the sources. For shared custom-data changes, also run `python3 -m unittest discover -s tests -v`. See [maintenance](docs/MAINTENANCE.md) and [design system](docs/DESIGN_SYSTEM.md), both in Japanese, for additional checks.

### Repository index for agents

```yaml
project: oil-transport-maps
readme: README.en.md
instructions: AGENTS.md
workflow: docs/AI_WORKFLOW.md
detailed_documentation_language: ja
entrypoint: scripts/build.py
map_ids: [middle-east, global, gulf-hormuz-oman]
all_targets: [middle-east, global]
default_language: ja
supported_languages: [ja, en]
default_output: {ja: dist, en: dist/en}
custom_layer_maps: [middle-east, global]
custom_data: user-data/{map_id}.geojson
input_schema: docs/user-data.schema.json
builders: maps/{map_id}/build.py
metadata: maps/{map_id}/metadata.json
english_catalogs: maps/{map_id}/locales/en.json
language_loader: scripts/map_language.py
design: [design/foundations.json, design/profiles/]
english_examples: examples/2026-10-22-english/
```

## License and attribution

The project's **original code, documentation, and map design** are available under [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE). This applies only to rights the authors can license. Retain attribution, link to the license, and indicate changes when reusing or adapting this material. Suggested attribution:

> Original maps and code: 東京大学大学院 渡邉英徳研究室 (Watanave Laboratory, The University of Tokyo), [Crude Oil Transport Route Maps](https://github.com/wtnv-lab/oil-transport-maps), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: added routes and annotations.

Third-party material retains its own terms:

- **Basemaps and styles:** © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) · [OpenFreeMap](https://openfreemap.org/) / © [OpenMapTiles](https://openmaptiles.org/). Preserve the displayed attribution and follow each provider's terms.
- **External geographic data:** data derived from OSM, GEM, and other sources remains subject to its original terms. See the [geodata notes](docs/pipeline-geodata-notes.md), in Japanese, for provenance and processing.
- **Dependencies and source publications:** their respective licenses and usage terms apply.

Finished PNGs, SVGs, and GeoJSON can contain both original and third-party material. The project's CC BY notice does not replace the attribution or terms of those underlying materials.
