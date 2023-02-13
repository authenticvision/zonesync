import os
from typing import Sequence, Tuple

import requests
import requests.auth

from zonesync import RR, Provider


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
    content = rrj['content']
    if rrj['type'] in ('CNAME', 'ALIAS'):
        content += '.'
    elif rrj['type'] in ('MX', 'SRV'):
        content = f"{rrj['prio']} {content}."
    elif rrj['type'] == 'TXT' and not rrj['content'].startswith('"'):
        content = f'"{content}"'
        # TODO: might cause false positive difference if local values are unquoted.
        # submitting a quoted single value will cause inwx to unquote it.
    return RR(
        name=rrj['name'] + '.',
        ttl=rrj['ttl'],
        type=rrj['type'],
        content=content,
        cf_id=rrj['id'],
    )


def rr_to_json(new, origin):
    # strip the origin, inwx doesn't like that
    name = new.name[:-len(origin)]
    if name != '':
        # if it's a subdomain, strip the trailing dot
        name = name[:-1]
    j = dict(
        name=name,
        type=new.type,
        content=new.content,
        ttl=new.ttl,
    )
    if new.content in ('CNAME', 'ALIAS'):
        j['content'] = new.content[:-1]  # we don't need the trailing dot
    elif new.type in ('MX', 'SRV'):
        idx = new.content.index(' ')
        j['content'] = new.content[idx + 1:-1]  # strip the trailing dot on the host for the api
        j['prio'] = int(new.content[:idx])
    return j
