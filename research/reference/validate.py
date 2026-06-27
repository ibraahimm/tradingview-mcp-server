#!/usr/bin/env python3
"""Integrity gate for the point-in-time reference layer (stdlib-only, CI-friendly).

Validates a directory of reference tables against the Frictionless-style schemas in
./schema/, plus the relational + temporal invariants the schemas cannot express
(foreign keys, no overlapping validity intervals, ticker concurrency, delisting
completeness, corporate-action shape).

    python research/reference/validate.py                       # validate ./seed
    python research/reference/validate.py --data path/to/prod   # validate a production dir
    python research/reference/validate.py --require-production   # fail if any row is illustrative

Exit 0 = all checks pass; non-zero = at least one violation. Designed to run in CI on every
change to the reference data.

NOTE ON SEED vs PRODUCTION: by default this validates the illustrative ./seed scaffolding so the
schemas stay coherent. Production reference data lives in a SEPARATE directory, must carry a real
`source` (never 'illustrative') and a `last_reviewed` date, and must pass `--require-production`.
"""
from __future__ import annotations
import csv, json, sys, re
from datetime import date
from pathlib import Path

REF = Path(__file__).resolve().parent
SCHEMA_DIR = REF / "schema"
OPEN_END = date(9999, 1, 1)

# Row-level invariants the schema JSON cannot express, keyed by table name.
def inv_security_master(rows, _all):
    out = []
    for r in rows:
        if r["delist_date"]:
            for f in ("delist_reason", "terminal_value", "terminal_value_basis"):
                if not r[f]:
                    out.append(f"security_master[{r['sec_id']}]: delist_date set but {f} empty")
    return out

def inv_corporate_actions(rows, _all):
    out = []
    for r in rows:
        if bool(r["ratio"]) == bool(r["amount"]):
            out.append(f"corporate_actions[{r['sec_id']},{r['ca_type']},{r['ex_date']}]: "
                       "exactly one of {ratio, amount} must be set")
    return out

def inv_ticker_concurrency(rows, _all):
    """(ticker, date) must map to at most one sec_id — codes may be reused, never concurrently."""
    out, by_ticker = [], {}
    for r in rows:
        by_ticker.setdefault(r["ticker"], []).append(
            (date.fromisoformat(r["valid_from"]),
             date.fromisoformat(r["valid_to"]) if r["valid_to"] else OPEN_END, r["sec_id"]))
    for tk, iv in by_ticker.items():
        iv.sort()
        for a, b in zip(iv, iv[1:]):
            if a[1] > b[0] and a[2] != b[2]:
                out.append(f"ticker_map: code {tk} concurrently maps to {a[2]} and {b[2]}")
    return out

ROW_INVARIANTS = {
    "security_master": [inv_security_master],
    "corporate_actions": [inv_corporate_actions],
    "ticker_map": [inv_ticker_concurrency],
}


def load_schema(p: Path):
    doc = json.loads(p.read_text())
    return {
        "name": doc["name"],
        "fields": doc["schema"]["fields"],
        "pk": doc.get("primaryKey", []),
        "fks": doc["schema"].get("foreignKeys", []),
        "missing": doc.get("missingValues", [""]),
    }


def coerce_ok(value, ftype):
    try:
        if ftype == "date":
            date.fromisoformat(value)
        elif ftype == "number":
            float(value)
        elif ftype == "boolean":
            return value in ("true", "false")
        elif ftype == "datetime":
            # accept ISO datetime; lenient
            return bool(value)
        return True
    except ValueError:
        return False


