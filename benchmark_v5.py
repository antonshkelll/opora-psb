"""Fresh local development run. Not a private judge score."""
import pathlib,json,csv,time,sys,hashlib
from core import Corpus,Gateway
from engine_v5 import Assistant
r=pathlib.Path(__file__).parent
class Capture:
    def __init__(self,g):self.g=g;self.outputs=[]
    def __getattr__(self,k):return getattr(self.g,k)
    def chat(self,*args):
        raw=self.g.chat(*args);self.outputs.append(raw);return raw
g=Capture(Gateway());bot=Assistant(Corpus(r/'data'),g)
with (r/'data/demo_questions.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
ids=set(sys.argv[1:] or ['1','3','5','10','13','17'])
report={'model':g.model,'provider':g.provider,'engine_sha256':hashlib.sha256((r/'engine_v5.py').read_bytes()).hexdigest(),'note':'Fresh public development cases, not independent accuracy or DeepSeek score. Deterministic cases have zero calls.','cases':[]}
if len(sys.argv)>1 and (r/'docs/v5-local-run.json').exists():
    previous=json.loads((r/'docs/v5-local-run.json').read_text(encoding='utf-8'));report['cases']=[c for c in previous['cases'] if c['id'] not in ids]
for row in rows:
    if row['id'] not in ids:continue
    print('RUN',row['id'],flush=True);g.outputs=[];v=bot.answer(row['question'],time.monotonic()+480)
    report['cases'].append({'id':row['id'],'question':row['question'],**v,'raw_model_outputs':g.outputs})
    (r/'docs/v5-local-run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(row['id'],v['status'],v['answer'],v['diagnostics'],flush=True)
