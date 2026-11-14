"""Replay recorded model selections through the final deterministic renderer.

No new model answers are invented here. Keep the measured answer, model decision,
latency and code digest, and label the rendering replay explicitly.
"""
import hashlib,json,pathlib,re
from core import Corpus
from engine_v2 import GroundedAssistant
from benchmark_v2 import RUBRICS,EXPECTED

class Recorded:
    provider='ollama';configured=True
    def __init__(self,decision):self.decision=decision
    def chat(self,*args):return json.dumps(self.decision,ensure_ascii=False)

path=pathlib.Path('docs/v2-real-demo-report.json');report=json.loads(path.read_text(encoding='utf-8'))
assert len(report['cases'])==18,'Complete all measurements first'
corpus=Corpus()
prefixes={'Да,':'yes','Нет,':'no','Предпосылка':'correction','Ответ зависит':'depends'}
for row in report['cases']:
    original=row.get('measured_answer',row['answer'])
    row.setdefault('measured_answer',original)
    diag=row['diagnostics']
    decision=diag.get('decision')
    if decision is None:
        decision={'status':row['status'],'verdict':next((v for p,v in prefixes.items() if original.startswith(p)),'facts'),'selected':diag['selected_paragraphs'],'reason':'missing_rule' if 'не найдено положения' in original else 'none'}
        row['decision_reconstruction']='Enums and IDs recovered from measured answer and diagnostics; no source selection changed.'
    result=GroundedAssistant(corpus,Recorded(decision)).answer(row['question'])
    assert result['status']!='unavailable',(row['id'],result.get('missing'))
    row['answer']=result['answer'];row['status']=result['status']
    row['diagnostics']['selected_paragraphs']=result['diagnostics']['selected_paragraphs']
    row['diagnostics']['decision']=decision
    row['rendering']='Recorded model decision replayed through final renderer; not a new model call.'
    simple=re.sub(r'\s+','',row['answer'].lower().replace('ё','е'))
    row['fact_groups']=[any(re.search(re.sub(r'\s+','',p.replace('ё','е')),simple) for p in group) for group in RUBRICS[row['id']]]
    row['facts_check']=all(row['fact_groups'])
    expected=EXPECTED[int(row['id'])-1]
    row['citation_check']=expected in {s['doc_id'] for s in result['sources_used']} if expected else row['status'] in ('partial','clarify','refused')
    row['rubric_pass']=row['facts_check'] and row['citation_check']
report['cases'].sort(key=lambda c:int(c['id']))
report['render_engine_sha256']=hashlib.sha256(pathlib.Path('engine_v2.py').read_bytes()).hexdigest()
report['summary']={'completed':18,'rubric_pass':sum(c['rubric_pass'] for c in report['cases']),'unavailable':sum(c['status']=='unavailable' for c in report['cases']),'generation_calls':sum(c['diagnostics']['generation_calls'] for c in report['cases'])}
report['note']='Real local model selections on all 18 public questions, with four affected cases remeasured. Final renderer replay is explicit; original measured answers and latency preserved. Keyword/source rubric is not legal accuracy or LLM-judge score.'
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report['summary']))
