#!/usr/bin/env python3
"""Google Drive file-scope helper; auth once, refresh locally, perform explicit operations."""
import argparse,base64,hashlib,json,os,secrets,tempfile,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
from http.server import HTTPServer,BaseHTTPRequestHandler
CLIENT=Path.home()/'dev/personal/automation/calendar-llm/credentials.json'
DIR=Path.home()/'.config/codex-google-drive'; TOKEN=DIR/'token.json'
SCOPE='https://www.googleapis.com/auth/drive.file'; EMAIL='petteri.r.raita@gmail.com'
def req(url,method='GET',data=None,headers=None,form=False):
 h=dict(headers or {}); body=None
 if data is not None:
  body=urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode();h['Content-Type']='application/x-www-form-urlencoded' if form else 'application/json'
 try:
  with urllib.request.urlopen(urllib.request.Request(url,data=body,headers=h,method=method),timeout=60) as r:return json.load(r)
 except urllib.error.HTTPError as e:
  try: msg=json.load(e).get('error',{}); msg=msg.get('message',str(msg)) if isinstance(msg,dict) else str(msg)
  except Exception: msg='Request rejected'
  raise RuntimeError(f'Google API HTTP {e.code}: {msg}') from None
def client():return json.loads(CLIENT.read_text())['installed']
def save(t):
 DIR.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(DIR,0o700);fd,tmp=tempfile.mkstemp(dir=DIR,prefix='.token-')
 try:
  with os.fdopen(fd,'w') as f:json.dump(t,f)
  os.replace(tmp,TOKEN);os.chmod(TOKEN,0o600)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def access(force=False):
 t=json.loads(TOKEN.read_text()); c=client()
 if force or t.get('expires_at',0)<time.time()+60:
  x=req(c['token_uri'],'POST',{'client_id':c['client_id'],'client_secret':c['client_secret'],'refresh_token':t['refresh_token'],'grant_type':'refresh_token'},form=True);t.update(x);t['expires_at']=time.time()+x.get('expires_in',3600);save(t)
 return t['access_token']
def call(path,method='GET',data=None):return req('https://www.googleapis.com/drive/v3/'+path,method,data,{'Authorization':'Bearer '+access()})
def auth():
 c=client();state=secrets.token_urlsafe(32);v=secrets.token_urlsafe(48);challenge=base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b'=').decode();result={}
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*a):pass
  def do_GET(self):
   q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
   if self.path.split('?')[0]!='/callback' or not secrets.compare_digest(q.get('state',[''])[0],state):self.send_error(400);return
   result.update({k:x[0] for k,x in q.items()});self.send_response(200);self.end_headers();self.wfile.write(b'Authorization received. Return to Codex.')
 with HTTPServer(('127.0.0.1',0),Handler) as server:
  server.timeout=1;redirect=f'http://127.0.0.1:{server.server_port}/callback';params={'client_id':c['client_id'],'redirect_uri':redirect,'response_type':'code','scope':'openid email '+SCOPE,'access_type':'offline','prompt':'consent','state':state,'code_challenge':challenge,'code_challenge_method':'S256','login_hint':EMAIL}
  print('AUTH_URL '+c['auth_uri']+'?'+urllib.parse.urlencode(params),flush=True);deadline=time.time()+900
  while not result and time.time()<deadline:server.handle_request()
  if 'code' not in result:raise RuntimeError('Authorization not completed: '+result.get('error','timeout'))
  t=req(c['token_uri'],'POST',{'client_id':c['client_id'],'client_secret':c['client_secret'],'code':result['code'],'code_verifier':v,'redirect_uri':redirect,'grant_type':'authorization_code'},form=True)
 if not t.get('refresh_token') or SCOPE not in t.get('scope','').split():raise RuntimeError('Refresh token or Drive permission missing; existing token preserved')
 info=req('https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+t['access_token']})
 if info.get('email','').lower()!=EMAIL or not info.get('email_verified'):raise RuntimeError('Wrong account; existing token preserved')
 t['expires_at']=time.time()+t.get('expires_in',3600);t['account_email']=info['email'];save(t);access(force=True);print('AUTH_AND_REFRESH_VERIFIED',flush=True)
def upload(parent,file):
 p=Path(file); size=p.stat().st_size;headers={'Authorization':'Bearer '+access(),'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Type':'application/octet-stream','X-Upload-Content-Length':str(size)}
 request=urllib.request.Request('https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable',data=json.dumps({'name':p.name,'parents':[parent]}).encode(),headers=headers,method='POST')
 with urllib.request.urlopen(request,timeout=60) as response:location=response.headers['Location']
 import http.client
 u=urllib.parse.urlsplit(location);conn=http.client.HTTPSConnection(u.netloc,timeout=600);conn.putrequest('PUT',u.path+'?'+u.query);conn.putheader('Content-Type','application/octet-stream');conn.putheader('Content-Length',str(size));conn.endheaders()
 with p.open('rb') as f:
  while chunk:=f.read(1024*1024):conn.send(chunk)
 r=conn.getresponse();data=r.read();conn.close()
 if r.status not in (200,201):raise RuntimeError('Upload failed: HTTP '+str(r.status))
 print(json.dumps(json.loads(data)))
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True);sub.add_parser('auth');sub.add_parser('verify');l=sub.add_parser('list');l.add_argument('folder');u=sub.add_parser('upload');u.add_argument('folder');u.add_argument('file');a=p.parse_args()
 if a.cmd=='auth':auth()
 elif a.cmd=='verify':access(force=True);print('REFRESH_OK');print(json.dumps(call('about?fields=user(displayName,emailAddress)')))
 elif a.cmd=='list':
  q="'"+a.folder+"' in parents and trashed = false";print(json.dumps(call('files?'+urllib.parse.urlencode({'q':q,'fields':'files(id,name,size,webViewLink)','pageSize':100}))))
 elif a.cmd=='upload':upload(a.folder,a.file)
if __name__=='__main__':
 try:main()
 except Exception as e:print('ERROR:',str(e),flush=True);raise SystemExit(1)
