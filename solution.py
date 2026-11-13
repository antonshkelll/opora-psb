"""Platform entry point: questions.csv + knowledge-base.zip -> submission.csv."""
import csv, os, time, sys, concurrent.futures
from pathlib import Path
from core import Corpus, Assistant

def main():
    data=Path(os.getenv('DATA_DIR','data')); started=time.monotonic()
    with (data/'questions.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['id','question']: raise ValueError('Expected id,question')
        rows=list(reader)
    ids=[r['id'] for r in rows]
    if len(set(ids))!=len(ids) or any(not i for i in ids): raise ValueError('Invalid IDs')
    bot=Assistant(Corpus(data)); deadline=started+1120
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
        return row['id'],r['answer']
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(8,int(os.getenv('MAX_WORKERS','4'))))) as pool:
        for future in concurrent.futures.as_completed([pool.submit(process,row) for row in rows]):
            i,answer=future.result(); results[i]=answer; save()
    print('Completed '+str(len(rows))+' questions',file=sys.stderr)

if __name__=='__main__': main()
