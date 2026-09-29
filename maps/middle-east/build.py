import json, math, base64, html, argparse, datetime
from pathlib import Path

D=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description="Generate the map SVG and representative route geometry")
parser.add_argument("--output-dir",type=Path,default=D.parents[1]/"dist")
args=parser.parse_args()
OUT=args.output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
META=json.loads((D/"metadata.json").read_text())
AS_OF=datetime.date.fromisoformat(META["as_of"])
W,H,TOP,BOT=1800,1080,84,140
M=lambda a: math.log(math.tan(math.pi/4+math.radians(a)/2))
m=json.loads((D/'data/base-projection.json').read_text())
(west,south),(east,north)=m['bounds']
def xy(p): return ((p[0]-west)/(east-west)*W,(M(north)-M(p[1]))/(M(north)-M(south))*H)
def path(coords): return 'M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in map(xy,coords))
def screenpath(coords): return 'M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in coords)
svg=[]
def add(s): svg.append(s)
def txt(x,y,t,size=22,color='#eff4f7',weight=500,anchor='start',halo=True,extra=''):
    add(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}" class="{"halo" if halo else ""}" {extra}>{html.escape(t)}</text>')
def geo(lon,lat,t,**kw): txt(*xy([lon,lat]),t,**kw)
def line(coords,color,width=4,dash=None,opacity=1,screen=False,under=True):
    d=screenpath(coords) if screen else path(coords)
    if under:add(f'<path d="{d}" fill="none" stroke="#10202a" stroke-width="{width+3}" opacity="0.85"/>')
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
def arrow(coords,color,at=.7,size=10,screen=False):
    ps=coords if screen else list(map(xy,coords))
    lengths=[math.dist(a,b) for a,b in zip(ps,ps[1:])];target=sum(lengths)*at
    for a,b,l in zip(ps,ps[1:],lengths):
        if target<=l:
            t=target/l;x=a[0]+t*(b[0]-a[0]);y=a[1]+t*(b[1]-a[1]);ang=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]));break
        target-=l
    add(f'<path d="M 0 0 L {-size*1.6} {-size*.72} L {-size*1.25} 0 L {-size*1.6} {size*.72} Z" fill="{color}" transform="translate({x:.2f} {y:.2f}) rotate({ang:.2f})"/>')
def point(p,label,lx,ly,sub=None,kind='port',anchor='start'):
    x,y=xy(p);destx=lx-8 if anchor=='start' else lx+8
    if math.dist((x,y),(destx,ly-7))>30:line([(x,y),(destx,ly-7)],'#d4e0e8',1.1,screen=True,under=False,opacity=.65)
    if kind=='plant':add(f'<rect x="{x-5.5}" y="{y-5.5}" width="11" height="11" rx="1" transform="rotate(45 {x} {y})" fill="#ecf3f7" stroke="#132432" stroke-width="2.5"/>')
    else:add(f'<circle cx="{x}" cy="{y}" r="6.5" fill="#f3f7fa" stroke="#132432" stroke-width="2.5"/>')
    txt(lx,ly,label,22,anchor=anchor)
    if sub:txt(lx,ly+22,sub,15,'#b7c4cc',400,anchor)
def chokepoint(p,label,dx,dy):
    x,y=xy(p);add(f'<circle cx="{x}" cy="{y}" r="17" stroke="#65d9eb" stroke-width="1.5" fill="none" opacity=".8"/>')
    direction=-1 if dx<0 else 1
    # Attach to the near edge of the label, with a clear gap outside the glyphs.
    line([(x+direction*12,y-12),(x+dx-direction*12,y+dy-7)],'#65d9eb',1.2,screen=True,under=False)
    txt(x+dx,y+dy,label,21,'#65d9eb',anchor='end' if dx<0 else 'start')

G='#95e273';R='#ff5576';C='#65d9eb';SH='#c7a6ff'
add(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H+TOP+BOT}" viewBox="0 0 {W} {H+TOP+BOT}" role="img" aria-labelledby="title desc">')
add('<title id="title">中東の原油輸送ルート</title><desc id="desc">公開資料による原油輸送経路の概念図。ヤンブー南航はサウジ関連船への航行制約を示す赤破線で、全船の完全封鎖ではない。海路は実航跡ではなく、稼働・輸送量・個別の日本向け輸送実績を示さない。シャトル船の起点・積替地点は代表位置。LNGなどは対象外。</desc>')
add('<defs><style>text{font-family:"Hiragino Sans","Noto Sans CJK JP","Yu Gothic",sans-serif}.halo{paint-order:stroke;stroke:#13202a;stroke-width:5;stroke-linejoin:round}path{stroke-linecap:round;stroke-linejoin:round}</style><clipPath id="mapclip"><rect width="1800" height="1080"/></clipPath></defs>')
add(f'<rect width="{W}" height="{H+TOP+BOT}" fill="#101c27"/>')
txt(48,41,META['title'],33,weight=600,halo=False)
txt(48,70,'公開資料による主要経路の整理 ｜ 当日の運航・稼働・輸送量を示す図ではありません',17,'#b7cbd9',400,halo=False)
txt(1752,42,f'作成：{AS_OF:%Y.%m.%d}',17,'#aebdc8',400,'end',False)
add(f'<g transform="translate(0 {TOP})" clip-path="url(#mapclip)">')
b64=base64.b64encode((D/'assets/osm-dark-base.png').read_bytes()).decode()
add(f'<image width="1800" height="1080" href="data:image/png;base64,{b64}"/>')

