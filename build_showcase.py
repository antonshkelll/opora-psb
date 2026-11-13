"""Build clearly labelled public reference scenarios from organizer examples."""
import csv,json,pathlib,re
from core import Corpus,clean_display
root=pathlib.Path(__file__).parent;c=Corpus(root/'data')
with (root/'data/demo_questions.csv').open(encoding='utf-8-sig',newline='') as f: questions=list(csv.DictReader(f))
with (root/'data/demo_output.csv').open(encoding='utf-8-sig',newline='') as f: answers={r['id']:r['answer'] for r in csv.DictReader(f)}
expected=['D01','D20',None,'D01','D06','D02','D01','D02','D03','D07','D08','D20','D09','D19','D01','D02','D03','D07']
anchors=['3.1. Арендная','Срок испытания',None,'3.1. Арендная','2.4. Договоры','5.3.','4.3.','5.4.','4.1.','1.3.','Выдача оригиналов','В период испытания','2. Согласие','сезонных работ','6.3.','2.1.','6.1.','3.2.']
cases=[]
for i,row in enumerate(questions):
    doc=next((d for d in c.docs if d['id']==expected[i]),None); evidence=[]
    if doc:
        start=doc['text'].find(anchors[i]);start=max(0,start)
        quote=doc['text'][start:start+650]
        if '\n' in quote:quote=quote[:quote.rfind('\n')]
        evidence=[{'doc_id':doc['id'],'title':doc['title'],'quote':quote,'provision':'Положение документа'}]
    text=clean_display(answers[row['id']])
    verdicts={'1':'450 000 рублей в месяц, до 5-го числа','5':'Да, одобрение директора было необходимо','3':'Для расчёта пособия не хватает данных','4':'В договоре указана другая сумма: 450 000 рублей','9':'Предоплата возможна по соглашению сторон','11':'Четыре рабочих дня превышают установленный срок','15':'Нужно оформить акт возврата помещения'}
    if row['id']=='1' and evidence:evidence[0]['quote']='\n'.join(evidence[0]['quote'].splitlines()[:3]);evidence[0]['provision']='Пункты 3.1-3.3'
    if row['id']=='5' and evidence:evidence[0]['quote']=evidence[0]['quote'].splitlines()[0];evidence[0]['provision']='Редакция 2023 года, пункт 2.4'
    cases.append({'id':row['id'],'question':clean_display(row['question']),'answer':text,'verdict':verdicts.get(row['id'],''),'status':'partial' if row['id']=='3' else 'answered','evidence':evidence})
payload={'type':'prepared_reference_examples','notice':'Ответы подготовлены заранее по демонстрационным материалам организаторов. Это не результат живой генерации.','documents':[{k:d[k] for k in ('id','title','name','text')} for d in c.docs],'cases':cases,'corpus_sha256':c.fingerprint}
(root/'web/demo.json').write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8')
print('Built',len(cases),'reference scenarios and',len(c.docs),'documents')
