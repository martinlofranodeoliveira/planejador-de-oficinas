"""CLI estática: leitura limitada, JSON estrito e falhas sem eco de entrada."""
import json
import math
import re
import sys

from .core import plan
from .errors import InputError

MAX_BYTES = 1048576
USAGE = "Uso: python -m planejador_oficinas INPUT.json [--max-nodes N]\n"


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise InputError("INVALID_INPUT")
        result[key] = value
    return result


def _constant(value):
    raise InputError("INVALID_INPUT")


def _float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InputError("INVALID_INPUT")
    return result


def _arguments(argv):
    if argv in (["--help"], ["-h"]):
        return None
    if len(argv) not in (1, 3) or not argv[0] or argv[0].startswith("-"):
        raise InputError("INVALID_INPUT")
    maximum = 20000
    if len(argv) == 3:
        if argv[1] != "--max-nodes" or re.fullmatch(r"[1-9][0-9]{0,5}", argv[2]) is None:
            raise InputError("INVALID_INPUT")
        maximum = int(argv[2])
        if not 1 <= maximum <= 200000:
            raise InputError("INVALID_INPUT")
    return argv[0], maximum


def main(argv=None):
    try:
        parsed = _arguments(list(sys.argv[1:] if argv is None else argv))
        if parsed is None:
            sys.stdout.write(USAGE)
            return 0
        filename, maximum = parsed
        with open(filename, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise InputError("INVALID_INPUT")
        document = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_pairs,
                              parse_constant=_constant, parse_float=_float)
        result = plan(document, max_nodes=maximum)
        if type(result) is not dict or result.get("status") not in {"scheduled", "unsatisfiable", "budget_exhausted"}:
            raise InputError("INVALID_INPUT")
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n"
        sys.stdout.write(encoded)
        return {"scheduled": 0, "unsatisfiable": 1, "budget_exhausted": 3}[result["status"]]
    except Exception:
        try:
            sys.stderr.write("INVALID_INPUT\n")
        except OSError:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
