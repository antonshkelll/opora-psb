import json, pathlib, zipfile, hashlib
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit

root=pathlib.Path(__file__).parent; out=root/'output';out.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold',r'C:\Windows\Fonts\arialbd.ttf'))
slides=json.loads((root/'docs/slides.json').read_text(encoding='utf-8'))
c=canvas.Canvas(str(out/'opora-presentation-v5.pdf'),pagesize=(1280,720))
c.setTitle('ОПОРА: VIBESECURITY / Hack&Change 2026');c.setAuthor('VIBESECURITY')
def text(t,x,y,size,color,font='Arial',width=1120,leading=None):
    c.setFont(font,size);c.setFillColor(HexColor(color));leading=leading or size*1.35
    for paragraph in t.split('\n'):
        if not paragraph:y-=leading*.45;continue
        for line in simpleSplit(paragraph,font,size,width):
            c.drawString(x,y,line);y-=leading
    return y
for i,s in enumerate(slides):
    dark=i==0;c.setFillColor(HexColor('#292459' if dark else '#f5f5f8'));c.rect(0,0,1280,720,fill=1,stroke=0)
    if s.get('image') and (root/s['image']).exists():
        text(s['title'],72,650,37,'#292459','ArialBold')
        c.drawImage(str(root/s['image']),72,90,width=1136,height=520,preserveAspectRatio=True,anchor='c')
        text(s['foot'],75,45,12,'#637080',width=1100,leading=17)
        c.showPage();continue
    text(s['title'],72,580 if dark else 610,90 if dark else 44,'#ffffff' if dark else '#292459','ArialBold')
    text(s['subtitle'],75,480,28,'#f8aaa3' if dark else '#f05a24',width=1120)
    text(s['body'],75,395,24,'#ffffff' if dark else '#292459',leading=31)
    if s.get('diagram'):
        for j,node in enumerate(s['diagram']):
            x=75+j*228;c.setFillColor(HexColor('#ffffff'));c.setStrokeColor(HexColor('#d8d6e5'));c.roundRect(x,150,200,48,8,fill=1,stroke=1);c.setFillColor(HexColor('#292459'));c.setFont('ArialBold',15);c.drawCentredString(x+100,168,node)
            if j<4:c.setFont('Arial',21);c.drawString(x+205,166,'>')
    text(s['foot'],75,94,15,'#d9dcd9' if dark else '#637080',width=1100,leading=21)
    if i==0:
        c.linkURL('https://github.com/antonshkelll/opora-psb',(70,85,1200,110),relative=0,thickness=0)
        c.linkURL('https://antonshkelll.github.io/opora-psb/',(70,64,1200,85),relative=0,thickness=0)
    c.showPage()
c.save()
(root/'web/presentation.pdf').write_bytes((out/'opora-presentation-v5.pdf').read_bytes())
with zipfile.ZipFile(out/'opora-submit-v5.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ['solution.py','core.py','engine_v5.py','requirements.txt']:z.write(root/name,name)
with zipfile.ZipFile(out/'opora-final-v5.zip','w',zipfile.ZIP_DEFLATED) as z:
    files=['core.py','engine_v5.py','solution.py','server.py','requirements.txt','fetch_materials.py','evaluate.py','Dockerfile','compose.yaml','.dockerignore','.env.example','README.md','web/index.html','data/knowledge-base.zip','data/demo_questions.csv','data/demo_output.csv','data/allowed_requirements.txt','output/opora-presentation-v5.pdf']
    files+=['output/opora-control-v4.zip']
    files+=['docs/'+p.name for p in (root/'docs').iterdir() if p.is_file()]
    files+=['tests/'+p.name for p in (root/'tests').glob('test_*.py')]
    files+=['build_deliverables.py','update_assets_v5.py','benchmark_v5.py']
    files += ['web/'+p.name for p in (root/'web').iterdir() if p.is_file() and p.name!='index.html']
    for name in files:z.write(root/name,name)
for name in ['opora-submit-v5.zip','opora-final-v5.zip','opora-presentation-v5.pdf']:
    p=out/name;print(name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