def validate_table(schema, rows):
    fails, name = [], schema["name"]
    fields = {f["name"]: f for f in schema["fields"]}
    header = set(rows[0].keys()) if rows else set()

    for fn in fields:
        if rows and fn not in header:
            fails.append(f"{name}: missing required column '{fn}'")

    # field-level checks
    for i, r in enumerate(rows):
        for fn, f in fields.items():
            raw = r.get(fn, "")
            c = f.get("constraints", {})
            null = raw in schema["missing"]
            if null:
                if c.get("required"):
                    fails.append(f"{name}[row {i}].{fn}: required but empty")
                continue
            if "pattern" in c and not re.match(c["pattern"], raw):
                fails.append(f"{name}[row {i}].{fn}: '{raw}' fails pattern {c['pattern']}")
            if "enum" in c and raw not in c["enum"]:
                fails.append(f"{name}[row {i}].{fn}: '{raw}' not in {c['enum']}")
            if not coerce_ok(raw, f.get("type", "string")):
                fails.append(f"{name}[row {i}].{fn}: '{raw}' is not a valid {f.get('type')}")

    # uniqueness (declared) + primary key
    for fn, f in fields.items():
        if f.get("constraints", {}).get("unique"):
            seen = [r[fn] for r in rows if r.get(fn)]
            if len(seen) != len(set(seen)):
                fails.append(f"{name}.{fn}: values not unique")
    if schema["pk"]:
        keys = [tuple(r[k] for k in schema["pk"]) for r in rows]
        if len(keys) != len(set(keys)):
            fails.append(f"{name}: primary key {schema['pk']} not unique")

    # validity-interval non-overlap (any table whose PK includes valid_from)
    if "valid_from" in schema["pk"] and any(f["name"] == "valid_to" for f in schema["fields"]):
        group_fields = [k for k in schema["pk"] if k != "valid_from"]
        groups = {}
        for r in rows:
            g = tuple(r[k] for k in group_fields)
            groups.setdefault(g, []).append(
                (date.fromisoformat(r["valid_from"]),
                 date.fromisoformat(r["valid_to"]) if r["valid_to"] else OPEN_END))
        for g, iv in groups.items():
            iv.sort()
            for a, b in zip(iv, iv[1:]):
                if a[1] > b[0]:
                    fails.append(f"{name}: overlapping intervals for {dict(zip(group_fields, g))}: {a} & {b}")
            for vf, vt in iv:
                if vf >= vt:
                    fails.append(f"{name}: valid_from {vf} >= valid_to {vt} for {dict(zip(group_fields, g))}")
    return fails


def validate_fks(schema, rows, tables):
    fails = []
    for fk in schema["fks"]:
        field = fk["fields"]
        ref = fk["reference"]
        ref_rows = tables.get(ref["resource"], [])
        ref_vals = {r[ref["fields"]] for r in ref_rows}
        for i, r in enumerate(rows):
            v = r.get(field, "")
            if v and v not in ref_vals:
                fails.append(f"{schema['name']}[row {i}].{field}: FK '{v}' not in {ref['resource']}.{ref['fields']}")
    return fails


def main() -> int:
    args = sys.argv[1:]
    data_dir = REF / "seed"
    require_prod = "--require-production" in args
    if "--data" in args:
        data_dir = Path(args[args.index("--data") + 1])

    schemas = {s["name"]: s for s in (load_schema(p) for p in sorted(SCHEMA_DIR.glob("*.schema.json")))}
    tables, fails = {}, []
    for name, schema in schemas.items():
        csv_path = data_dir / f"{name}.csv"
        if not csv_path.exists():
            fails.append(f"{name}: data file {csv_path} not found")
            continue
        with csv_path.open() as fh:
            tables[name] = list(csv.DictReader(fh))

    for name, schema in schemas.items():
        rows = tables.get(name, [])
        fails += validate_table(schema, rows)
        for inv in ROW_INVARIANTS.get(name, []):
            fails += inv(rows, tables)

    for name, schema in schemas.items():
        fails += validate_fks(schema, tables.get(name, []), tables)

    if require_prod:
        for name, rows in tables.items():
            for i, r in enumerate(rows):
                if r.get("source", "") == "illustrative":
                    fails.append(f"{name}[row {i}]: source='illustrative' but --require-production is set "
                                 "(seed scaffolding must not be used as production reference data)")

    mode = "PRODUCTION" if require_prod else "seed/illustrative"
    if fails:
        print(f"FAIL [{mode}] ({len(fails)} issue(s)) in {data_dir}:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"PASS [{mode}]: {len(schemas)} table(s) in {data_dir}; "
          "PK/FK/enum/pattern/interval/concurrency invariants OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
