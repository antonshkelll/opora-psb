import unittest,json,time,os
from unittest.mock import patch
from core import Corpus,Gateway,env
from engine_v3 import LegalAssistant,LegalIndex,event_date,event_year,check,dialogue,number_tokens

class Fake:
    configured=True;provider='organizer'
    def __init__(self,items):self.items=iter(items);self.calls=0
    def chat(self,*args):self.calls+=1;return json.dumps(next(self.items),ensure_ascii=False)

class V3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Corpus('data');cls.index=LegalIndex(cls.c)
    def docclaim(self,did,needle,text=None):
        s=next(s for s in self.index.units if s['doc_id']==did)
        lines=[l for l in s['text'].splitlines() if l.strip()];i=next(i for i,l in enumerate(lines) if needle in l)
        return {'status':'answered','claims':[{'text':text or lines[i],'evidence':[s['id']+f':P{i+1:03}']}],'missing':''}
    def test_iso(self):self.assertEqual(str(event_date('2024-08-15')),'2024-08-15')
    def test_numeric_date(self):self.assertEqual(str(event_date('15.08.2024')),'2024-08-15')
    def test_invalid_date(self):self.assertIsNone(event_date('2024-02-31'))
    def test_plain_year(self):self.assertEqual(event_year('В 2024 подписали'),2024)
    def test_instrument_not_event(self):self.assertIsNone(event_year('П-17/2024'))
    def test_occurrence_order(self):self.assertEqual(str(event_date('январь 2025, затем июнь 2024')),'2024-06-01')
    def test_new_edition_boundary(self):
        for d,edition in [('2025-02-28',2023),('2025-03-01',2025),('2024-08-15',2023)]:
            units=self.index.search('Нужно одобрение директора? Дата события: '+d,12)
            found=[u['edition'] for u in units if u['edition']]
            self.assertTrue(found);self.assertEqual(set(found),{edition})
    def test_comparison_keeps_editions(self):self.assertEqual({s['edition'] for s in self.index.search('Сравните редакции регламента 2023 и 2025') if s['edition']},{2023,2025})
    def test_entity(self):self.assertEqual(self.index.search('Гарантия Альфа-Трейдинг')[0]['doc_id'],'D03')
    def test_amendment(self):self.assertIn('D04',{s['doc_id'] for s in self.index.search('Адрес доставки по П-17/2024 после изменения')})
    def test_injection_removed(self):self.assertFalse(any('ВНИМАНИЕ ДЛЯ ИИ' in d['text'] for d in self.c.docs))
    def test_history_no_legal_assistant_fact(self):self.assertNotIn('999',dialogue('Пользователь: Северный Склад\nАссистент: Цена 999\nПользователь: Срок?')[1])
    def test_extract_needs_one_call(self):
        g=Fake([self.docclaim('D01','3.1.')]);r=LegalAssistant(self.c,g).answer('Арендная плата Северный Склад')
        self.assertEqual(r['status'],'answered');self.assertEqual(g.calls,1)
    def test_synthesis_review(self):
        g=Fake([self.docclaim('D08','Выдача оригиналов','Четыре рабочих дня превышают допустимый срок.'),{'valid':True}]);r=LegalAssistant(self.c,g).answer('Допустим срок четыре рабочих дня для оригинала из архива?')
        self.assertTrue(r['diagnostics']['reviewed']);self.assertEqual(g.calls,2)
    def test_review_blocks_opposite_yes(self):
        g=Fake([self.docclaim('D08','Выдача оригиналов','Да, разрешено на четыре рабочих дня.'),{'valid':False,'corrected':self.docclaim('D08','Выдача оригиналов','Нет, допустимо не более трёх рабочих дней.')}]);r=LegalAssistant(self.c,g).answer('Допустим срок четыре рабочих дня для оригинала из архива?')
        self.assertIn('Нет,',r['answer']);self.assertNotIn('Да, разрешено',r['answer'])
    def test_review_fail_not_published(self):
        g=Fake([self.docclaim('D08','Выдача оригиналов','Да, разрешено.'),{'valid':False}]);r=LegalAssistant(self.c,g).answer('Можно взять оригинал на четыре дня?')
        self.assertEqual(r['status'],'unavailable');self.assertNotIn('Да, разрешено',r['answer'])
    def test_unknown_evidence(self):
        with self.assertRaises(ValueError):check({'status':'answered','claims':[{'text':'Да','evidence':['made-up']}],'missing':''},{},'')
    def test_unsupported_number(self):
        with self.assertRaises(ValueError):check({'status':'answered','claims':[{'text':'999 рублей','evidence':['p']}],'missing':''},{'p':({},'Цена 450 000 рублей')},'Цена?')
    def test_empty_answered(self):
        with self.assertRaises(ValueError):check({'status':'answered','claims':[]},{},'')
    def test_specific_missing(self):
        g=Fake([{'status':'clarify','claims':[],'missing':'Укажите дату спецификации.'},{'valid':True}]);r=LegalAssistant(self.c,g).answer('Какой адрес доставки по П-17/2024?')
        self.assertIn('дату спецификации',r['answer'])
    def test_unconfigured_is_technical(self):
        g=Fake([]);g.configured=False;r=LegalAssistant(self.c,g).answer('Аренда')
        self.assertEqual(r['status'],'unavailable')
    def test_no_clock_based_blanket_rejection(self):
        g=Fake([self.docclaim('D20','Срок испытания')]);r=LegalAssistant(self.c,g).answer('Испытание главного бухгалтера в 2025 году')
        self.assertEqual(r['status'],'answered')
    def test_provider_enforced(self):self.assertEqual(Gateway(provider='organizer').provider,'organizer')
    def test_archive_bound_exceeded(self):
        r=LegalAssistant(self.c,Fake([])).answer('Можно взять оригинал из архива на четыре рабочих дня?')
        self.assertIn('Нет,',r['answer']);self.assertEqual(r['diagnostics']['generation_calls'],0)
    def test_archive_bound_equal(self):
        r=LegalAssistant(self.c,Fake([])).answer('Можно взять оригинал из архива на три рабочих дня?')
        self.assertTrue(r['diagnostics']['result'])
    def test_archive_unit_mismatch_not_computed(self):
        g=Fake([]);g.configured=False
        r=LegalAssistant(self.c,g).answer('Можно взять оригинал из архива на 4 календарных дня?')
        self.assertNotIn('operation',r['diagnostics'])
    def test_placeholder(self):
        with patch.dict(os.environ,{'LLM_MODEL':'LLM_MODEL'}):self.assertEqual(env('LLM_MODEL','fallback'),'fallback')
    def test_number_thousands(self):self.assertEqual(number_tokens('450 тыс. рублей'),number_tokens('450 000 рублей'))
    def test_number_words(self):self.assertEqual(number_tokens('четыре дня и трех дней'),number_tokens('4 дня и 3 дня'))
    def test_bibliographic_ids_not_quantities(self):
        obj={'status':'answered','claims':[{'text':'Срок 3 дня, пункт P007 документа D08U001','evidence':['D08U001:P007']}],'missing':''}
        self.assertEqual(check(obj,{'D08U001:P007':({'title':'Записка','text':''},'Не более 3 дней')},'Срок?')['status'],'answered')
    def test_number_millions(self):self.assertEqual(number_tokens('1,5 млн'),number_tokens('1 500 000'))
    def test_number_decimal_format(self):self.assertEqual(number_tokens('450000.00'),number_tokens('450 000'))
    def test_null_missing(self):self.assertEqual(check({'status':'clarify','claims':[],'missing':None},{},'')['missing'],'')
    def test_claim_list_required(self):
        with self.assertRaises(ValueError):check({'status':'answered','claims':'claim'},{},'')

if __name__=='__main__':unittest.main()
