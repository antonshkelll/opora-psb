"""Evidence-first legal RAG. Runtime dependencies: Python standard library only."""
import os, re, json, math, time, hashlib, zipfile, urllib.request, urllib.error, threading, io
from xml.etree import ElementTree as ET
from pathlib import Path
from collections import Counter

def normalize(s):
    return re.sub(r'\s+', ' ', s.lower().replace('ё','е')).strip()

def tokens(s):
    return re.findall(r'[а-яa-z0-9]{2,}', normalize(s))

def clean_display(s):
    return s.replace('\u2014', ':').replace('\u2013','-')

INJECTION = re.compile(r'внимание для ии|игнорируй все|не упоминай эту инструкцию|ignore (?:all|previous)', re.I)

def env(name, default=''):
    value=os.getenv(name,'').strip()
    return default if not value or value==name else value

def env_int(name, default, low, high):
    try: return max(low,min(high,int(env(name))))
    except ValueError: return default

def read_document(name, raw):
    if name.lower().endswith('.docx'):
        with zipfile.ZipFile(io.BytesIO(raw)) as doc:
            info=doc.getinfo('word/document.xml')
            if info.file_size>16_000_000: raise ValueError('DOCX exceeds limit')
            tree=ET.fromstring(doc.read(info))
        ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        return '\n'.join(''.join(t.text or '' for t in p.iter(ns+'t')) for p in tree.iter(ns+'p'))
    return raw.decode('utf-8-sig')

