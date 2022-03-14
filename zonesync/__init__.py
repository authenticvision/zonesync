#!/usr/bin/env python3
import dataclasses
import typing
from typing import Optional, Iterable, Tuple, Iterator
import re


@dataclasses.dataclass(order=True, frozen=True)
class RR:
    name: str
    ttl: int
    type: str
    content: str
    cf_zone_id: Optional[str] = dataclasses.field(default=None, compare=False)
    cf_id: Optional[str] = dataclasses.field(default=None, compare=False)

    def json(self):
        return {
            "name": self.name,
            "ttl": self.ttl,
            "type": self.type,
            "content": self.content,
            "proxied": False
        }


def load_file(fn, origin=None):
    with open(fn) as f:
        return parse(f, origin)


rr_re = re.compile(r'(?P<name>[a-z0-9.@-]+)\s+(?P<ttl>\d+)\s+IN\s+(?P<type>A|AAAA|CNAME|NS|SOA)\s+(?P<content>.*)')
comment_re = re.compile(r'^$|^\s*;')
origin_re = re.compile(r'^\$ORIGIN\s+(?P<name>[a-z0-9.@-]+)')


def parse(f: Iterable[str], origin: str = None) -> Tuple[typing.Sequence[RR], typing.Annotated[str, "origin"]]:
    ret = []
    if origin is not None and origin[-1] != '.':
        origin += '.'
    for l in map(str.strip, f):
        if comment_re.match(l):
            continue
        elif m := origin_re.match(l):
            if origin is not None and origin != m.group('name'):
                raise ValueError(f"$ORIGIN ({m.group('name')!r}) does not match previously set origin ({origin!r})")
            origin = m.group('name')
            if origin[-1] != '.':
                raise ValueError(f"$ORIGIN ({origin!r}) does not end with a dot")
        elif m := rr_re.match(l):
            if origin is None:
                raise ValueError("$ORIGIN is missing")
            rr = RR(
                name=m.group('name'),
                ttl=int(m.group('ttl')),
                type=m.group('type'),
                content=m.group('content'),
            )
            ret.append(normalize_rr(rr, origin))
        else:
            raise ValueError(f"Unknown line encountered: {l!r}")
    return ret, origin


def normalize_rr(rr, origin):
    if rr.name == '@':
        rr = dataclasses.replace(rr, name=origin)
    elif not rr.name.endswith(origin):
        rr = dataclasses.replace(rr, name=rr.name + '.' + origin)
    return rr


def no_soa_or_ns(rrs: Iterable[RR]) -> Iterator[RR]:
    return filter(lambda rr: rr.type not in ('SOA', 'NS'), rrs)


OldRR: typing.TypeAlias = Optional[RR]
NewRR: typing.TypeAlias = Optional[RR]


def diff(old: Iterable[RR], new: Iterable[RR]) -> typing.Sequence[Tuple[OldRR, NewRR]]:
    return list(diff_generator(old, new))


def diff_generator(old: Iterable[RR], new: Iterable[RR]) -> Iterable[Tuple[OldRR, NewRR]]:
    new = set(new)
    old = set(old)
    added = new - old
    removed = old - new
    rem_it = iter(sorted(removed))
    r = next(rem_it, None)
    for a in sorted(added):
        while r and r.name < a.name:
            yield r, None
            r = next(rem_it, None)
        if r and r.name == a.name:
            yield r, a
            r = next(rem_it, None)
        else:
            yield None, a
    if r:
        yield r, None
    for r in rem_it:
        yield r, None
