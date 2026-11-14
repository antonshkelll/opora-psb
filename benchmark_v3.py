"""Real V3 smoke evaluation. Never estimates private judge score."""
import json,time,pathlib,os
from core import Corpus,Gateway
from engine_v3 import LegalAssistant
root=pathlib.Path(__file__).parent
bot=LegalAssistant(Corpus(root/'data'),Gateway())
report={'pipeline':'v3','model':bot.gateway.model,'provider':bot.gateway.provider,'note':'Real smoke test only, not private score or independent accuracy.','cases':[]}
class Capture:
    def __init__(self,g):self.g=g;self.outputs=[]
    def __getattr__(self,k):return getattr(self.g,k)
    def chat(self,*args):
        raw=self.g.chat(*args);self.outputs.append(raw);return raw
bot.gateway=Capture(bot.gateway)
cases=[('rent','Какая плата по договору аренды А-08/2024 Северный Склад и до какого числа?'),('archive','Можно взять оригинал договора из архива на четыре рабочих дня?')]
if len(__import__('sys').argv)>1:cases=[x for x in cases if x[0] in __import__('sys').argv[1:]]
previous=root/'docs/v3-real-smoke.json'
if previous.exists() and len(cases)<2:report['cases']=[x for x in json.loads(previous.read_text(encoding='utf-8'))['cases'] if x['id'] not in {x[0] for x in cases}]
for key,q in cases:
    print('RUN',key,flush=True);r=bot.answer(q,time.monotonic()+600)
    report['cases'].append({'id':key,'question':q,**r,'raw_model_outputs':bot.gateway.outputs[:]});bot.gateway.outputs=[]
    (root/'docs/v3-real-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(key,r['status'],r['answer'],r['diagnostics'],flush=True)