# Country and water labels are separate from the sourced basemap.
for lon,lat,t,size in [(29.3,25.7,'エジプト',24),(44.5,21.8,'サウジアラビア',30),(44.2,31,'イラク',24),(55.4,30,'イラン',27),(58.4,20.8,'オマーン',25),(47,16,'イエメン',25),(29.9,20.0,'スーダン',22),(37.2,15.8,'エリトリア',19),(42.7,11.8,'ジブチ',18),(53.45,22.70,'アラブ首長国連邦',17)]:
    geo(lon,lat,t,size=size,color='#aab4bb',weight=400,anchor='middle')
for lon,lat,t,size,rotate in [(33.8,32.1,'地中海',24,0),(38.1,20.3,'紅海',24,0),(53.3,25.1,'ペルシャ湾',23,0),(61.1,24.9,'オマーン湾',22,0),(59,17.8,'アラビア海',28,0),(47.65,13.8,'アデン湾',21,0)]:
    x,y=xy([lon,lat]);txt(x,y,t,size,C,400,'middle',extra=f'transform="rotate({rotate} {x} {y})"')

features=[]
def feat(name,coords,kind,source,note):
    features.append({'type':'Feature','properties':{'name':name,'category':kind,'source':source,'accuracy':note},'geometry':{'type':'LineString','coordinates':coords}})

crude=json.loads((D/'data/petroline-osm.geojson').read_text())['features'][0]['geometry']['coordinates']
line(crude,G,4.3);arrow(crude,G,.51,10);arrow(crude,G,.83,10)
feat('東西原油パイプライン（Petroline）',crude,'crude_pipeline','https://www.openstreetmap.org/way/54729631 ; https://www.openstreetmap.org/way/1044430260','公開OSM線形。測量精度を保証しない。港湾支線を含まない。')
txt(841,401,'東西原油パイプライン',22,G,500,'middle')

gem=json.loads((D/'data/gem_selected_pipelines.geojson').read_text())['features']
adc=next(f for f in gem if 'Bab-Habshan' in f['properties']['project'])
ac=adc['geometry']['coordinates'][0]+adc['geometry']['coordinates'][2][1:]
line(ac,G,4.3);arrow(ac,G,.61,10)
feat('ハブシャン—フジャイラ原油パイプライン（ADCOP）',ac,'crude_pipeline','Global Energy Monitor, public map dataset 2024-06-12','公開資料に基づく概略線形。')
txt(1270,567,'アブダビ原油パイプライン',21,G,500)
line([xy([54.82,24.28]),(1415,541),(1402,546)],G,1,screen=True,under=False,opacity=.8)

# SUMED uses the vetted route when it becomes available; fallback geometry remains explicit.
sumedfile=D/'data/sumed_onshore_with_gap.geojson'
sf=json.loads(sumedfile.read_text())['features'];sd=[]
for f in sf:
    c=f['geometry']['coordinates'];sd+=c
    line(c,G,4.2,'4 4' if f['properties']['is_interpolated'] else None)
    feat('SUMEDパイプライン'+('（未収録区間の補間）' if f['properties']['is_interpolated'] else ''),c,'crude_pipeline',f['properties']['source'],f['properties']['accuracy'])
arrow(sd,G,.7,10)
txt(75,245,'SUMEDパイプライン',22,G,500)
line([xy([31.23,29.72]),(283,215),(283,225)],G,1,screen=True,under=False)

