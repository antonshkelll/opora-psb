"""Retrieval benchmark on public demo questions. Does not estimate LLM-judge score."""
import csv,json,pathlib
from core import Corpus
from engine_v5 import LegalIndex
c=Corpus(); index=LegalIndex(c); expected=['D01','D20',None,'D01','D06','D02','D01','D02','D03','D07','D08','D20','D09','D19','D01','D02','D03','D07']
with open('data/demo_questions.csv',encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
checks=[]
for row,target in zip(rows,expected):
    sources=index.search(row['question'],7); found={s['doc_id'] for s in sources}
    checks.append({'id':row['id'],'expected_document':target,'retrieved':sorted(found),'hit':target in found if target else None})
eligible=[r for r in checks if r['hit'] is not None]
report={'corpus_documents':len(c.docs),'chunks':len(index.units),'removed_injection_lines':c.removed,'corpus_sha256':c.fingerprint,'metric':'document recall@7 with applicability filter','hits':sum(r['hit'] for r in eligible),'eligible':len(eligible),'recall':sum(r['hit'] for r in eligible)/len(eligible),'note':'Public demos only; document recall is not answer quality or private leaderboard performance. Expected IDs manually mapped from published examples.','cases':checks}
pathlib.Path('docs').mkdir(exist_ok=True); pathlib.Path('docs/v5-retrieval-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2))
