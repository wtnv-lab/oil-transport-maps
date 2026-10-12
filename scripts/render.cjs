/**
 * 背景を内包したSVGを、オフラインのブラウザーで2倍解像度のPNGに変換する。
 * QAは文字・引出線の配置を確認する補助。地理・出典の正しさは検証しない。
 * 使用例: node scripts/render.cjs dist/global.svg dist/global.png
 */
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {launchBrowser} = require('./browser.cjs');

async function main() {
  const [input, output] = process.argv.slice(2).map(p => path.resolve(p));
  if (!input || !output) {
    throw new Error('Usage: node scripts/render.cjs map.svg map.png');
  }

  const svg = fs.readFileSync(input, 'utf8');
  const width = Number(svg.match(/<svg[^>]*width="(\d+)"/)[1]);
  const height = Number(svg.match(/<svg[^>]*height="(\d+)"/)[1]);
  const {preview} = JSON.parse(fs.readFileSync(path.join(__dirname, '../design/foundations.json'), 'utf8'));
  const rasterScale = preview.raster_scale;
  const browser = await launchBrowser();

  try {
    const context = await browser.newContext({
      viewport: {width, height},
      deviceScaleFactor: rasterScale,
      offline: true,
    });
    const page = await context.newPage();
    await page.goto(pathToFileURL(input).href);
    // フォント確定前の撮影では字幅とQAの結果が安定しない。
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({path: output});

    // evaluate内はブラウザー側。DOMの実際の配置を使い、SVG座標の推測を避ける。
    const qa = await page.evaluate(() => {
      const texts = [...document.querySelectorAll('text')].map(element => ({
        element,
        text: element.textContent,
        bounds: element.getBoundingClientRect(),
      }));
      const textOverlaps = [];
      for (let i = 0; i < texts.length; i++) {
        for (let j = i + 1; j < texts.length; j++) {
          const a = texts[i];
          const b = texts[j];
          if (
            a.bounds.left < b.bounds.right && a.bounds.right > b.bounds.left &&
            a.bounds.top < b.bounds.bottom && a.bounds.bottom > b.bounds.top
          ) {
            textOverlaps.push([a.text, b.text]);
          }
        }
      }

      // 検査対象のクラスを持つ引出線のみ。海路と文字の接触は目視でも確認する。
      const leaders = [...document.querySelectorAll('.callout-leader, .label-leader')];
      const leaderTextIntersections = [];
      leaders.forEach((element, index) => {
        const length = element.getTotalLength();
        const matrix = element.getScreenCTM();
        for (const text of texts) {
          // 線の端点と文字枠の外周を少し除外し、境界での過検出を抑える。
          for (let distance = 3; distance < length - 3; distance += 2) {
            const point = element.getPointAtLength(distance);
            const screen = new DOMPoint(point.x, point.y).matrixTransform(matrix);
            if (
              screen.x > text.bounds.left + 1 && screen.x < text.bounds.right - 1 &&
              screen.y > text.bounds.top + 1 && screen.y < text.bounds.bottom - 1
            ) {
              leaderTextIntersections.push({leader: index + 1, text: text.text});
              break;
            }
          }
        }
      });

      // 後から描いた注記枠が既存ラベルを隠す場合、文字同士の比較では見逃す。
      // 枠より前に描かれた文字だけを対象にし、枠自身の本文を除外する。
      const calloutTextOcclusions = [];
      document.querySelectorAll('.callout-box').forEach((box, index) => {
        const bounds = box.getBoundingClientRect();
        for (const text of texts) {
          const paintedBeforeBox = text.element.compareDocumentPosition(box) & Node.DOCUMENT_POSITION_FOLLOWING;
          if (paintedBeforeBox &&
              bounds.left < text.bounds.right && bounds.right > text.bounds.left &&
              bounds.top < text.bounds.bottom && bounds.bottom > text.bounds.top) {
            calloutTextOcclusions.push({callout: index + 1, text: text.text});
          }
        }
      });

      // 独自データのラベルがクリップで欠けないか、実フォントの文字枠で確認。
      // SVG本体の寸法ではなく、各レイヤーの地図領域と変換行列を使用する。
      const userTexts = [...document.querySelectorAll('.user-data-text')];
      const userDataTextOutsideMap = [];
      for (const element of userTexts) {
        const layer = element.closest('.user-data-layer');
        const clipId = layer.getAttribute('clip-path').match(/url\(#([^)]*)\)/)[1];
        const rect = document.getElementById(clipId).querySelector('rect');
        const x = Number(rect.getAttribute('x'));
        const y = Number(rect.getAttribute('y'));
        const matrix = layer.getScreenCTM();
        const a = new DOMPoint(x, y).matrixTransform(matrix);
        const b = new DOMPoint(
          x + Number(rect.getAttribute('width')), y + Number(rect.getAttribute('height'))
        ).matrixTransform(matrix);
        const bounds = element.getBoundingClientRect();
        if (
          bounds.left < a.x || bounds.right > b.x ||
          bounds.top < a.y || bounds.bottom > b.y
        ) {
          userDataTextOutsideMap.push(element.textContent);
        }
      }

      return {
        textOverlaps,
        leaderTextIntersections,
        calloutTextOcclusions,
        ...(userTexts.length ? {userDataTextOutsideMap} : {}),
        straightLeaders: leaders.every(element => !/[CQAS]/i.test(element.getAttribute('d'))),
        squareCallouts: [...document.querySelectorAll('.callout-box')].every(
          element => !element.getAttribute('rx')
        ),
        // 全球図のクレジット確認用。中東図ではfalseでもエラーにしない。
        researchCreditPresent: document.documentElement.textContent.includes(
          '東京大学大学院 渡邉英徳研究室'
        ),
      };
    });

    // 異常時にもPNGとQAを残し、修正箇所を確認できるようにする。
    const result = {width: width * rasterScale, height: height * rasterScale, ...qa};
    fs.writeFileSync(output.replace(/\.png$/i, '.qa.json'), JSON.stringify(result, null, 2) + '\n');
    console.log(JSON.stringify({output, ...result}));
    if (
      qa.textOverlaps.length || qa.leaderTextIntersections.length || qa.calloutTextOcclusions.length ||
      qa.userDataTextOutsideMap?.length ||
      !qa.straightLeaders || !qa.squareCallouts
    ) {
      throw new Error('文字・引出線の重なり、文字のはみ出し、または枠形状の問題を検出しました。PNGとQA JSONを確認してください。');
    }
  } finally {
    await browser.close();
  }
}

main().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
