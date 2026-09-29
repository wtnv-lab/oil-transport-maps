import base64, html, json, math, argparse, datetime
from pathlib import Path

D=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description="Generate the map SVG and representative route geometry")
parser.add_argument("--output-dir",type=Path,default=D.parents[1]/"dist")
args=parser.parse_args()
OUT=args.output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
META=json.loads((D/"metadata.json").read_text())
AS_OF=datetime.date.fromisoformat(META["as_of"])
W,MH,TOP,H=2400,1120,145,1365
COL={'1':'#70e49d','2':'#ff727b','3':'#ffbd62','4':'#d19bff','5':'#4edce7','6':'#70aaff','S':'#e6dcae','common':'#dce7ee'}
M=lambda lat:math.log(math.tan(math.pi/4+math.radians(lat)/2))
def xy(p):
    lon,lat=p
    while lon < -55: lon+=360
    while lon > 305: lon-=360
    return ((lon+55)/360*W,TOP+MH/2+(M(18)-M(lat))*W/(2*math.pi))
svg=[]
def add(s):svg.append(s)
def text(x,y,s,size=22,color='#eef4f8',weight=500,anchor='start',halo=True):
    add(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}"'+(' class="halo"' if halo else '')+'>'+html.escape(s)+'</text>')
def path(ps):return 'M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in ps)
def line(ps,color,width=4,dash=None,under=True,opacity=1):
    d=path(ps)
    if under:add(f'<path d="{d}" fill="none" stroke="#071925" stroke-width="{width+4}" opacity=".9"/>')
    add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" opacity="{opacity}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
def arrow(ps,col,at=.6,size=8):
    lens=[math.dist(a,b) for a,b in zip(ps,ps[1:])]; target=sum(lens)*at
    for a,b,l in zip(ps,ps[1:],lens):
        if target<=l:
            t=target/l;x=a[0]+t*(b[0]-a[0]);y=a[1]+t*(b[1]-a[1]);ang=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]));break
        target-=l
    for offset in (-W,0,W):
        if 12<x+offset<W-12:
            add(f'<path class="route-arrow" d="M 0 0 L {-size*1.75} {-size*.62} L {-size*1.75} {size*.62} Z" fill="{col}" transform="translate({x+offset:.2f} {y:.2f}) rotate({ang:.2f})"/>')
def smooth(ps,start_dir=None,end_dir=None):
    """Bounded Hermite curves through the sea waypoints, with common tangents.

    Short coastal segments have small handles. Long offshore segments receive
    longer handles, keeping the curve smooth without turning coastal shortcuts
    into new routes. The continuous world path is clipped only after smoothing.
    """
    ps=[p for i,p in enumerate(ps) if i==0 or math.dist(p,ps[i-1])>.01]
    tang=[]
    for i,p in enumerate(ps):
        a=ps[max(i-1,0)];b=ps[min(i+1,len(ps)-1)]
        dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy)
        tang.append((dx/l,dy/l))
    if start_dir:tang[0]=start_dir
    if end_dir:tang[-1]=end_dir
    d=f'M {ps[0][0]:.3f},{ps[0][1]:.3f}'
    samples=[ps[0]]
    for i,(p,q) in enumerate(zip(ps,ps[1:])):
        dist=math.dist(p,q)
        a=min(dist,math.dist(ps[i-1],p) if i else dist)*.29
        b=min(dist,math.dist(q,ps[i+2]) if i+2<len(ps) else dist)*.29
        c1=(p[0]+tang[i][0]*a,p[1]+tang[i][1]*a)
        c2=(q[0]-tang[i+1][0]*b,q[1]-tang[i+1][1]*b)
        d+=f' C {c1[0]:.3f},{c1[1]:.3f} {c2[0]:.3f},{c2[1]:.3f} {q[0]:.3f},{q[1]:.3f}'
        steps=max(8,math.ceil(dist/1.5))
        for j in range(1,steps+1):
            t=j/steps;u=1-t
            samples.append(tuple(u*u*u*p[k]+3*u*u*t*c1[k]+3*u*t*t*c2[k]+t*t*t*q[k] for k in (0,1)))
    return d,samples
