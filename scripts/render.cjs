const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {launchBrowser} = require('./browser.cjs');

(async () => {
  const [input, output] = process.argv.slice(2).map(p => path.resolve(p));
  if (!input || !output) throw new Error('Usage: node scripts/render.cjs map.svg map.png');
  const svg = fs.readFileSync(input, 'utf8');
  const width = Number(svg.match(/<svg[^>]*width="(\d+)"/)[1]);
  const height = Number(svg.match(/<svg[^>]*height="(\d+)"/)[1]);
  const browser = await launchBrowser();
  try {
    const context = await browser.newContext({viewport: {width, height}, deviceScaleFactor: 2, offline: true});
    const page = await context.newPage();
    await page.goto(pathToFileURL(input).href);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({path: output});
    const qa = await page.evaluate(() => {
      const texts = [...document.querySelectorAll('text')].map(e => ({text:e.textContent, b:e.getBoundingClientRect()}));
      const textOverlaps = [];
      for (let i=0; i<texts.length; i++) for (let j=i+1; j<texts.length; j++) {
        const a=texts[i], b=texts[j];
        if (a.b.left<b.b.right && a.b.right>b.b.left && a.b.top<b.b.bottom && a.b.bottom>b.b.top) textOverlaps.push([a.text,b.text]);
      }
      const leaders = [...document.querySelectorAll('.callout-leader, .label-leader')];
      const leaderTextIntersections=[];
      leaders.forEach((e,i) => {
        const len=e.getTotalLength(), matrix=e.getScreenCTM();
        for (const t of texts) for (let s=3; s<len-3; s+=2) {
          const q=e.getPointAtLength(s), p=new DOMPoint(q.x,q.y).matrixTransform(matrix);
          if (p.x>t.b.left+1 && p.x<t.b.right-1 && p.y>t.b.top+1 && p.y<t.b.bottom-1) {
            leaderTextIntersections.push({leader:i+1,text:t.text}); break;
          }
        }
      });
      return {
        textOverlaps, leaderTextIntersections,
        straightLeaders:leaders.every(e => !/[CQAS]/i.test(e.getAttribute('d'))),
        squareCallouts:[...document.querySelectorAll('.callout-box')].every(e => !e.getAttribute('rx')),
        researchCreditPresent:document.documentElement.textContent.includes('東京大学大学院 渡邉英徳研究室')
      };
    });
    const result={width:width*2,height:height*2,...qa};
    fs.writeFileSync(output.replace(/\.png$/i,'.qa.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify({output,...result}));
    if (qa.textOverlaps.length || qa.leaderTextIntersections.length || !qa.straightLeaders || !qa.squareCallouts) {
      throw new Error('文字や引出線の重なり、または枠形状の問題を検出しました。PNGとQA JSONを確認してください。');
    }
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error.message);process.exitCode=1;});
