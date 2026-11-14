import unittest,time,json
from core import Corpus
from engine_v2 import LegalIndex,AssistantV2,GroundedAssistant,decode_answer,check_answer,dialogue

class Fake:
    configured=True;provider='organizer'
    def __init__(self,answers):self.answers=iter(answers);self.calls=0
    def chat(self,*args):self.calls+=1;return next(self.answers)

class V2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.c=Corpus('data');cls.idx=LegalIndex(cls.c)
    def test_dialogue_ignores_assistant_claims(self):
        last,context=dialogue('Пользователь: Альфа-Трейдинг\nАссистент: Гарантия 24 месяца, Альфа-Трейд.\nПользователь: Можно аванс?')
        self.assertEqual(last,'Можно аванс?');self.assertNotIn('24',context)
    def test_heading_is_not_evidence(self):
        u=next(u for u in self.idx.units if u['doc_id']=='D01')
        lines=[l for l in u['text'].splitlines() if l.strip()]
        n=next(i for i,l in enumerate(lines) if l.startswith('5. '))
        fake=Fake([json.dumps({'status':'answered','verdict':'facts','selected':[u['id']+f':P{n+1:03}'],'reason':'none'})])
        r=GroundedAssistant(self.c,fake).answer('Условия аренды Северный Склад')
        self.assertEqual(r['status'],'partial');self.assertEqual(r['claims'],[])
    def test_isolated_list_item_is_not_a_missing_rule_answer(self):
        u=next(u for u in self.idx.units if u['doc_id']=='D20')
        lines=[l for l in u['text'].splitlines() if l.strip()]
        n=next(i for i,l in enumerate(lines) if l.startswith('беременных женщин'))
        fake=Fake([json.dumps({'status':'partial','verdict':'facts','selected':[u['id']+f':P{n+1:03}'],'reason':'missing_rule'})])
        r=GroundedAssistant(self.c,fake).answer('Какой размер пособия по беременности и родам?')
        self.assertEqual(r['claims'],[]);self.assertIn('не найдено положения',r['answer'])
    def test_partial_has_no_contradictory_blanket_refusal(self):
        u=next(u for u in self.idx.units if u['doc_id']=='D01')
        lines=[l for l in u['text'].splitlines() if l.strip()]
        n=next(i for i,l in enumerate(lines) if l.startswith('6.3.'))
        fake=Fake([json.dumps({'status':'partial','verdict':'facts','selected':[u['id']+f':P{n+1:03}'],'reason':'missing_rule'})])
        r=GroundedAssistant(self.c,fake).answer('Возврат помещения Северный Склад')
        self.assertIn('по акту',r['answer']);self.assertNotIn('не найдено положения',r['answer'])
    def test_contract_routing(self):
        s=self.idx.search('По договору с Альфа-Трейдинг можно заплатить авансом?',3)
        self.assertIn('ПТ-05',s[0]['name']);self.assertIn('предоплата',s[0]['text'])
    def test_old_edition(self):
        s=self.idx.search('Договор на 12 млн заключали в августе 2024 года. Нужно ли одобрение директора?')
        regs=[u for u in s if u['edition']]
        self.assertTrue(regs);self.assertEqual(regs[0]['edition'],2023);self.assertIn('10 000 000',regs[0]['text'])
    def test_early_2025_uses_old_edition(self):
        s=self.idx.search('15 января 2025 года подписываем договор на 12 миллионов: требуется одобрение директора?')
        regs=[u for u in s if u['edition']]
        self.assertEqual(regs[0]['edition'],2023)
    def test_later_2025_uses_new_edition(self):
        s=self.idx.search('15.03.2025 подписываем договор на 12 миллионов: требуется одобрение директора?')
        regs=[u for u in s if u['edition']]
        self.assertEqual(regs[0]['edition'],2025)
    def test_inapplicable_edition_never_reaches_model(self):
        s=self.idx.search('Договор на 12 миллионов заключали в августе 2024 года. Нужно ли одобрение директора?')
        self.assertFalse(any(u['edition']==2025 for u in s));self.assertTrue(any(u['edition']==2023 for u in s))
    def test_comparison_preserves_both_editions(self):
        s=self.idx.search('Сравни редакции регламента: одобрение директора в августе 2024 года и теперь')
        self.assertEqual({u['edition'] for u in s if u['edition']},{2023,2025})
    def test_amendment_application_condition(self):
        s=self.idx.search('Адрес доставки Альфа-Трейд: спецификация подписана после 1 октября 2024 года')
        self.assertTrue(any('после 1 октября' in u['text'] for u in s))
    def test_trial_exception_preserved(self):
        s=self.idx.search('Максимальный испытательный срок главному бухгалтеру?',4)
        self.assertTrue(any('шести месяцев' in u['text'] for u in s))
    def test_false_citation_rejected(self):self.assertEqual(check_answer({'status':'answered','answer':'Факт [D99U001]','citations':[]},[]),['unknown source IDs'])
    def test_plain_answer_with_valid_ids(self):
        raw='450 000 рублей [D01U001]';obj=decode_answer(raw)
        self.assertFalse(check_answer(obj,[{'id':'D01U001'}]))
    def test_no_mandatory_second_call(self):
        s=self.idx.search('Северный Склад: арендная плата')[0]
        g=Fake([json.dumps({'status':'answered','answer':'450 000 рублей ['+s['id']+']','citations':[s['id']]})]);r=AssistantV2(self.c,g).answer('Северный Склад: арендная плата')
        self.assertEqual(r['status'],'answered');self.assertEqual(g.calls,1);self.assertTrue(r['claims'][0]['evidence'][0]['quote'])
    def test_partial_does_not_require_nonexistent_source(self):
        g=Fake([json.dumps({'status':'partial','answer':'В базе недостаточно сведений о пособии.','citations':[]})]);r=AssistantV2(self.c,g).answer('Пособие по беременности')
        self.assertEqual(r['status'],'partial');self.assertEqual(g.calls,1)
    def test_failure_keeps_original_evidence(self):
        class Offline:configured=False
        r=AssistantV2(self.c,Offline()).answer('Арендная плата Северный Склад')
        self.assertEqual(r['status'],'unavailable');self.assertIn('450 000',r['sources'][0]['text']);self.assertIn('Найденные положения',r['answer'])
    def test_grounded_compiler_discards_model_inventions(self):
        source=self.idx.search('Северный Склад: арендная плата')[0]
        lines=[l for l in source['text'].splitlines() if l.strip()]
        n=next(i for i,l in enumerate(lines) if l.startswith('3.1.'))+1
        sid=source['id']+f':P{n:03}'
        g=Fake([json.dumps({'status':'answered','verdict':'facts','selected':[sid],'reason':'none','answer':'Договор автоматически продлевается каждый месяц. 500 000 рублей.'})])
        r=GroundedAssistant(self.c,g).answer('Северный Склад: арендная плата')
        self.assertEqual(r['status'],'answered');self.assertIn('450 000',r['answer']);self.assertNotIn('500 000',r['answer']);self.assertNotIn('продлевается',r['answer']);self.assertEqual(g.calls,1)
        self.assertEqual(r['claims'][0]['evidence'][0]['quote'],lines[n-1])
    def test_grounded_compiler_rejects_forged_paragraph(self):
        raw=json.dumps({'status':'answered','verdict':'facts','selected':['D99U001:P999'],'reason':'none'})
        r=GroundedAssistant(self.c,Fake([raw,raw])).answer('Северный Склад: аренда')
        self.assertEqual(r['status'],'unavailable');self.assertIn('UNKNOWN_PARAGRAPH',r['missing'])
    def test_grounded_compiler_clarifies_entity(self):
        raw=json.dumps({'status':'clarify','verdict':'depends','selected':[],'reason':'entity'})
        r=GroundedAssistant(self.c,Fake([raw])).answer('Какая гарантия у Альфы?')
        self.assertEqual(r['status'],'clarify');self.assertIn('Уточните контрагента',r['answer']);self.assertEqual(r['claims'],[])
    def test_grounded_historical_statute_guard(self):
        s=self.idx.search('Какой срок испытания по ст. 70 ТК в 2020 году?')[0]
        if s['kind']!='law':self.fail('Law routing failed')
        raw=json.dumps({'status':'answered','verdict':'facts','selected':[s['id']+':P001'],'reason':'none'})
        r=GroundedAssistant(self.c,Fake([raw])).answer('Какой срок испытания по ст. 70 ТК в 2020 году?')
        self.assertEqual(r['status'],'partial');self.assertIn('историческая редакция',r['answer']);self.assertEqual(r['claims'],[])

if __name__=='__main__':unittest.main()