features=[]
route_samples={}
def route(name,coords,key,dash=None,width=4.6,arrows=(.58,),wrapped=False,start_dir=None,end_dir=None):
    ps=[]
    for xx,yy in map(xy,coords):
        if ps:
            while xx-ps[-1][0]>W/2:xx-=W
            while xx-ps[-1][0]<-W/2:xx+=W
        ps.append((xx,yy))
    d,samples=smooth(ps,start_dir,end_dir)
    width=min(width,3.5)
    for offset in (-W,0,W):
        if max(x for x,y in samples)+offset<0 or min(x for x,y in samples)+offset>W:continue
        add(f'<path class="sea-route" d="{d}" transform="translate({offset} 0)" fill="none" stroke="{COL[key]}" stroke-width="{width}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')
        route_samples.setdefault(key,[]).extend([(x+offset,y) for x,y in samples if -10<x+offset<W+10])
    for at in arrows:arrow(samples,COL[key],at)
    features.append({'type':'Feature','properties':{'name':name,'route':key,'geometry_note':'公表された経由地を結ぶ模式航路。AIS航跡ではない。'},'geometry':{'type':'LineString','coordinates':coords}})
    return ps
def dot(p,label=None,at=None,color='#f5f8fa',size=5.4,anchor='start',font=21):
    x,y=xy(p)
    add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size}" fill="{color}" stroke="#0b1c2b" stroke-width="2.5"/>')
    if label and at:
        tx,ty=at
        end=(tx-9 if anchor=='start' else tx+9,ty-7)
        if math.dist((x,y),end)>34:line([(x,y),end],'#aebdca',1.15,under=False)
        text(tx,ty,label,font,anchor=anchor)
def badge(x,y,s,key,r=16):
    text(x,y+6,s,20,COL[key],500,'middle')
def bubble(x,y,w,title,key,rows,tail,status=None):
    # A single straight leader meets the actual smoothed route; no arrowhead.
    start,end=tail[0],tail[-1]
    if key in route_samples:end=min(route_samples[key],key=lambda p:math.dist(p,end))
    add(f'<path class="callout-leader" d="{path([start,end])}" fill="none" stroke="#a7b4bd" stroke-width="1.1" opacity=".8"/>')
    # Keep the footprint while redistributing surplus bottom padding into
    # the status/body gaps. Two 21px body rows now have a 36px baseline pitch.
    height=96+max(0,len(rows)-1)*36+(36 if status else 0)
    add(f'<rect class="callout-box" x="{x}" y="{y}" width="{w}" height="{height}" fill="#111e27" fill-opacity=".97" stroke="#71808b" stroke-opacity=".7" stroke-width=".9"/>')
    text(x+21,y+38,key,23,COL[key],500,halo=False)
    text(x+55,y+38,title,24,'#e5ebef',500,halo=False)
    yy=y+78
    if status:
        text(x+21,yy,status,19,'#aebecb',400,halo=False);yy+=36
    for row in rows:
        text(x+21,yy,row,21,'#dce5ec',400,halo=False);yy+=36
    return height

