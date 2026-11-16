import unittest,json,pathlib,hashlib,zipfile
from core import Corpus
from engine_v5 import Assistant,LegalIndex,event_date,event_year,numbers,decode,paragraphs
class Fake:
    configured=True;provider='ollama'
    def __init__(self,value):self.value=value;self.calls=0
    def chat(self,*a):self.calls+=1;return self.value if isinstance(self.value,str) else json.dumps(self.value,ensure_ascii=False)
class V5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Corpus('data');cls.idx=LegalIndex(cls.c)
    def claim(self,text='Арендная плата: 450 000 рублей.',needle='3.1.'):
        u=next(u for u in self.idx.units if u['doc_id']=='D01');pid=next(k for k,v in paragraphs(u).items() if needle in v)
        return {'status':'answered','claims':[{'text':text,'evidence':[u['id']+':'+pid]}],'missing':''}
    def test_one_call(self):
        g=Fake(self.claim());v=Assistant(self.c,g).answer('Плата Северный Склад?');self.assertEqual(g.calls,1);self.assertEqual(v['status'],'answered')
    def test_direct_claim_preserved(self):self.assertTrue(Assistant(self.c,Fake(self.claim())).answer('Плата Северный Склад?')['answer'].startswith('Арендная плата:'))
    def test_bad_number_falls_back_not_refuses(self):
        g=Fake(self.claim('Цена 999 рублей.'));v=Assistant(self.c,g).answer('Плата Северный Склад?');self.assertNotIn('999',v['answer']);self.assertIn('450 000',v['answer']);self.assertEqual(g.calls,1)
    def test_money_abbreviation(self):self.assertEqual(numbers('450 тыс. рублей'),numbers('450 000 рублей'))
    def test_decimal(self):self.assertEqual(numbers('1,5 млн'),numbers('1500000.00'))
    def test_number_words(self):self.assertEqual(numbers('четыре и трех'),numbers('4 и 3'))
    def test_unknown_claim_not_published(self):
        v=Assistant(self.c,Fake({'status':'answered','claims':[{'text':'Придуманный факт','evidence':['X']}]})).answer('Аренда');self.assertNotIn('Придуманный факт',v['answer']);self.assertEqual(v['status'],'partial')
    def test_valid_claim_survives_other_bad_claim(self):
        d=self.claim();d['claims'].append({'text':'НЕПОДТВЕРЖДЁННОЕ','evidence':['X']});v=Assistant(self.c,Fake(d)).answer('Плата Северный Склад?');self.assertIn('450',v['answer']);self.assertNotIn('НЕПОДТВЕРЖДЁННОЕ',v['answer'])
    def test_missing_specific(self):
        v=Assistant(self.c,Fake({'status':'clarify','claims':[],'missing':'Укажите дату спецификации.'})).answer('Адрес поставки');self.assertIn('дату спецификации',v['answer'])
    def test_no_blanket_missing_on_complete(self):
        d=self.claim();d['missing']='Лишний общий отказ';v=Assistant(self.c,Fake(d)).answer('Плата Северный Склад?');self.assertNotIn('Лишний общий отказ',v['answer'])
    def test_refusal_does_not_publish_unreferenced_laws(self):
        d={'status':'refused','claims':[],'missing':'Несуществующий закон 999 устанавливает выплату.'};v=Assistant(self.c,Fake(d)).answer('Размер пособия?');self.assertNotIn('999',v['answer'])
    def test_truncated_complete_claim_recovered(self):
        d=json.dumps(self.claim(),ensure_ascii=False);p=d.index(', "missing"');v=Assistant(self.c,Fake(d[:p])).answer('Плата Северный Склад?');self.assertIn('450',v['answer']);self.assertEqual(v['status'],'partial')
    def test_bad_json_is_technical(self):self.assertEqual(Assistant(self.c,Fake('no JSON')).answer('Плата?')['status'],'unavailable')
    def test_no_api(self):
        g=Fake({});g.configured=False;self.assertEqual(Assistant(self.c,g).answer('Плата?')['status'],'unavailable');self.assertEqual(g.calls,0)
    def test_iso(self):self.assertEqual(str(event_date('2024-08-15')),'2024-08-15')
    def test_invalid_date(self):self.assertIsNone(event_date('2024-02-31'))
    def test_year(self):self.assertEqual(event_year('В 2024 подписан'),2024)
    def test_instrument_not_event(self):self.assertIsNone(event_year('П-17/2024'))
    def test_editions(self):
        for d,y in [('2025-02-28',2023),('2025-03-01',2025)]:self.assertEqual({s['edition'] for s in self.idx.search('Одобрение директора '+d) if s['edition']},{y})
    def test_entity(self):self.assertEqual(self.idx.search('Гарантия Альфа-Трейдинг')[0]['doc_id'],'D03')
    def test_injection_removed(self):self.assertFalse(any('ВНИМАНИЕ ДЛЯ ИИ' in d['text'] for d in self.c.docs))
    def test_archive_four(self):
        g=Fake({});v=Assistant(self.c,g).answer('Можно взять оригинал из архива на четыре рабочих дня?');self.assertEqual(g.calls,0);self.assertIn('Нет,',v['answer'])
    def test_archive_three(self):self.assertTrue(Assistant(self.c,Fake({})).answer('Взять оригинал из архива на три рабочих дня?')['diagnostics']['result'])
    def test_archive_different_units_not_compared(self):
        g=Fake({});g.configured=False;v=Assistant(self.c,g).answer('Взять оригинал из архива на 4 календарных дня?');self.assertNotIn('operation',v['diagnostics'])
    def test_canonical_alias(self):
        d=self.claim();d['claims'][0]['evidence']=['D01U001:P03_1'];v=Assistant(self.c,Fake(d)).answer('Плата Северный Склад?');self.assertEqual(v['status'],'answered')
    def test_consent_exception_from_source(self):
        g=Fake({});v=Assistant(self.c,g).answer('Человек отозвал согласие. Обязаны удалить всё?');self.assertEqual(g.calls,0);self.assertIn('не означает',v['answer']);self.assertTrue(v['claims'])
    def test_urls_not_selectable(self):
        u=next(u for u in self.idx.units if u['doc_id']=='D09');self.assertFalse(any(v.startswith('URL:') for v in paragraphs(u).values()))
    def test_citations_are_actual(self):
        v=Assistant(self.c,Fake(self.claim())).answer('Плата Северный Склад?')
        for c in v['claims']:
            for e in c['evidence']:self.assertIn(e['quote'],next(s['text'] for s in v['sources'] if s['id']==e['source']))