# Shipping lines are geographical sketches, not observed AIS tracks.
yanbu=[38.235,23.935]
northsea=[yanbu,[37.85,24.05],[37.05,25.1],[36.3,25.9],[35.4,26.7],[34.7,27.35],[34.05,27.85],[33.7,28.15],[33.33,28.7],[32.79,29.25],[32.43,29.55],[32.338333,29.598333]]
line(northsea,R,3.7);arrow(northsea,R,.36,10);arrow(northsea,R,.78,10)
feat('ヤンブー→アイン・スフナ（海上・概略）',northsea,'schematic_shipping','作図用の海域内代表点','概略航路。実航跡・現在の運航を示さない。')
canalfile=D/'data/suez-canal-main.geojson'
if canalfile.exists():
    cc=json.loads(canalfile.read_text())['features'][0]['geometry']['coordinates']
    if cc[0][1]>cc[-1][1]:cc=cc[::-1]
else:
    cc=[[32.572,29.932],[32.566,30.10],[32.508,30.24],[32.39,30.44],[32.326,30.574],[32.346,30.735],[32.31,31.0],[32.31,31.27]]
suez=[[32.43,29.64]]+cc+[[32.34,31.48],[31.8,31.60],[30.85,31.58],[30.0,31.48],[29.30,31.40]]
line(suez,R,3.0);arrow(suez,R,.63,9)
feat('スエズ運河経由→地中海西航（海上・概略）',suez,'schematic_shipping','Suez Canal Authority; OSM; SUMED; cartographic route','運河北上後に地中海西航へ合流する概念線。全船のシディ・ケリル寄港を示さない。SUMED利用・再積載との組合せは船型・喫水等で異なる。')
# Only the westbound Mediterranean segment is within the map extent.
cape=[[29.6824996,31.0510105],[29.60,31.20],[29.30,31.40],[28.70,31.55],[27.80,31.68],[26.60,31.85],[25.22,31.99]]
line(cape,R,3.7);arrow(cape,R,.97,12)
txt(45,30,'喜望峰回り → 日本方面',21,R)
feat('シディ・ケリル→地中海→ジブラルタル→喜望峰回り（表示範囲内のみ）',cape,'schematic_shipping','ユーザー指定の迂回ルート。The National 2026-09-12','地中海西航の一部のみ描画。ジブラルタル・喜望峰は図外。実航跡ではない。')
southsea=[yanbu,[37.98,23.7],[38.1,22.5],[38.75,20.8],[39.6,18.9],[40.5,17.15],[41.5,15.5],[42.4,14.0],[43.08,12.75],[43.25,12.55],[43.7,12.23],[44.3,12.03],[45.4,12.10],[47.3,12.6],[49.6,13.0],[52.4,13.65]]
line(southsea,R,3.7,'12 10');arrow(southsea,R,.20,10);arrow(southsea,R,.48,10);arrow(southsea,R,.985,12)
feat('ヤンブー→バブ・エル・マンデブ→日本方面（航行制約・破線）',southsea,'restricted_schematic_shipping','ユーザー指定の破線。EIA September 2026 STEO; The National 2026-09-12','サウジ関連船への航行制約を示す。全船の一律完全封鎖とは断定しない。実航跡ではない。')
fuj=[[56.358639,25.187944],[56.60,25.22],[57.18,25.10],[58.2,24.87],[59.4,24.20],[60.55,23.53],[61.7,23.20],[63.15,23.12]]
soh=[[56.63,24.511667],[57.0,24.51],[57.55,24.46],[58.2,24.1],[59.4,23.5],[60.6,22.91],[61.7,22.66],[63.15,22.63]]
for name,route in [('フジャイラ→日本方面',fuj),('ソハール→日本方面',soh)]:
    line(route,R,3.7);arrow(route,R,.98,12);feat(name,route,'schematic_shipping','作図用の海域内代表点','日本方面を示す模式的な線。運航実績は未検証。')
# Schematic offshore origin moved close to Ras Tanura, as requested.
shuttle=[[50.33,26.80],[50.75,27.00],[51.5,27.05],[52.5,26.9],[53.6,26.6],[54.6,26.55],[55.5,26.55],[56.1,26.60],[56.45,26.58],[56.70,26.43],[56.77,26.10],[56.75,25.78],[56.70,25.47],[56.64,25.22]]
line(shuttle,SH,3.7);arrow(shuttle,SH,.28,10);arrow(shuttle,SH,.70,10);arrow(shuttle,SH,.985,10)
sx,sy=xy(shuttle[-1]);add(f'<circle cx="{sx}" cy="{sy}" r="5" fill="#0b1c2b" stroke="{SH}" stroke-width="2"/>')
txt(1300,308,'シャトル船（模式）',21,SH)
txt(1240,282,'起点・積替地点は代表位置',15,'#d4c5ee',400)
feat('ラス・タヌラ付近→ホルムズ海峡→フジャイラ沖（シャトル船・模式）',shuttle,'schematic_shuttle','https://www.seatrade-maritime.com/tankers/hormuz-shuttle-tankers-an-evolving-trend-amid-the-iran-war','ユーザー指定により模式線の起点をラス・タヌラ沖付近へ配置。特定港からの運航実績を示すものではない。フジャイラ沖の船間積替を表す概念図で、実航跡・正確な積替地点ではない。')
txt(1735,472,'日本方面へ',24,R,500,'end')
txt(1356,953,'日本方面へ',23,R)

