#!/usr/bin/env python3
import dataclasses
from typing import Optional

import requests
import netrc
import re

api_token = netrc.netrc().authenticators('api.cloudflare.com')[2]


rr_re = re.compile(r'(?P<name>[a-z0-9.@-]+)\s+(?P<ttl>\d+)\s+IN\s+(?P<type>A|AAAA|CNAME|NS|SOA)\s+(?P<content>.*)')
comment_re = re.compile(r'^$|^\s*;')


@dataclasses.dataclass(order=True, frozen=True)
class RR:
    name: str
    ttl: int
    type: str
    content: str
    cf_id: Optional[str] = dataclasses.field(compare=False)


s = requests.Session()
s.headers['Authorization'] = f'Bearer {api_token}'


class FuckOffAuth(requests.auth.AuthBase):
    """
    Prevent requests from using the netrc entry as basic auth, overriding the
    custom Authorization header
    """

    def __call__(self, r):
        return r


s.auth = FuckOffAuth()


def load_cf(origin):
    resp = s.get(f'https://api.cloudflare.com/client/v4/zones', params={'name': origin})
    zone_id = resp.json()['result'][0]['id']
    resp = s.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?per_page=5000')
    for rrj in resp.json()['result']:
        yield RR(
            name=rrj['name'] + '.',
            ttl=rrj['ttl'],
            type=rrj['type'],
            content=rrj['content'] + ('.' if rrj['type'] == 'CNAME' else ''),
            cf_id=rrj['id'],
        )


def load_file(fn, origin):
    with open(fn) as f:
        yield from parse(f, origin)


def parse(f, origin):
    if origin[-1] != '.':
        origin += '.'
    for l in map(str.strip, f):
        if comment_re.match(l):
            continue
        if m := rr_re.match(l):
            rr = RR(
                name=m.group('name'),
                ttl=int(m.group('ttl')),
                type=m.group('type'),
                content=m.group('content'),
                cf_id=None,
            )
            yield patch_rr(rr, origin)
        else:
            print(l)


def patch_rr(rr, origin):
    if rr.name == '@':
        rr = dataclasses.replace(rr, name=origin)
    elif not rr.name.endswith(origin):
        rr = dataclasses.replace(rr, name=rr.name + '.' + origin)
    return rr


def no_soa_or_ns(rrs):
    return filter(lambda rr: rr.type not in ('SOA', 'NS'), rrs)


class CF:
    def remove(self, rr):
        print(f"removing {rr}")

    def update(self, old, new):
        print(f"updating {old} to {new}")

    def add(self, rr):
        print(f"adding {rr}")


cf = CF()

if __name__ == '__main__':
    local = set(no_soa_or_ns(load_file('example.org.zone', 'example.org')))
    remote = set(no_soa_or_ns(load_cf('example.org')))
    added = local - remote
    for rr in added:
        print('+', rr)
    removed = remote - local
    for rr in removed:
        print('-', rr)

    rem_it = iter(sorted(removed))
    r = next(rem_it)
    for a in sorted(added):
        while r and (r.name, r.type) < (a.name, a.type):
            cf.remove(r)
            r = next(rem_it, None)
        if r and (r.name, r.type) == (a.name, a.type):
            cf.update(r, a)
            r = next(rem_it, None)
        else:
            cf.add(a)

    if r:
        cf.remove(r)

    for r in rem_it:
        cf.remove(r)

