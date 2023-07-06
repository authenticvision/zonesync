import os
from typing import Sequence, Tuple

import requests
import requests.auth

from zonesync import RR, Provider, ensure_trailing_dot, strip_origin, Origin, strip_trailing_dot


class Inwx(Provider):
    def __init__(self, user, password, totp=None):
        self.session = requests.Session()
        resp = self._api_call('account.login', **{'user': user, 'pass': password})  # 'pass' is a keyword
        if resp.get('tfa') == 'GOOGLE-AUTH':
            if totp is None:
                totp = input("Enter TOTP code: ")
            self._api_call('account.unlock', tan=totp)

    def _api_call(self, method, **params):
        resp = self.session.post('https://api.domrobot.com/jsonrpc/', json=dict(method=method, params=params))
        resp.raise_for_status()
        j = resp.json()
        if j['code'] != 1000:
            raise RuntimeError(f"error from inwx api: {j.get('reason') or resp.text}")
        return j.get('resData')

    def load(self, origin: str):
        origin = origin.rstrip('.')
        resp = self._api_call('nameserver.info', domain=origin)
        ret = [json_to_rr(rrj) for rrj in resp['record']]
        return ret, resp['roId']

    def remove(self, old: RR, zone_id, origin):
        assert old.cf_id is not None
        print(f"removing {old}")
        self._api_call('nameserver.deleteRecord', id=old.cf_id)

    def update(self, old: RR, new: RR, zone_id, origin):
        assert old.cf_id is not None
        print(f"updating {old} to {new}")
        j = rr_to_json(new, origin)
        j['id'] = old.cf_id
        self._api_call('nameserver.updateRecord', **j)

    def add(self, new: RR, zone_id, origin):
        print(f"adding {new}")
        j = rr_to_json(new, origin)
        j['roId'] = zone_id
        self._api_call('nameserver.createRecord', **j)


def json_to_rr(rrj):
    content = ensure_trailing_dot(rrj['content'], rrj['type'])
    if rrj['type'] in ('MX', 'SRV'):
        content = f"{rrj['prio']} {content}"
    elif rrj['type'] == 'TXT' and not rrj['content'].startswith('"'):
        content = f'"{content}"'
        # TODO: might cause false positive difference if local values are unquoted.
        # submitting a quoted single value will cause inwx to unquote it.
    return RR(
        name=ensure_trailing_dot(rrj['name']),  # already is a full domain including origin but without trailing dot
        ttl=rrj['ttl'],
        type=rrj['type'],
        content=content,
        cf_id=rrj['id'],
    )


def rr_to_json(new: RR, origin: Origin):
    j = dict(
        name=strip_origin(new.name, origin),  # must be a subdomain only for submitting
        type=new.type,
        content=strip_trailing_dot(new.content, new.type),
        ttl=new.ttl,
    )
    if new.type in ('MX', 'SRV'):
        j['priority'], _, j['content'] = j['content'].partition(' ')
    return j
