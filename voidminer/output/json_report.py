from __future__ import annotations

import orjson

from voidminer.models import Report


def write_json_report(path: str, report: Report) -> None:
    payload = report.model_dump(mode="json")
    with open(path, "wb") as fp:
        fp.write(orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS))
