/** 拡大図の接線方向の矢印・PNG・1440px表示例を生成し、文字配置を検査する。 */
const fs=require('node:fs');
const path=require('node:path');
const {launchBrowser}=require('../../scripts/browser.cjs');
const root=path.resolve(__dirname,'../..');
async function main(){
 const stem=path.resolve(process.argv[2] || path.join(root,'dist/gulf-hormuz-oman'));
 const design=JSON.parse(fs.readFileSync(stem+'.design.json','utf8'));
 const svg=fs.readFileSync(stem+'.svg','utf8');
 const width=Number(svg.match(/<svg[^>]*width="(\d+)"/)[1]);
 const height=Number(svg.match(/<svg[^>]*height="(\d+)"/)[1]);
 const html=s=>`<html><style>html,body{margin:0;background:${design.colors.frame}}svg{display:block}</style>${s}</html>`;
 const browser=await launchBrowser();
 try{
  const ctx=await browser.newContext({viewport:{width,height},deviceScaleFactor:design.preview.raster_scale,offline:true});
  const page=await ctx.newPage();await page.setContent(html(svg));await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(design=>{
   document.querySelectorAll('.generated-arrow').forEach(e=>e.remove());
   const clip=document.querySelector('#mapclip rect');
   const top=Number(clip.getAttribute('y')),bottom=top+Number(clip.getAttribute('height')),right=Number(clip.getAttribute('width'));
   for(const p of document.querySelectorAll('path.route,path.legend-route')){
    const total=p.getTotalLength();let visible=total;
    for(let d=0;d<=total;d+=2){const q=p.getPointAtLength(d);if(q.x<0||q.x>right||q.y<top||q.y>bottom){visible=d;break;}}
    const size=Math.min(Number(p.dataset.arrowSize),visible/9);
    const gap=Math.min(design.lines.paired_arrow_gap,visible*.2);
    const center=visible*.5;
    const positions=p.classList.contains('pair')?[[center-gap,true],[center+gap,false]]:[[center,false]];
    for(const [d,reverse] of positions){
     const c=p.getPointAtLength(d),a=p.getPointAtLength(Math.max(0,d-1)),b=p.getPointAtLength(Math.min(total,d+1));
     const arrow=document.createElementNS('http://www.w3.org/2000/svg','path');
     const s=design.symbols;
     arrow.setAttribute('d',`M 0 0 L ${-size*s.arrow_length_factor} ${-size*s.arrow_half_width_factor} L ${-size*s.arrow_notch_factor} 0 L ${-size*s.arrow_length_factor} ${size*s.arrow_half_width_factor} Z`);
     arrow.setAttribute('fill',p.getAttribute('stroke'));
     arrow.setAttribute('transform',`translate(${c.x} ${c.y}) rotate(${Math.atan2(b.y-a.y,b.x-a.x)*180/Math.PI+(reverse?180:0)})`);
     arrow.setAttribute('class','generated-arrow');p.after(arrow);
    }
   }
  },design);
  const qa=await page.evaluate(({width,height})=>{
   const texts=[...document.querySelectorAll('text')].map(el=>({el,text:el.textContent,box:el.getBoundingClientRect()}));
   const textOverlaps=[];
   for(let i=0;i<texts.length;i++)for(let j=i+1;j<texts.length;j++){
    const a=texts[i].box,b=texts[j].box;
    if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)textOverlaps.push([texts[i].text,texts[j].text]);
   }
   const leaderTextIntersections=[];
   for(const p of document.querySelectorAll('.label-leader')){
    const length=p.getTotalLength(),m=p.getScreenCTM();
    const hits=new Set();
    for(let d=1;d<length;d++){
     const q=p.getPointAtLength(d),s=new DOMPoint(q.x,q.y).matrixTransform(m);
     for(const t of texts){const b=t.box;if(s.x>b.left+1&&s.x<b.right-1&&s.y>b.top+1&&s.y<b.bottom-1)hits.add(t.text);}
    }
    leaderTextIntersections.push(...hits);
   }
   const panelTextOcclusions=[];
   for(const panel of document.querySelectorAll('.callout-box,.legend-box')){
    const a=panel.getBoundingClientRect();
    for(const t of texts){
     if(!(t.el.compareDocumentPosition(panel)&Node.DOCUMENT_POSITION_FOLLOWING))continue;
     const b=t.box;
     if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)panelTextOcclusions.push(t.text);
    }
   }
   return {textOverlaps,leaderTextIntersections,panelTextOcclusions,outsideCanvas:texts.filter(t=>t.box.left<0||t.box.right>width||t.box.top<0||t.box.bottom>height).map(t=>t.text),textCount:texts.length};
  },{width,height});
  const finalSvg=await page.locator('svg').evaluate(el=>el.outerHTML);
  fs.writeFileSync(stem+'.svg',finalSvg);fs.writeFileSync(stem+'.qa.json',JSON.stringify(qa,null,2));
  await page.screenshot({path:stem+'.png'});
  const pw=design.preview.desktop_width,ph=Math.ceil(height*pw/width);
  const pctx=await browser.newContext({viewport:{width:pw,height:ph},deviceScaleFactor:1,offline:true});
  const preview=await pctx.newPage();await preview.setContent(html(finalSvg).replace('</style>',`svg{width:${pw}px;height:auto}</style>`));
  await preview.evaluate(()=>document.fonts.ready);await preview.screenshot({path:stem+'-pc1440.png'});
  console.log(JSON.stringify(qa));
  if([qa.textOverlaps,qa.leaderTextIntersections,qa.panelTextOcclusions,qa.outsideCanvas].some(a=>a.length))process.exitCode=1;
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1});
