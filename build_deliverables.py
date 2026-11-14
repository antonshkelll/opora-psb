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
c=canvas.Canvas(str(out/'opora-presentation-v2.pdf'),pagesize=(1280,720))
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
    text(s['foot'],75,94,15,'#d9dcd9' if dark else '#637080',width=1100,leading=21)
    c.linkURL('https://github.com/antonshkelll/opora-psb',(70,20,1150,85),relative=0,thickness=0)
    c.showPage()
c.save()
(root/'web/presentation.pdf').write_bytes((out/'opora-presentation-v2.pdf').read_bytes())
with zipfile.ZipFile(out/'opora-submit-v2.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ['solution.py','core.py','engine_v2.py','requirements.txt']:z.write(root/name,name)
with zipfile.ZipFile(out/'opora-final-v2.zip','w',zipfile.ZIP_DEFLATED) as z:
    files=['core.py','engine_v2.py','solution.py','server.py','requirements.txt','fetch_materials.py','evaluate.py','benchmark_v2.py','Dockerfile','compose.yaml','.dockerignore','.env.example','README.md','web/index.html','data/knowledge-base.zip','data/demo_questions.csv','data/demo_output.csv','data/allowed_requirements.txt','output/opora-presentation-v2.pdf']
    files+=['docs/'+p.name for p in (root/'docs').iterdir() if p.is_file()]
    files+=['tests/'+p.name for p in (root/'tests').glob('test_*.py')]
    files+=['build_showcase.py','verify_local.py','build_deliverables.py','refresh_materials.py','finalize_report.py']
    files += ['web/'+p.name for p in (root/'web').iterdir() if p.is_file() and p.name!='index.html']
    for name in files:z.write(root/name,name)
for name in ['opora-submit-v2.zip','opora-final-v2.zip','opora-presentation-v2.pdf']:
    p=out/name;print(name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
