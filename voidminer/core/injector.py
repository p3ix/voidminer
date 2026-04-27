from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def inject_query_param(url: str, parameter: str, payload: str) -> str:
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    query_pairs.append((parameter, payload))
    new_query = urlencode(query_pairs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))
