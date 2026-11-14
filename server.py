import json, os
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from core import Corpus
from engine_v3 import LegalAssistant

bot=LegalAssistant(Corpus())
class Handler(BaseHTTPRequestHandler):
    def send(self,code,body,kind='application/json; charset=utf-8'):
        raw=body.encode('utf-8'); self.send_response(code); self.send_header('Content-Type',kind); self.send_header('Content-Length',str(len(raw))); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/': return self.send(200,Path('web/index.html').read_text(encoding='utf-8'),'text/html; charset=utf-8')
        static={'/styles.css':'text/css; charset=utf-8','/app.js':'application/javascript; charset=utf-8','/demo.json':'application/json; charset=utf-8','/presentation.pdf':'application/pdf','/deck.html':'text/html; charset=utf-8','/slides.json':'application/json; charset=utf-8','/showcase-preview.png':'image/png'}
        if path in static:
            file=Path('web')/path[1:]
            if not file.exists():return self.send(404,'{}')
            if path.endswith(('.pdf','.png')):
                raw=file.read_bytes();self.send_response(200);self.send_header('Content-Type',static[path]);self.send_header('Content-Length',str(len(raw)));self.end_headers();return self.wfile.write(raw)
            return self.send(200,file.read_text(encoding='utf-8'),static[path])
        if path=='/api/health': return self.send(200,json.dumps({'ok':True,'model_configured':bot.gateway.configured,'provider':bot.gateway.provider,'model':bot.gateway.model,'documents':len(bot.corpus.docs),'chunks':len(bot.index.units),'removed_instructions':bot.corpus.removed,'corpus_sha256':bot.corpus.fingerprint}))
        if path=='/api/documents': return self.send(200,json.dumps(bot.corpus.docs,ensure_ascii=False))
        return self.send(404,'{}')
    def do_POST(self):
        if self.path!='/api/ask': return self.send(404,'{}')
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size<1 or size>40000: return self.send(413,'{}')
            body=json.loads(self.rfile.read(size)); question=body['question']
            if not isinstance(question,str) or not question.strip() or len(question)>16000: raise ValueError()
            self.send(200,json.dumps(bot.answer(question),ensure_ascii=False))
        except (ValueError,KeyError): self.send(400,json.dumps({'error':'Некорректный запрос'}))
    def log_message(self,*args): pass

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8080'))),Handler).serve_forever()
