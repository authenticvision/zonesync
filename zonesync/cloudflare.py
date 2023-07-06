from typing import Sequence, Tuple

import requests
import requests.auth

from zonesync import RR, Provider, ensure_trailing_dot, strip_trailing_dot


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
        ret = [json_to_rr(rrj) for rrj in resp.json()['result']]
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


def json_to_rr(rrj):
    content = ensure_trailing_dot(rrj['content'], rrj['type'])
    if rrj['type'] in ('MX', 'SRV'):
        content = f"{rrj['priority']} {content}"
    return RR(
        name=ensure_trailing_dot(rrj['name']),
        ttl=rrj['ttl'],
        type=rrj['type'],
        content=content,
        cf_zone_id=rrj['zone_id'],
        cf_id=rrj['id'],
    )


def rr_to_json(new: RR):
    j = dict(
        name=strip_trailing_dot(new.name),
        type=new.type,
        content=strip_trailing_dot(new.content, new.type),
        ttl=new.ttl,
        proxied=False,
    )
    if new.type in ('MX', 'SRV'):
        j['priority'], _, j['content'] = j['content'].partition(' ')
    return j
