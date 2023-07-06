import argparse
import os
import re
import zonesync
import zonesync.cloudflare
import zonesync.inwx
from zonesync import normalize_origin


def main():
    p = argparse.ArgumentParser(description="Synchronize a local zone file with Cloudflare")
    p.add_argument('-p', '--provider', choices=('cloudflare', 'inwx'), required=True)
    sp = p.add_subparsers(dest='cmd')
    syncp = sp.add_parser('sync')
    syncp.add_argument('zonefile', help="Zone file to sync. Must define $ORIGIN.")
    initp = sp.add_parser('init')
    initp.add_argument('zonefile', help="Zone file to create")
    initp.add_argument('origin', help="Zone to fetch records from")
    args = p.parse_args()

    match args.provider:
        case 'cloudflare':
            api = zonesync.cloudflare.CloudFlare(os.environ.get('CLOUDFLARE_API_TOKEN'))
        case 'inwx':
            api = zonesync.inwx.Inwx(os.environ['INWX_USER'], os.environ['INWX_PASSWORD'], os.environ.get('INWX_TOTP'))
        case _:
            raise RuntimeError("No supported provider matched existing NS records")

    match args.cmd:
        case 'sync':
            sync(api, args)
        case 'init':
            init(api, args)
        case _:
            raise KeyError(f"Unknown command {args.cmd!r}")


def init(api: zonesync.Provider, args):
    origin = normalize_origin(args.origin)
    remote, zone_id = api.load(origin)
    with open(args.zonefile, 'x') as f:
        print(f'$ORIGIN {origin}', file=f)
        for rr in filter(lambda rr: rr.type == 'NS', remote):
            print(f'{zonesync.shorten_name(rr.name, origin)}\t{rr.ttl}\tIN\t{rr.type}\t{rr.content}', file=f)
        print(file=f)
        for rr in zonesync.no_soa_or_ns(remote):
            print(f'{zonesync.shorten_name(rr.name, origin)}\t{rr.ttl}\tIN\t{rr.type}\t{rr.content}', file=f)


def sync(api: zonesync.Provider, args):
    local, origin = zonesync.load_file(args.zonefile)
    remote, zone_id = api.load(origin)
    local = zonesync.no_soa(local)
    if not api.want_self_ns_records():
        local = filter(lambda rr: not (rr.type == 'NS' and rr.name == origin), local)
    remote = zonesync.no_soa(remote)
    actions = zonesync.diff(remote, local)
    if len(actions) == 0:
        print("Nothing to do")
        return
    for old, new in actions:
        print(f"{old}->\n{new}")
    if input("Apply actions? (y/N) ") not in ('Y', 'y'):
        return

    for old, new in actions:
        if old is None:
            api.add(new, zone_id, origin)
        elif new is None:
            api.remove(old, zone_id, origin)
        else:
            api.update(old, new, zone_id, origin)
