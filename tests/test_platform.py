"""Exercise packaged entry point over an actual HTTP connection to a local API fixture."""
import csv,json,os,pathlib,shutil,subprocess,sys,tempfile,threading,unittest,zipfile
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer

class PlatformContract(unittest.TestCase):
    def test_four_file_archive_http_and_csv(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        requests=[]
        class API(BaseHTTPRequestHandler):
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                requests.append(body)
                context=json.loads(body['messages'][1]['content'])['CONTEXT']
                source=next(s for s in context if 'А-08' in s['title'])
                pid=next(k for k,v in source['paragraphs'].items() if v.startswith('3.1.'))
                decision={'status':'answered','verdict':'facts','selected':[source['id']+':'+pid],'reason':'none'}
                raw=json.dumps({'choices':[{'message':{'content':json.dumps(decision,ensure_ascii=False)}}]}).encode()
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),API)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                work=pathlib.Path(temp);data=work/'data';data.mkdir()
                archive=work/'entry.zip'
                with zipfile.ZipFile(archive,'w') as z:
                    for name in ('solution.py','core.py','engine_v4.py','requirements.txt'):z.write(root/name,name)
                with zipfile.ZipFile(archive) as z:
                    self.assertEqual(len(z.namelist()),4);z.extractall(work)
                shutil.copyfile(root/'data/knowledge-base.zip',data/'kb.zip')
                with (data/'questions.csv').open('w',encoding='utf-8',newline='') as f:
                    w=csv.writer(f);w.writerow(['id','question']);w.writerows([['а,1','Какая арендная плата по договору А-08/2024 Северный Склад?'],['б2','Пользователь: Северный Склад\nПользователь: Какая плата по А-08/2024?']])
                env=os.environ.copy();env.update(DATA_DIR=str(data),LLM_BASE_URL=f'http://127.0.0.1:{server.server_port}/v1',LLM_API_KEY='fixture-key',LLM_MODEL='fixture-model',LLM_PROVIDER='ollama',MAX_WORKERS='2')
                result=subprocess.run([sys.executable,'solution.py'],cwd=work,env=env,check=True,capture_output=True,timeout=30)
                with (work/'submission.csv').open(encoding='utf-8',newline='') as f:
                    reader=csv.DictReader(f);rows=list(reader);self.assertEqual(reader.fieldnames,['id','answer'])
                self.assertEqual([r['id'] for r in rows],['а,1','б2'])
                self.assertTrue(all('450 000' in r['answer'] and '[D01U001]' in r['answer'] and len(r['answer'])<=10000 for r in rows))
                self.assertEqual(len(requests),2);self.assertTrue(all(b['model']=='fixture-model' for b in requests))
                self.assertNotIn(b'fixture-key',result.stderr)
                report=json.loads((work/'run_report.json').read_text(encoding='utf-8'))
                self.assertEqual(report['statuses'],{'answered':2})
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
