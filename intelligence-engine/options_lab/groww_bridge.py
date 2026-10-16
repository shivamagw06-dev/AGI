"""Use the existing finance service's Groww credentials without copying them."""
import json
import os
import urllib.request

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def request(action,params):
    base=os.getenv('FINANCE_BACKEND_URL','https://finance-news-backend-19i5.onrender.com').rstrip('/')
    if not base.startswith('https://'):raise ValueError('HTTPS required for broker data bridge')
    token=os.getenv('INTELLIGENCE_ENGINE_TOKEN','').strip()
    if len(token)<10:raise ValueError('Service authentication unavailable')
    req=urllib.request.Request(base+'/api/market/internal/nifty-groww',data=json.dumps(dict(action=action,params=params)).encode(),
        headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    with urllib.request.build_opener(NoRedirect).open(req,timeout=35) as r:return json.load(r)


class FeedAuthorization:
    def generate_socket_token(self,key_pair):
        return request('socket',dict(socketKey=key_pair.public_key.decode('utf-8')))
