const fs = require('fs'), path = require('path');
const { launchBrowser } = require('../../scripts/browser.cjs');
const dir = __dirname;

(async () => {
  // 保存済みのスタイルを簡素化する。タイルの取得にはネット接続が必要。
  const style = JSON.parse(
    fs.readFileSync(path.join(dir, 'data/osm-dark-style.json'))
  );
  style.layers = style.layers.filter(
    l => l.type === 'background' ||
      ['water', 'boundary_country_z0-4', 'boundary_country_z5-'].includes(l.id)
  );

  for (const l of style.layers) {
    if (l.type === 'background') {
      l.paint['background-color'] = '#29323a';
    }
    if (l.id === 'water') {
      l.paint['fill-color'] = '#0b1c2b';
    }
    if (l.id.startsWith('boundary_country')) {
      l.paint = {
        'line-color': '#586673',
        'line-opacity': .43,
        'line-width': .7,
      };
      l.filter = [
        'all',
        l.filter,
        ['!=', ['get', 'maritime'], 1],
        ['!=', ['get', 'maritime'], '1'],
      ];
    }
  }

  // 地名・航路・凡例はSVG側で重ねるため、背景には文字やアイコンを含めない。
  delete style.sprite;
  delete style.glyphs;
  fs.writeFileSync(
    path.join(dir, 'data/osm-dark-custom.json'),
    JSON.stringify(style, null, 2)
  );

  const browser = await launchBrowser({
    args: ['--enable-webgl', '--ignore-gpu-blocklist'],
  });

  try {
    const page = await browser.newPage({
      viewport: { width: 2400, height: 1120 },
      deviceScaleFactor: 2,
    });

    // 通信失敗やHTTPエラーも記録し、欠けた背景を正常な成果物として保存しない。
    let errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('requestfailed', r => errors.push(r.url() + ': ' + r.failure()?.errorText));
    page.on('response', r => {
      if (r.status() >= 400) {
        errors.push(`HTTP ${r.status()}: ${r.url()}`);
      }
    });

    await page.setContent(
      '<!doctype html><html><head><style>html,body,#map{margin:0;width:100%;height:100%;background:#0b1c2b}.maplibregl-control-container{display:none}</style></head><body><div id="map"></div></body></html>'
    );
    await page.addScriptTag({
      path: require.resolve('maplibre-gl/dist/maplibre-gl.js'),
    });

    await page.evaluate(s => {
      // 世界図の表示範囲。出力画像と同じ範囲・縮尺を後段のSVG描画でも使用する。
      window.map = new maplibregl.Map({
        container: 'map',
        style: s,
        interactive: false,
        attributionControl: false,
        preserveDrawingBuffer: true,
        center: [125, 18],
        zoom: Math.log2(2400 / 512),
        renderWorldCopies: true,
      });
      window.mapErrors = [];
      map.on('error', e => window.mapErrors.push(e.error?.message || String(e.error)));
      window.ready = new Promise(resolve => map.once('idle', resolve));
    }, style);

    // タイルの読込みと描画が落ち着くidleを待つ。90秒で終わらなければ失敗とする。
    await Promise.race([
      page.evaluate(() => window.ready),
      new Promise((_, reject) => {
        const timer = setTimeout(
          () => reject(new Error('背景地図の読込みが90秒以内に終わりませんでした')),
          90000
        );
        timer.unref();
      }),
    ]);
    errors.push(...await page.evaluate(() => window.mapErrors));
    if (errors.length) {
      throw new Error('背景の取得でエラー: ' + errors.join(' | '));
    }

    // 背景PNGと表示範囲・投影用情報を組で保存する。片方だけの差替えは位置ずれの原因になる。
    await page.screenshot({ path: path.join(dir, 'assets/osm-dark-world.png') });
    const meta = await page.evaluate(() => ({
      bounds: map.getBounds().toArray(),
      center: map.getCenter().toArray(),
      zoom: map.getZoom(),
      width: 2400,
      height: 1120,
    }));
    fs.writeFileSync(
      path.join(dir, 'data/base-projection.json'),
      JSON.stringify(meta, null, 2)
    );
    console.log(JSON.stringify({ meta, errors }));
  } finally {
    await browser.close();
  }
})().catch(e => {
  console.error(e);
  process.exit(1);
});