chokepoint([56.45,26.57],'ホルムズ海峡',64,-46)
chokepoint([43.31,12.58],'バブ・エル・マンデブ海峡',-70,-45)
x,y=xy([32.43,30.5]);line([(x,y),(455,110)],C,1.2,screen=True,under=False);txt(465,113,'スエズ運河',22,C)

points=[
 ('シディ・ケリル',[29.6824996,31.0510105],68,152,'SUMED北端・再積込み','port','start'),
 ('アイン・スフナ',[32.3214022,29.6069879],371,219,'SUMED南端・荷揚げ','port','start'),
 ('ヤンブー',[38.2687784,23.9793099],540,561,'紅海側の輸出拠点','port','start'),
 ('ラス・タヌラ',[50.163,26.645],1110,285,'ペルシャ湾側の輸出港','port','end'),
 ('アブカイク',[49.6855348,25.922357],1202,365,'東西原油ライン起点','plant','start'),
 ('ハブシャン',[53.6176,23.8279],1230,500,None,'plant','start'),
 ('フジャイラ',[56.358639,25.187944],1502,384,None,'port','start'),
 ('ソハール',[56.630,24.511667],1496,481,'独立した港湾拠点','port','start')]
for name,p,lx,ly,sub,kind,anchor in points:
    point(p,name,lx,ly,None,kind,anchor)
    features.append({'type':'Feature','properties':{'name':name,'category':kind,'accuracy':'施設・港の代表点。積出しブイや個別設備の正確な位置ではない。'},'geometry':{'type':'Point','coordinates':p}})

# Compact map key placed in unused land area.
add('<rect x="46" y="718" width="431" height="196" rx="8" fill="#122330" opacity=".96" stroke="#3b4b57" stroke-width="1"/>')
txt(68,752,'凡例',20,halo=False)
for y,col,dash,t in [(786,G,None,'原油パイプライン（概略・一部補間）'),(821,R,None,'海上経路（模式）'),(856,R,'12 10','南航に制約（サウジ関連船）'),(891,SH,None,'湾内→湾外の積替輸送（模式）')]:
    line([(70,y-6),(122,y-6)],col,3.4,dash,screen=True,under=False);txt(138,y,t,17,halo=False)

# Geographically honest scale bar, referenced to latitude 23 N.
kmdeg=111.32*math.cos(math.radians(23)); length=500/kmdeg/(east-west)*W
xx,yy=62,1022
for i in range(2):add(f'<rect x="{xx+i*length/2:.2f}" y="{yy}" width="{length/2:.2f}" height="5" fill="{["#d2dbe0","#778894"][i]}"/>')
txt(xx,yy-10,'0',13,'#bac7d0',400,halo=False);txt(xx+length,yy-10,'500 km',13,'#bac7d0',400,'end',False)
add('<path d="M 1739 59 L 1731 89 L 1739 83 L 1747 89 Z" fill="#b7cbd8"/>');txt(1739,45,'N',16,'#b7cbd8',500,'middle',False)
add('</g>')

fy=TOP+H
add(f'<path d="M 0 {fy} H 1800" stroke="#40515d"/>')
txt(48,fy+29,'海路は模式線。実線も安全な通航を示さず、「日本方面」は方向のみで、個別貨物の仕向地を確認したものではありません。',18,'#c4d2dc',400,halo=False)
txt(48,fy+58,'赤破線は全船の完全封鎖を意味しません。紫線はラス・タヌラ発の実績を示すものではなく、ホルムズ海峡を通過します。',18,'#c4d2dc',400,halo=False)
txt(48,fy+87,'対象は原油の主要経路。LNG・LPG・石油製品などを網羅していません。',18,'#c4d2dc',400,halo=False)
add(f'<a href="https://www.openstreetmap.org/copyright">')
txt(48,fy+122,'© OpenStreetMap contributors  ·  OpenFreeMap / © OpenMapTiles',14,'#9dafbb',400,halo=False)
add('</a>')
txt(1752,fy+122,'資料：OSM・GEM・Aramco・ADNOC・SUMED・EIA・S&P Global・Seatrade Maritime',13,'#9dafbb',400,'end',False)
add('</svg>')
(OUT/'middle-east.svg').write_text('\n'.join(svg))
(OUT/'middle-east.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,indent=2))
print('Wrote SVG and feature collection')
