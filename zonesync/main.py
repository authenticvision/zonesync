import argparse
import os
import zonesync
import zonesync.cloudflare
import zonesync.inwx


def main():
    p = argparse.ArgumentParser(description="Synchronize a local zone file with Cloudflare")
    p.add_argument('zone', help="Zone file to sync. Must define $ORIGIN.")
    args = p.parse_args()
    local, origin = zonesync.load_file(args.zone)
    if any('ns.cloudflare.com' in rr.content for rr in local if rr.type == 'NS'):
        api = zonesync.cloudflare.CloudFlare(os.environ.get('CLOUDFLARE_API_TOKEN'))
    else:
        api = zonesync.inwx.Inwx(os.environ['INWX_USER'], os.environ['INWX_PASSWORD'])
    remote, zone_id = api.load(origin)
    local = zonesync.no_soa_or_ns(local)
    remote = zonesync.no_soa_or_ns(remote)
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