add(f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add('<defs><style>text{font-family:"Hiragino Kaku Gothic ProN","Hiragino Sans","Noto Sans CJK JP",sans-serif}.halo{paint-order:stroke;stroke:#0b1c2b;stroke-width:3px;stroke-linejoin:round}path{stroke-linecap:round;stroke-linejoin:round}</style><clipPath id="map"><rect y="145" width="2400" height="1120"/></clipPath></defs>')
add(f'<rect width="{W}" height="{H}" fill="#0b1721"/>')
text(48,62,META['title'],39,weight=600,halo=False)
text(48,111,'中東・北米の主な経路と輸送コスト・リスク',22,'#b8c9d7',400,halo=False)
text(2352,59,f'{AS_OF.year}年{AS_OF.month}月{AS_OF.day}日 再検証',23,'#d4dfe7',400,'end',False)
text(2352,104,'公開情報による模式図  ｜  線の太さは輸送量を示さない',19,'#a5bacb',400,'end',False)
img=base64.b64encode((D/'assets/osm-dark-world.png').read_bytes()).decode()
add(f'<image x="0" y="{TOP}" width="2400" height="1120" href="data:image/png;base64,{img}"/>')
add('<g clip-path="url(#map)">')

# Geographic routes: representative waypoints around coastlines and chokepoints.
yanbu=[38.2,24.0];sidi=[29.7,31.1];fuj=[56.4,25.2];japan=[139.7,35.1];us=[-94.1,28.5];cape=[18,-38]
malacca=[103.65,1.2]
med=[yanbu,[37.7,24.1],[36.4,25.5],[34.8,27.2],[33.4,28],[32.4,29.6],sidi,[28.6,32],[26,33],[21,34.2],[16,34.6],[12,36.4],[11.5,37],[11,37.4],[10,38],[2,37],[-5.6,35.9],[-10,34],[-16,25],[-19,13],[-15,-3],[-4,-21],[8,-33],cape]
route('ヤンブー → SUMED → 地中海 → 喜望峰',med,'3',arrows=(.38,.77),end_dir=(1,0))
# Suez is an alternative to the SUMED land crossing; narrow at world-map scale.
route('スエズ運河経由の代替接続',[[32.4,29.6],[32.55,29.9],[32.57,30.7],[32.31,31.27],[31.2,31.6],[28.6,32]],'3',width=2.6,arrows=())
cape_us=[us,[-89,26.8],[-85,24.3],[-81,23.7],[-78,26],[-72,27],[-60,21],[-48,10],[-31,-7],[-15,-23],[0,-35],cape]
route('米湾岸 → 大西洋 → 喜望峰',cape_us,'4',arrows=(.29,.77),wrapped=True,end_dir=(1,0))
common_cape=[cape,[27,-37],[40,-33],[56,-22],[68,-10],[82,0],[92,5.5],[96,5.7],[99,4.8],[101,3],[103.65,1.2]]
route('喜望峰 → インド洋 → マラッカ海峡',common_cape,'common',width=4.5,arrows=(.44,),start_dir=(1,0),end_dir=(1,0))
oman=[fuj,[57.2,25.3],[59.5,23.8],[61.5,21],[65,16],[72,9],[79,5.2],[86,5],[92,5.5],[96,5.7],[99,4.8],[101,3],malacca]
route('オマーン湾側 → マラッカ海峡',oman,'1',arrows=(.47,),end_dir=(1,0))
gulf=[[50.33,26.8],[51.5,27.05],[53.6,26.6],[55.5,26.55],[56.1,26.6],[56.45,26.58],[56.7,26.43],[56.77,26.1],[56.75,25.78],[57.2,25.3]]
route('湾内発 → ホルムズ海峡 → アジア方面（直航・積替えの共通区間）',gulf,'1',width=2.7,arrows=())
route('フジャイラ沖の積替え接続（模式）',[[56.75,25.78],[56.6,25.3],fuj],'1',dash='3 5',width=2.7,arrows=())
route('ソハール沖の積替え接続（模式）',[[56.75,25.78],[57.0,25.2],[57.0,24.7],[58.0,24.4],[59.5,23.8]],'1',dash='3 5',width=2.7,arrows=())
south=[yanbu,[37.7,23.8],[38.4,21.9],[39.8,19.1],[41.15,16.4],[42.7,14.3],[43.4,12.6],[45.5,12],[50.4,13.4],[54,12.9],[61,9],[68,6],[78,4.1],[86,5]]
route('ヤンブー → バブ・エル・マンデブ → 日本方面（航行制約）',south,'2',dash='10 8',width=4.3,arrows=(.50,),end_dir=(1,0))
asian=[malacca,[104.6,1.1],[106,2.5],[110,8],[115,15],[120,20],[122,21.4],[126,26],[130,29],[134,31.3],[138.8,34.1],japan]
route('中東・喜望峰方面の日本向け共通区間',asian,'common',width=5,arrows=(.63,),start_dir=(1,0))
panama=[us,[-91,26],[-86,23],[-85.5,21.5],[-83.5,18],[-80,12],[-79.92,9.36],[-79.7,9.1],[-79.57,8.95],[-80,7],[-83,6],[-92,9],[-104,14],[-117,22],[-135,30],[-156,35],[-177,36],[165,35],[152,34.5],[143,34.5],[141,34.3],[140,34.6],[139.85,34.85],japan]
route('米湾岸 → パナマ運河 → 太平洋 → 日本',panama,'5',arrows=(.52,.78))
canada=[[-123.1,49.3],[-123.45,49.2],[-123.5,48.7],[-123.3,48.3],[-124.7,48.3],[-126,48],[-133,46.5],[-147,46],[-163,45],[-179,43],[166,40],[153,37],[144,35.6],[141,34.3],[140,34.6],[139.85,34.85],japan]
route('カナダ西岸 → 北太平洋 → 日本',canada,'6',arrows=(.39,.70))

# Quiet geographic labels, all horizontal.
for lon,lat,label in [(15,10,'アフリカ'),(262,43,'北アメリカ'),(287,-19,'南アメリカ')]:
    text(*xy((lon,lat)),label,26,'#8b9eab',500,'middle')
for lon,lat,label in [(73,-17,'インド洋'),(185,23,'太平洋'),(-28,21,'大西洋')]:
    text(*xy((lon,lat)),label,26,'#587c95',500,'middle')
dot(japan,'日本',(1314,537),size=9,anchor='start',font=29)
dot(us,'米国メキシコ湾岸',(2110,594),anchor='end',font=22)
dot(canada[0],'バンクーバー',(2020,434),font=22)
dot(yanbu,'ヤンブー',(581,690),anchor='end',font=21)
dot(sidi,'シディ・ケリル',(546,548),anchor='end',font=20)
dot(fuj,'フジャイラ／ソハール',(802,646),font=20)
dot([-79.8,9.15],'パナマ運河',(2270,795),font=20)
dot([20,-34.8],'喜望峰周辺',(540,1008),anchor='start',font=20)
dot([43.4,12.6],'バブ・エル・マンデブ海峡',(630,792),anchor='end',font=18)
dot([56.3,26.45],'ホルムズ海峡',(785,595),font=19)
dot([-5.6,35.9],'ジブラルタル海峡',(303,539),anchor='end',font=19)
text(609,631,'紅海',18,'#86b7d1',500,'middle')
text(682,605,'ペルシャ湾',18,'#86b7d1',500,'middle')
text(1105,822,'マラッカ海峡',20,'#a7c2d5')

# Optional transshipment hubs: not mandatory waypoints for every cargo.
for p in [[56.7,25.1],[101.95,2.4]]:
    x,y=xy(p);add(f'<circle cx="{x}" cy="{y}" r="10" fill="none" stroke="{COL["S"]}" stroke-width="2"/>')
dot([101.95,2.4],'リンギ沖',(1042,858),anchor='end',font=19)

# Route identifiers beside visible segments.
for x,y,key in [(891,762,'1'),(753,795,'2'),(318,719,'3'),(240,991,'4'),(1835,646,'5'),(1710,509,'6')]:badge(x,y,key,key)
text(712,1085,'3・4  喜望峰から日本へ',21,'#c1ced7',400)
text(1211,717,'1–4',20,'#c1ced7',400)

# Six route balloons plus one concise STS balloon.
bubble(40,193,520,'地中海・喜望峰経由','3',[
    'コスト：紅海南下比で航海が３週間以上増',
    'リスク：設備への再攻撃・積替え接続の遅れ'],
    [(540,361),xy([29.7,31.1])],
    'ヤンブー発／9/28 再開報道・全面復旧は未確認')
bubble(628,198,578,'中東からインド洋経由','1',[
    'コスト：保険・船腹。積替え便は追加費用',
    'リスク：攻撃・混雑。湾内発はホルムズ通過'],
    [(668,366),xy([57.2,25.3])],
    '湾外積み＋湾内発の直航・STS／9月の通航回復')
bubble(1452,192,548,'カナダ西岸・太平洋経由','6',[
    'コスト：直航で運河料・洋上積替費を回避',
    'リスク：積出量・船型制約、油種の適合'],
    [(1806,360),xy([-137,46.35])],
    'Aframax級で直航／8月に日本着の実績')
bubble(752,388,536,'紅海南下','2',[
    'コスト：短距離だが保険・通航条件が不安定',
    'リスク：フーシ派の攻撃・拿捕'],
    [(1220,556),xy([74,4.86])],
    'ヤンブー発／大型原油船の回避・全船閉鎖ではない')
bubble(1550,757,548,'米湾岸・パナマ経由','5',[
    'コスト：運河・予約料金、積載量の制約',
    'リスク：予約待ち・水位変動／VLCCは不可'],
    [(2018,757),xy([-103,13.6])],
    '9/28 喫水制限緩和／10/15 通航枠増の予定')
bubble(1778,1045,574,'米湾岸・喜望峰経由','4',[
    'コスト：長距離で燃料・用船日数が増加',
    'リスク：船腹不足、荒天・納期の長期化'],
    [(2352,1095),xy([-56,17.3])],
    'VLCC（大型原油タンカー）の主な代替経路')
bubble(1136,997,574,'洋上積替え（STS）','S',[
    'コスト：積替え・待機・接続船の費用',
    'リスク：荷役混雑、天候による作業中断'],
    [(1161,997),xy([101.95,2.4])],
    '湾外・マレーシアの代表拠点／全便共通ではない')

# Unobtrusive map key in otherwise open southern Indian Ocean.
line([(65,1172),(135,1172)],'#dce7ee',4.5,under=False);text(152,1180,'海上経路（模式）',19,'#cbd8e2',halo=False)
line([(65,1210),(135,1210)],COL['2'],4.5,'11 10',under=False);text(152,1218,'航行制約・回避',19,'#cbd8e2',halo=False)
line([(482,1172),(552,1172)],COL['1'],3.4,'3 5',under=False);text(568,1180,'湾外での積替え接続',19,'#cbd8e2',halo=False)
add(f'<circle cx="494" cy="1210" r="9" fill="none" stroke="{COL["S"]}" stroke-width="2"/>');text(518,1218,'STS拠点',19,'#cbd8e2',halo=False)
text(912,1218,'白線：複数ルートの共通区間',18,'#a7bdcd',anchor='end',halo=False)
add('</g>')
add('<path d="M 0 1265 H 2400" stroke="#354a59" stroke-width="1"/>')
text(48,1300,'コストは費用の要因で、同条件の運賃比較ではありません。実線も当日の運航や安全を示しません。',18,'#b5c5d1',400,halo=False)
text(2352,1300,'作図：'+META['credit'],20,'#d5dfe5',400,'end',False)
text(48,1338,'© OpenStreetMap contributors  ·  OpenFreeMap / © OpenMapTiles',16,'#91a8ba',halo=False)
text(2352,1338,'資料：Bloomberg・Reuters・S&P Global・Kpler・Baltic Exchange・パナマ運河庁ほか',16,'#91a8ba',anchor='end',halo=False)
add('</svg>')
(OUT/'global.svg').write_text('\n'.join(svg))
(OUT/'global.geojson').write_text(json.dumps({'type':'FeatureCollection','as_of':META['as_of'],'revalidated_at':META.get('revalidated_at'),'source_notes':'docs/global-sources-and-costs.md','features':features},ensure_ascii=False,indent=2))
print('Wrote map SVG and route geometry')
