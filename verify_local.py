"""Run a small real-model smoke evaluation; never estimates the platform score."""
import json,pathlib,time,os,sys
from core import Corpus,Assistant,Gateway

def main():
    bot=Assistant(Corpus(),Gateway()); cases=[('rent','Какая арендная плата по договору с ООО «Северный Склад» и до какого числа её нужно вносить?'),('missing','Какой размер пособия по беременности и родам?')]
    report={'provider':bot.gateway.provider,'model':bot.gateway.model,'cases':[],'note':'Real local model smoke test. Not a DeepSeek or leaderboard evaluation.'}
    if '--missing-only' in sys.argv:
        cases=[cases[1]]
        previous=pathlib.Path('docs/local-model-report.json')
        if previous.exists():report['cases']=[c for c in json.loads(previous.read_text(encoding='utf-8'))['cases'] if c['name']!='missing']
    for name,question in cases:
        print('Running '+name,flush=True);r=bot.answer(question,time.monotonic()+600)
        item={'name':name,'question':question,'status':r['status'],'answer':r['answer'],'elapsed_ms':r['elapsed_ms'],'error':r.get('missing',''),'claims':r.get('claims',[])}
        if name=='rent': item['smoke_check']=r['status']=='answered' and '450' in r['answer'] and '5' in r['answer']
        else: item['smoke_check']=r['status'] in ('partial','refused','clarify') and bool(r.get('missing'))
        report['cases'].append(item)
        pathlib.Path('docs/local-model-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(item,ensure_ascii=False),flush=True)
    print('Passed '+str(sum(c['smoke_check'] for c in report['cases']))+'/'+str(len(report['cases'])),flush=True)

if __name__=='__main__': main()