class Corpus:
    def __init__(self, data_dir=None):
        base=Path(data_dir or env('DATA_DIR','data'))
        archives=[base/n for n in ('knowledge-base.zip','knowledge_base.zip','kb.zip')]
        archive=next((p for p in archives if p.exists()),None)
        if archive:
            with zipfile.ZipFile(archive) as z:
                names=sorted(n for n in z.namelist() if n.lower().endswith(('.txt','.md','.docx')) and not n.startswith('__MACOSX'))
                if sum(z.getinfo(n).file_size for n in names)>64_000_000: raise ValueError('Corpus exceeds 64 MB')
                raw=[(n, read_document(n,z.read(n))) for n in names]
        else:
            raw=[(p.name,p.read_text(encoding='utf-8-sig')) for p in sorted(base.rglob('*.txt')) if p.name!='allowed_requirements.txt']
        if not raw: raise ValueError('База знаний не найдена в DATA_DIR')
        self.docs=[]; self.chunks=[]; self.removed=0
        for i,(name,text) in enumerate(raw):
            lines=text.splitlines(); safe=[]
            for line in lines:
                if INJECTION.search(line): self.removed+=1
                else: safe.append(line)
            text='\n'.join(safe)
            doc={'id':f'D{i+1:02}', 'name':Path(name).name,'title':next((l for l in safe if l.strip()),name), 'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}
            self.docs.append(doc)
            # Preserve document introduction and provision labels; overlap long legal paragraphs.
            for start in range(0,len(text),2100):
                fragment=text[max(0,start-240):start+2340]
                self.chunks.append({'id':f'{doc["id"]}-{start//2100+1}', 'doc_id':doc['id'],'name':doc['name'],'title':doc['title'],'text':fragment})
        self.tf=[Counter(tokens(c['name']+' '+c['title']+' '+c['text'])) for c in self.chunks]
        self.df=Counter(t for c in self.tf for t in c)
        self.avg=sum(sum(c.values()) for c in self.tf)/len(self.tf)
        self.fingerprint=hashlib.sha256(''.join(d['sha256'] for d in self.docs).encode()).hexdigest()

    def search(self, question, top_k=8):
        q=tokens(question); scores=[]; n=len(self.tf)
        for idx,tf in enumerate(self.tf):
            length=sum(tf.values()); score=0
            for t in set(q):
                # Prefix overlap helps Russian inflection without external morphology.
                terms=[t] if t in tf else [w for w in tf if len(t)>4 and w[:5]==t[:5]]
                for term in terms:
                    f=tf[term]; idf=math.log(1+(n-self.df[term]+0.5)/(self.df[term]+0.5))
                    score+=idf*f*2.5/(f+1.5*(0.25+0.75*length/self.avg))*(1 if term==t else .5)
            scores.append((score,idx))
        ranked=sorted(scores,reverse=True)
        chosen=[dict(self.chunks[i],score=round(s,3)) for s,i in ranked[:top_k] if s>0]
        # Always attach linked amendments and both editions when the parent is retrieved.
        selected_docs={c['doc_id'] for c in chosen}
        for d in self.docs:
            linked=('Доп соглашение' in d['name'] and any('П-17' in c['name'] for c in chosen)) or ('Регламент' in d['name'] and any('Регламент' in c['name'] for c in chosen)) or ('комплаенс' in d['name'] and re.search('иностран|санкци',question,re.I))
            if linked and d['id'] not in selected_docs:
                chosen.append({'id':d['id']+'-linked','doc_id':d['id'],'name':d['name'],'title':d['title'],'text':d['text'],'score':0})
        return chosen

class Gateway:
    def __init__(self,provider=None):
        self.provider=provider or env('LLM_PROVIDER','organizer')
        self.base=(env('LLM_BASE_URL') or env('BASE_URL') or env('OPENAI_BASE_URL')).rstrip('/')
        self.key=env('LLM_API_KEY') or env('OPENAI_API_KEY')
        self.model=env('LLM_MODEL') or env('OPENAI_MODEL') or env('GEN_MODEL')
        if self.provider=='ollama':
            self.base=env('OLLAMA_BASE_URL','http://127.0.0.1:11434').rstrip('/')
            self.model=env('OLLAMA_MODEL','qwen3.5:4b');self.key=''
        elif self.provider=='openrouter':
            self.base='https://openrouter.ai/api/v1';self.key=env('OPENROUTER_API_KEY')
            self.model=env('OPENROUTER_MODEL','openrouter/free')
            if not (self.model.endswith(':free') or self.model=='openrouter/free'): raise ValueError('Only free OpenRouter models are permitted in this profile')
        elif self.provider=='gemini':
            self.base='https://generativelanguage.googleapis.com/v1beta/openai';self.key=env('GEMINI_API_KEY')
            self.model=env('GEMINI_MODEL','gemini-3.8-flash')
        elif self.provider!='organizer': raise ValueError('Unknown LLM_PROVIDER')
        self.calls=0; self.lock=threading.Lock()
    @property
    def configured(self): return bool(self.base and self.model and (self.provider in ('organizer','ollama') or self.key))
    def chat(self,messages,deadline):
        if not self.configured: raise RuntimeError('API_NOT_CONFIGURED')
        try: temperature=max(0,min(2,float(env('TEMPERATURE','0'))))
        except ValueError: temperature=0
        payload={'model':self.model,'messages':messages,'temperature':temperature,'max_tokens':env_int('MAX_TOKENS',2400,128,5000)}
        headers={'Content-Type':'application/json'}
        if self.key: headers['Authorization']='Bearer '+self.key
        endpoint=self.base+'/chat/completions'
        if self.provider=='ollama':
            endpoint=self.base.removesuffix('/v1')+'/api/chat'
            payload={'model':self.model,'messages':messages,'stream':False,'think':False,'format':'json','keep_alive':'10m','options':{'temperature':temperature,'num_predict':env_int('MAX_TOKENS',1200,128,5000),'num_ctx':env_int('OLLAMA_CONTEXT',8192,4096,32768)}}
        for attempt in range(3):
            left=deadline-time.monotonic()
            if left<3: raise TimeoutError('Deadline')
            req=urllib.request.Request(endpoint,json.dumps(payload).encode(),headers)
            try:
                with self.lock: self.calls+=1
                with urllib.request.urlopen(req,timeout=min(300 if self.provider=='ollama' else 60,left)) as r: result=json.load(r)
                return result['message']['content'] if self.provider=='ollama' else result['choices'][0]['message']['content']
            except urllib.error.HTTPError as e:
                if e.code not in (429,500,502,503,504) or attempt==2: raise RuntimeError('API_HTTP_'+str(e.code)) from None
            except (TimeoutError,urllib.error.URLError):
                if attempt==2: raise RuntimeError('API_UNAVAILABLE') from None
            time.sleep(min(2**attempt,max(0,deadline-time.monotonic())))
