from typing import Sequence, Tuple

import requests
import requests.auth

from zonesync import RR, Provider, ZonesyncError, ensure_trailing_dot, strip_trailing_dot


class FuckOffAuth(requests.auth.AuthBase):
    """
    Prevent requests from using the netrc entry as basic auth, overriding the
    custom Authorization header
    """

    def __call__(self, r):
        return r


class Cloudflare(Provider):
    def __init__(self, api_token):
        if not api_token:
            raise ZonesyncError("Cloudflare API Token required (set CLOUDFLARE_API_TOKEN)")
        self.session = s = requests.Session()
        s.headers['Authorization'] = f'Bearer {api_token}'
        s.auth = FuckOffAuth()

    def load(self, origin):
        resp = self.session.get(f'https://api.cloudflare.com/client/v4/zones', params={'name': origin})
        zones = result(resp, f"looking up zone {origin}")
        if not zones:
            raise ZonesyncError(f"No Cloudflare zone named {origin}")
        zone_id = zones[0]['id']
        resp = self.session.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?per_page=5000')
        ret = [json_to_rr(rrj, zone_id) for rrj in result(resp, f"listing records of {origin}")]
        return ret, zone_id

    def remove(self, old, zone_id, origin):
        assert old.cf_id is not None
        print(f"removing {old}")
        resp = self.session.delete(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{old.cf_id}')
        result(resp, f"removing {old}")

    def update(self, old, new, zone_id, origin):
        assert old.cf_id is not None
        print(f"updating {old} to {new}")
        resp = self.session.put(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{old.cf_id}', json=rr_to_json(new))
        result(resp, f"updating {old}")

    def add(self, new, zone_id, origin):
        print(f"adding {new}")
        resp = self.session.post(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records', json=rr_to_json(new))
        result(resp, f"adding {new}")

    def want_self_ns_records(self) -> bool:
        return False


def result(resp, what):
    """
    Return the `result` of a Cloudflare API response, or raise a readable error
    """
    try:
        j = resp.json()
    except ValueError:
        j = {}

    if resp.ok and j.get('success') and j.get('result') is not None:
        return j['result']

    errors = "; ".join(f"{e.get('message')} (code {e.get('code')})" for e in j.get('errors') or [])
    if not errors:
        errors = resp.text.strip() or f"HTTP {resp.status_code}"
    raise ZonesyncError(f"Cloudflare API error while {what}: {errors}")


def json_to_rr(rrj, zone_id):
    content = ensure_trailing_dot(rrj['content'], rrj['type'])
    if rrj['type'] in ('MX', 'SRV'):
        content = f"{rrj['priority']} {content}"

    if rrj['proxied']:
        ttl = 0 # sentinel for rr_to_json
    else:
        ttl = rrj['ttl']

    return RR(
        name=ensure_trailing_dot(rrj['name']),
        ttl=ttl,
        type=rrj['type'],
        content=content,
        cf_zone_id=zone_id,
        cf_id=rrj['id'],
    )


def rr_to_json(new: RR):
    ttl = new.ttl
    proxied = False
    if ttl == 0:
        ttl = 1 # automatic is the only value permitted for proxied records
        proxied = True

    j = dict(
        name=strip_trailing_dot(new.name),
        type=new.type,
        content=strip_trailing_dot(new.content, new.type),
        ttl=ttl,
        proxied=proxied,
    )

    if new.type in ('MX', 'SRV'):
        j['priority'], _, j['content'] = j['content'].partition(' ')

    return j
