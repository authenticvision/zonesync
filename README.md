# zonesync

Synchronize a zone file to [CloudFlare](https://cloudflare.com/) or
[INWX](https://inwx.de).

The `$ORIGIN` directive must be set to identify the zone.

**Warning: Be very careful when using this, API interactions are not well
tested and might produce unexpected records.**

# Usage

Quick dev setup install:

```sh
$ uv tool install -e .
```

```sh
$ export INWX_USER=… INWX_PASSWORD=…
$ zonesync -p inwx example.org.zone
None -> RR(name='something.example.org.', ttl=3600, type='CNAME', content='example.org.', cf_zone_id=None, cf_id=None)
None -> RR(name='something-else.example.org.', ttl=3600, type='CNAME', content='example.org.', cf_zone_id=None, cf_id=None)
Apply actions? (Y/n) y
adding RR(name='something.example.org.', ttl=3600, type='CNAME', content='example.org.', cf_zone_id=None, cf_id=None)
adding RR(name='something-else.example.org.', ttl=3600, type='CNAME', content='example.org.', cf_zone_id=None, cf_id=None)
```

## CloudFlare API token setup

Obtain a CloudFlare API Token

Go to `My Profile` -> `API Tokens` -> `Create Token`

Click on `Edit zone DNS -> Use template`

Set a `Token name` (including your name).

Under `Zone Resources` select `Include` `All zones`

`Continue to Summary` -> `Create Token`

Export it as `CLOUDFLARE_API_TOKEN` for zonesync to use.
