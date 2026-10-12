/**
 * PC幅でSVGまたはローカル見本帳を描画する。通信は行わない。
 * node scripts/preview.cjs dist/global.svg dist/global-pc1440.png
 * node scripts/preview.cjs docs/design-system.html docs/design-system.png --selector '#specimen'
 * 縮小画像は閲覧確認用。配布する原寸PNGは render.cjs で生成する。
 */
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {launchBrowser} = require('./browser.cjs');

async function main() {
  const [inputArg, outputArg, ...options] = process.argv.slice(2);
  if (!inputArg || !outputArg) throw new Error('Usage: preview.cjs input.svg|html output.png [--width 1440] [--selector CSS]');
  const defaults = JSON.parse(fs.readFileSync(path.join(__dirname, '../design/foundations.json'), 'utf8'));
  let width = defaults.preview.desktop_width;
  let selector;
  for (let i = 0; i < options.length; i += 2) {
    if (options[i] === '--width') width = Number(options[i + 1]);
    else if (options[i] === '--selector' && options[i + 1]) selector = options[i + 1];
    else throw new Error(`Unknown or incomplete option: ${options[i]}`);
  }
  if (!Number.isInteger(width) || width < 320 || width > 8192) throw new Error('Width must be an integer from 320 to 8192.');
  const input = path.resolve(inputArg);
  const output = path.resolve(outputArg);
  if (input === output) throw new Error('Input and output must differ.');
  if (!/\.(svg|html)$/i.test(input) || !/\.png$/i.test(output)) throw new Error('Expected SVG/HTML input and PNG output.');
  const browser = await launchBrowser();
  try {
    const context = await browser.newContext({viewport: {width, height: 1000}, deviceScaleFactor: 1, offline: true});
    const page = await context.newPage();
    if (/\.svg$/i.test(input)) {
      // HTML内のSVGとして拡縮すると、書体確定とレイアウトが安定する。
      const svg = fs.readFileSync(input, 'utf8');
      await page.setContent(`<html><head><style>body{margin:0}svg{display:block;width:${width}px;height:auto}</style></head><body>${svg}</body></html>`);
    } else await page.goto(pathToFileURL(input).href);
    await page.evaluate(() => document.fonts.ready);
    fs.mkdirSync(path.dirname(output), {recursive: true});
    if (selector || /\.svg$/i.test(input)) await page.locator(selector || 'svg').screenshot({path: output});
    else await page.screenshot({path: output, fullPage: true});
    console.log(JSON.stringify({output, width, selector: selector || null}));
  } finally {
    await browser.close();
  }
}
main().catch(error => {console.error(error.message); process.exitCode = 1;});
