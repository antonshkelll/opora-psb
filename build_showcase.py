"""Publish recorded model answers with exact evidence; no reference-answer substitution."""
import json,pathlib
from core import Corpus,clean_display
from engine_v2 import LegalIndex
root=pathlib.Path(__file__).parent
c=Corpus(root/'data');index=LegalIndex(c)
report=json.loads((root/'docs/v2-real-demo-report.json').read_text(encoding='utf-8'))
assert len(report['cases'])==18,'Complete the real benchmark first'
lookup={u['id']+f':P{n+1:03}':(u,line) for u in index.units for n,line in enumerate(l for l in u['text'].splitlines() if l.strip())}
cases=[]
for row in sorted(report['cases'],key=lambda r:int(r['id'])):
    evidence=[]
    for sid in row['diagnostics'].get('selected_paragraphs',[]):
        unit,quote=lookup[sid]
        evidence.append({'doc_id':unit['doc_id'],'title':unit['title'],'quote':quote,'provision':sid})
    cases.append({'id':row['id'],'question':clean_display(row['question']),'answer':row['answer'],'verdict':'','status':row['status'],'evidence':evidence,'elapsed_ms':row['elapsed_ms']})
payload={'type':'recorded_model_runs','model':report['model'],'notice':'Сохранённые ответы реального локального прогона Qwen3.5 4B. Страница не вызывает модель. Это не оценка DeepSeek и не закрытый тест.','documents':[{k:d[k] for k in ('id','title','name','text')} for d in c.docs],'cases':cases,'corpus_sha256':c.fingerprint}
(root/'web/demo.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print('Published',len(cases),'recorded scenarios,',len(c.docs),'documents')
