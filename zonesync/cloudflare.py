from typing import Sequence, Tuple

import requests
import requests.auth

from zonesync import RR, Provider


class FuckOffAuth(requests.auth.AuthBase):
    """
    Prevent requests from using the netrc entry as basic auth, overriding the
    custom Authorization header
    """

    def __call__(self, r):
        return r


class CloudFlare(Provider):
    def __init__(self, api_token):
        if not api_token:
            raise ValueError("CloudFlare API Token required")
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

    def remove(self, old, zone_id, origin):
        assert old.cf_id is not None
        print(f"removing {old}")
        resp = self.session.delete(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{old.cf_id}')
        resp.raise_for_status()

    def update(self, old, new, zone_id, origin):
        assert old.cf_id is not None
        print(f"updating {old} to {new}")
        resp = self.session.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{old.cf_id}', json=rr_to_json(new))
        resp.raise_for_status()

    def add(self, new, zone_id, origin):
        print(f"adding {new}")
        resp = self.session.post(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records', json=rr_to_json(new))
        resp.raise_for_status()


def rr_to_json(new):
    return dict(
        name=new.name,
        type=new.type,
        content=new.content,
        ttl=new.ttl,
        proxied=False,
    )
