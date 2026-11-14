"""Real public-demo evaluation. Rubrics stay outside the submitted runtime."""
import csv,json,pathlib,time,re,sys,hashlib
from core import Corpus,Gateway
from engine_v2 import GroundedAssistant,LegalIndex

# Published public examples: groups accept Russian number words and numeric formatting.
RUBRICS={
'1':[['450000'],['5|пят']], '2':[['6|шест']], '3':[['недостат|нет|отсутств|не содерж|не найден']],
'4':[['450000']], '5':[['10000000|10млн|10миллион|десят'],['2023']],
'6':[['5|пят'],['рабоч']], '7':[['круглосуточ|24час|любое время']],
'8':[['акт'],['недостат|дефект']], '9':[['предоплат|аванс'],['соглаш|соглас']],
'10':[['руководител'],['подразделен']], '11':[['3|трех|три|трёх'],['рабоч']],
'12':[['распространя|действуют|применя']], '13':[['продолж|без соглас|основан'],['не|нет']],
'14':[['срочн'],['сезон']], '15':[['акт']], '16':[['включ|вход']],
'17':[['производител|талон']], '18':[['3|трех|три|трёх'],['рабоч']]}
EXPECTED=['D01','D20',None,'D01','D06','D02','D01','D02','D03','D07','D08','D20','D09','D19','D01','D02','D03','D07']

def main():
    corpus=Corpus();bot=GroundedAssistant(corpus,Gateway());path=pathlib.Path('docs/v2-real-demo-report.json')
    with open('data/demo_questions.csv',encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    selected=set(sys.argv[1:]); rows=[r for r in rows if not selected or r['id'] in selected]
    report={'pipeline':'v2','provider':bot.gateway.provider,'model':bot.gateway.model,'engine_sha256':hashlib.sha256(pathlib.Path('engine_v2.py').read_bytes()).hexdigest(),'corpus_sha256':corpus.fingerprint,'note':'Public demo rubric checks, not LLM-judge score. References and rubrics are not included in submission runtime.','cases':[]}
    if selected and path.exists():
        previous=json.loads(path.read_text(encoding='utf-8'))
        for c in previous['cases']:c.setdefault('measurement_engine_sha256',previous['engine_sha256'])
        report['cases']=[c for c in previous['cases'] if c['id'] not in selected]
    for row in rows:
        print('RUN '+row['id'],flush=True);result=bot.answer(row['question'],time.monotonic()+300)
        answer=result['answer'];simple=re.sub(r'\s+','',answer.lower().replace('ё','е'))
        checks=[any(re.search(re.sub(r'\s+','',pattern.replace('ё','е')),simple) for pattern in group) for group in RUBRICS[row['id']]]
        needed=EXPECTED[int(row['id'])-1];cited={s['doc_id'] for s in result.get('sources_used',[])}
        citation_ok=needed in cited if needed else result['status'] in ('partial','refused','clarify')
        item={'id':row['id'],'question':row['question'],'status':result['status'],'answer':answer,'facts_check':all(checks),'fact_groups':checks,'citation_check':citation_ok,'rubric_pass':all(checks) and citation_ok and result['status']!='unavailable','elapsed_ms':result['elapsed_ms'],'diagnostics':result.get('diagnostics',{})}
        item['measurement_engine_sha256']=report['engine_sha256'];item['measurement_mode']='real_model_call'
        report['cases'].append(item);report['summary']={'completed':len(report['cases']),'rubric_pass':sum(c['rubric_pass'] for c in report['cases']),'unavailable':sum(c['status']=='unavailable' for c in report['cases']),'generation_calls':sum(c['diagnostics'].get('generation_calls',0) for c in report['cases'])}
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(item,ensure_ascii=False),flush=True)
    print(json.dumps(report['summary']),flush=True)

if __name__=='__main__':main()
