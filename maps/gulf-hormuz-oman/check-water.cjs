/** Check the actual smoothed shuttle paths against the saved OSM raster.
 * This checks cartographic land overlap, not navigability or safe water depth.
 * Port departure segments inside the port marker are excluded explicitly.
 */
const fs = require('node:fs');
const path = require('node:path');
const {launchBrowser} = require('../../scripts/browser.cjs');
const stem = path.resolve(process.argv[2] || path.join(__dirname, '../../dist/gulf-hormuz-oman'));
async function main() {
  const browser = await launchBrowser();
  try {
    const page = await browser.newPage({viewport: {width: 1800, height: 1034}, offline: true});
    await page.setContent(fs.readFileSync(stem + '.svg', 'utf8'));
    const result = await page.evaluate(async () => {
      const base = document.querySelector('image');
      const img = new Image(); img.src = base.getAttribute('href'); await img.decode();
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      const ctx = canvas.getContext('2d'); ctx.drawImage(img, 0, 0);
      const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      const scale = canvas.width / Number(base.getAttribute('width'));
      const top = Number(base.getAttribute('y'));
      const isLand = (x, y) => {
        const ix = Math.round(x * scale), iy = Math.round((y - top) * scale);
        if (ix < 0 || ix >= canvas.width || iy < 0 || iy >= canvas.height) return false;
        const i = 4 * (iy * canvas.width + ix);
        // Nearest of the two dominant OSM land/water fills; includes coast antialiasing.
        const rgb = [pixels[i], pixels[i + 1], pixels[i + 2]];
        const dist = c => c.reduce((s, v, k) => s + (rgb[k] - v) ** 2, 0);
        return dist([41, 47, 52]) < dist([11, 28, 43]);
      };
      const results = [];
      const sel = '[data-category="schematic_gulf_shipping"] .route, [data-category="schematic_das_shuttle"] .route, [data-category="schematic_sts_connection"] .route, [data-category="schematic_fujairah_mina_sts"] .route';
      for (const p of document.querySelectorAll(sel)) {
        const category = p.parentElement.dataset.category;
        const start = ['schematic_sts_connection', 'schematic_fujairah_mina_sts'].includes(category) ? 0 : 10;
        const half = Number(p.getAttribute('stroke-width')) / 2;
        const length = p.getTotalLength(), hits = [], centerHits = [];
        let count = 0;
        for (let d = start; d <= length; d += 0.25) {
          const q = p.getPointAtLength(d);
          const a = p.getPointAtLength(Math.max(0, d - 0.25));
          const b = p.getPointAtLength(Math.min(length, d + 0.25));
          const n = Math.hypot(b.x - a.x, b.y - a.y);
          const nx = -(b.y - a.y) / n, ny = (b.x - a.x) / n;
          if (isLand(q.x, q.y)) centerHits.push([q.x, q.y]);
          if ([-half, 0, half].some(o => isLand(q.x + nx * o, q.y + ny * o))) hits.push([q.x, q.y]);
          count++;
        }
        results.push({category, name: p.parentElement.dataset.name, samples: count,
          excludedPortDeparturePx: start, centerLandHits: centerHits.length,
          strokeLandHits: hits.length, examples: hits.slice(0, 6)});
      }
      return {method: 'Actual SVG curve sampled every 0.25 logical px, at center and both stroke edges against saved OSM raster.',
        limitation: 'Cartographic overlap only; not navigational validation. First 10 px at departure port symbols excluded.', routes: results};
    });
    fs.writeFileSync(stem + '.water-qa.json', JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify(result));
    if (result.routes.some(r => r.strokeLandHits)) process.exitCode = 1;
  } finally { await browser.close(); }
}
main().catch(e => { console.error(e); process.exitCode = 1; });
