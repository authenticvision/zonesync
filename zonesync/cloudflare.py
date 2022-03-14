import netrc
import requests
import requests.auth

from zonesync import RR


class FuckOffAuth(requests.auth.AuthBase):
    """
    Prevent requests from using the netrc entry as basic auth, overriding the
    custom Authorization header
    """

    def __call__(self, r):
        return r


class CloudFlare:
    def __init__(self, api_token=None):
        if api_token is None:
            api_token = netrc.netrc().authenticators('api.cloudflare.com')[2]
        self.session = s = requests.Session()
        s.headers['Authorization'] = f'Bearer {api_token}'
        s.auth = FuckOffAuth()

    def load(self, origin):
        ret = []
        resp = self.session.get(f'https://api.cloudflare.com/client/v4/zones', params={'name': origin})
        zone_id = resp.json()['result'][0]['id']
        resp = self.session.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?per_page=5000')
        for rrj in resp.json()['result']:
            ret.append(RR(
                name=rrj['name'] + '.',
                ttl=rrj['ttl'],
                type=rrj['type'],
                content=rrj['content'] + ('.' if rrj['type'] == 'CNAME' else ''),
                cf_zone_id=zone_id,
                cf_id=rrj['id'],
            ))
        return ret, zone_id

    def remove(self, old, zone_id):
        assert old.cf_id is not None
        print(f"removing {old}")
        resp = self.session.delete(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{old.cf_id}')
        resp.raise_for_status()

    def update(self, old, new, zone_id):
        assert old.cf_id is not None
        print(f"updating {old} to {new}")
        resp = self.session.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{old.cf_id}', json=new.json())
        resp.raise_for_status()

    def add(self, new, zone_id):
        print(f"adding {new}")
        resp = self.session.post(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records', json=new.json())
        resp.raise_for_status()

    def apply(self, actions, zone_id):
        for old, new in actions:
            if old is None:
                self.add(new, zone_id)
            elif new is None:
                self.remove(old, zone_id)
            else:
                self.update(old, new, zone_id)
