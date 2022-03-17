import argparse
import os
import zonesync
import zonesync.cloudflare


def main():
    p = argparse.ArgumentParser(description="Synchronize a local zone file with Cloudflare")
    p.add_argument('zone', help="Zone file to sync. Must define $ORIGIN.")
    args = p.parse_args()
    cf = zonesync.cloudflare.CloudFlare(os.environ.get('CLOUDFLARE_API_TOKEN'))
    local, origin = zonesync.load_file(args.zone)
    local = zonesync.no_soa_or_ns(local)
    remote, zone_id = cf.load(origin)
    actions = zonesync.diff(remote, local)
    if len(actions) == 0:
        print("Nothing to do")
        return
    for old, new in actions:
        print(old, '->', new)
    if input("Apply actions? (y/N) ") not in ('Y', 'y'):
        return
    cf.apply(actions, zone_id)
