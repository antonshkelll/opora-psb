"""Platform entry point: questions.csv + knowledge-base.zip -> submission.csv."""
import csv, os, time, sys, concurrent.futures, json
from pathlib import Path
from core import Corpus, Gateway, env, env_int
from engine_v2 import GroundedAssistant

def main():
    data=Path(env('DATA_DIR','data')); started=time.monotonic()
    with (data/'questions.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['id','question']: raise ValueError('Expected id,question')
        rows=list(reader)
    ids=[r['id'] for r in rows]
    if len(set(ids))!=len(ids) or any(not i for i in ids): raise ValueError('Invalid IDs')
    bot=GroundedAssistant(Corpus(data),Gateway(provider='organizer')); deadline=started+1120
    diagnostics=[]
    results={i:'Не удалось обработать вопрос в доступное время. Юридический вывод не сделан.' for i in ids}
    def save():
        tmp=Path('submission.csv.tmp')
        with tmp.open('w',encoding='utf-8',newline='') as f:
            w=csv.writer(f); w.writerow(['id','answer']); w.writerows((i,results[i]) for i in ids)
        tmp.replace('submission.csv')
    save()
    def process(row):
        if time.monotonic()>deadline-5: return row['id'],results[row['id']]
        r=bot.answer(row['question'],min(deadline,time.monotonic()+110))
        return row['id'],r['answer'],{'id':row['id'],'status':r['status'],'elapsed_ms':r['elapsed_ms'],**r.get('diagnostics',{})}
    with concurrent.futures.ThreadPoolExecutor(max_workers=env_int('MAX_WORKERS',4,1,8)) as pool:
        for future in concurrent.futures.as_completed([pool.submit(process,row) for row in rows]):
            value=future.result()
            if len(value)==2:i,answer=value;info={'id':i,'status':'deadline'}
            else:i,answer,info=value
            diagnostics.append(info);results[i]=answer;save()
            print(json.dumps(info,ensure_ascii=False),file=sys.stderr,flush=True)
    Path('run_report.json').write_text(json.dumps({'pipeline':'v2','questions':len(rows),'elapsed_seconds':round(time.monotonic()-started,2),'statuses':{s:sum(i['status']==s for i in diagnostics) for s in sorted({i['status'] for i in diagnostics})},'items':diagnostics},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Completed '+str(len(rows))+' questions',file=sys.stderr)

if __name__=='__main__': main()
