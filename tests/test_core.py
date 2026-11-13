import unittest, tempfile, zipfile, pathlib, csv, os, subprocess, sys, json
from core import Corpus, Assistant, validate

class FakeGateway:
    configured=True
    def __init__(self, responses): self.responses=iter(responses)
    def chat(self,*args): return json.dumps(next(self.responses),ensure_ascii=False)

class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.c=Corpus('data')
    def test_corpus(self): self.assertEqual(len(self.c.docs),21)
    def test_document_injection_removed(self):
        self.assertGreater(self.c.removed,0)
        self.assertNotIn('ВНИМАНИЕ ДЛЯ ИИ', ''.join(d['text'] for d in self.c.docs))
    def test_amendment_link(self):
        s=self.c.search('Адрес доставки по договору П-17/2024 Альфа-Трейд',3)
        self.assertTrue(any('Доп соглашение' in c['name'] for c in s))
    def test_editions_link(self):
        s=self.c.search('Регламент: одобрение директора в 2024 году',3)
        self.assertTrue(any('2023' in c['name'] for c in s)); self.assertTrue(any('2025' in c['name'] for c in s))
    def test_fabricated_quote(self):
        obj={'status':'answered','claims':[{'text':'90 дней','evidence':[{'source':self.c.chunks[0]['id'],'quote':'Несуществующая цитата'}]}]}
        self.assertIn('Quote not found',validate(obj,self.c.chunks))
    def test_missing_evidence(self): self.assertIn('Unsupported claim',validate({'status':'answered','claims':[{'text':'Факт'}]},[]))
    def test_no_api_is_not_legal_refusal(self):
        class Offline: configured=False
        r=Assistant(self.c,Offline()).answer('Арендная плата')
        self.assertEqual(r['status'],'unavailable'); self.assertTrue(r['sources'])
    def test_valid_end_to_end_mock(self):
        s=self.c.search('Арендная плата')[0]
        obj={'status':'answered','claims':[{'text':'Проверяемый вывод','evidence':[{'source':s['id'],'quote':s['text'][:80],'provision':''}]}],'missing':''}
        r=Assistant(self.c,FakeGateway([obj,{'valid':True}])).answer('Арендная плата')
        self.assertEqual(r['status'],'answered'); self.assertIn('Источник:',r['answer'])
    def test_semantic_audit_blocks(self):
        s=self.c.search('Арендная плата')[0]
        obj={'status':'answered','claims':[{'text':'Ошибочный вывод','evidence':[{'source':s['id'],'quote':s['text'][:80]}]}],'missing':''}
        r=Assistant(self.c,FakeGateway([obj,{'valid':False}])).answer('Арендная плата')
        self.assertEqual(r['status'],'unavailable'); self.assertNotIn('Ошибочный вывод',r['answer'])
    def test_zip_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            p=pathlib.Path(temp); (p/'questions.csv').write_text('id,question\nabc,"Вопрос, с запятой"\nxyz,"Другой вопрос"\n',encoding='utf-8')
            with zipfile.ZipFile(p/'knowledge-base.zip','w') as z:z.writestr('doc.txt','Тестовый документ с положениями договора.')
            env=dict(os.environ,DATA_DIR=temp,LLM_BASE_URL='',OPENAI_BASE_URL='',LLM_MODEL='',OPENAI_MODEL='',GEN_MODEL='')
            subprocess.run([sys.executable,str(pathlib.Path('solution.py').resolve())],cwd=temp,env=env,check=True,capture_output=True)
            with (p/'submission.csv').open(encoding='utf-8',newline='') as f:
                r=csv.DictReader(f); self.assertEqual(r.fieldnames,['id','answer']); rows=list(r)
            self.assertEqual([r['id'] for r in rows],['abc','xyz']); self.assertTrue(all(0<len(r['answer'])<=10000 for r in rows))

if __name__=='__main__': unittest.main()
