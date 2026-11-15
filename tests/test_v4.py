import unittest,json,pathlib,zipfile,hashlib
from core import Corpus
from engine_v4 import GroundedAssistant,LegalIndex,event_date,event_year

class Fake:
    configured=True;provider='ollama'
    def __init__(self,decision):self.decision=decision;self.calls=0
    def chat(self,*args):self.calls+=1;return json.dumps(self.decision,ensure_ascii=False)

class V4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Corpus('data');cls.index=LegalIndex(cls.c)
    def choice(self,did,needle,verdict='facts'):
        s=next(s for s in self.index.units if s['doc_id']==did);lines=[l for l in s['text'].splitlines() if l.strip()]
        n=next(i for i,l in enumerate(lines) if needle in l)
        return {'status':'answered','verdict':verdict,'selected':[s['id']+f':P{n+1:03}'],'reason':'none'}
    def test_exact_rollback_files(self):
        with zipfile.ZipFile('output/opora-rollback-v2.zip') as z:
            manifest=json.loads(pathlib.Path('docs/rollback-v2-sha256.json').read_text())
            for n in z.namelist():self.assertEqual(hashlib.sha256(z.read(n)).hexdigest(),manifest[n])
    def test_iso(self):self.assertEqual(str(event_date('2024-08-15')),'2024-08-15')
    def test_year(self):self.assertEqual(event_year('В 2024 подписан'),2024)
    def test_invalid_date(self):self.assertIsNone(event_date('2024-02-31'))
    def test_date_boundary(self):
        for d,y in [('2025-02-28',2023),('2025-03-01',2025)]:
            a=[s['edition'] for s in self.index.search('Одобрение директора '+d) if s['edition']]
            self.assertTrue(a);self.assertEqual(set(a),{y})
    def test_comparison(self):self.assertEqual({s['edition'] for s in self.index.search('Сравните редакции 2023 и 2025') if s['edition']},{2023,2025})
    def test_entity(self):self.assertEqual(self.index.search('Гарантия Альфа-Трейдинг')[0]['doc_id'],'D03')
    def test_no_second_call(self):
        g=Fake(self.choice('D01','3.1.'));r=GroundedAssistant(self.c,g).answer('Аренда Северный Склад')
        self.assertEqual(g.calls,1);self.assertEqual(r['status'],'answered')
    def test_model_yes_not_trusted(self):
        g=Fake(self.choice('D08','Выдача оригиналов','yes'));r=GroundedAssistant(self.c,g).answer('Взять оригинал из архива на четыре рабочих дня?')
        self.assertNotIn('Да,',r['answer']);self.assertIn('не более 3',r['answer'])
    def test_numeric_free_text_ignored(self):
        d=self.choice('D01','3.1.');d['answer']='Цена 999 рублей';r=GroundedAssistant(self.c,Fake(d)).answer('Аренда Северный Склад')
        self.assertNotIn('999',r['answer']);self.assertIn('450 000',r['answer'])
    def test_no_clock_based_legal_refusal(self):
        r=GroundedAssistant(self.c,Fake(self.choice('D20','Срок испытания'))).answer('Срок испытания в 2025 году')
        self.assertEqual(r['status'],'answered')
    def test_parent_condition(self):
        r=GroundedAssistant(self.c,Fake(self.choice('D19','для выполнения сезонных работ'))).answer('Срочный договор для сезонных работ')
        self.assertIn('Срочный трудовой договор заключается:',r['answer'])
    def test_recorded_decisions_replay_only(self):
        report=json.loads(pathlib.Path('docs/v2-selection-control.json').read_text(encoding='utf-8'))
        for case in report['cases']:
            with self.subTest(case=case['id']):
                r=GroundedAssistant(self.c,Fake(case['diagnostics']['decision'])).answer(case['question'])
                self.assertNotEqual(r['status'],'unavailable')
                for claim in r['claims']:
                    for proof in claim['evidence']:
                        source=next(s for s in r['sources'] if s['id']==proof['source']);self.assertIn(proof['quote'],source['text'])

if __name__=='__main__':unittest.main()
