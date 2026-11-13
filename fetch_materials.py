"""Download public organizer materials. No authentication or API keys required."""
import concurrent.futures, pathlib, urllib.request, zipfile
p=pathlib.Path(__file__).parent/'data'; p.mkdir(exist_ok=True)
pairs=[('1cIgcdlHoEmJoPh-oBJRIE9-TzZfy7Jk2','demo_output.csv'),('10GQd7WmGaJgFA0l8jPquiOIfVHsHRIkt','demo_questions.csv'),('1ZoE5uQgOLxPnu0f5njH2qGPuqkSnH_1r','knowledge-base.zip'),('16VEQvoLjSGanImhg-6ATU3Km5Sih9pcF','allowed_requirements.txt')]
def get(pair):
 i,n=pair
 r=urllib.request.urlopen('https://drive.google.com/uc?export=download&id='+i, timeout=60)
 content=r.read(); (p/n).write_bytes(content)
 return n,len(content)
print(list(concurrent.futures.ThreadPoolExecutor().map(get,pairs)))
with zipfile.ZipFile(p/'knowledge-base.zip') as z:
 if z.testzip(): raise ValueError('Invalid knowledge base archive')
 print('Knowledge base verified:',len(z.namelist()),'files')

