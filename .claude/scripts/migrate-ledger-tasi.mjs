#!/usr/bin/env node
// One-time, IDEMPOTENT migration: rename tracker-ledger wave tags W1/W2/W3 -> TASI-W1/TASI-W2/TASI-W3
// in the `source` and `first_source` fields. States/journeys are computed at report time from these
// tags, so no other field changes. See research/spec/decisions.md D-2026-07-02-05.
//   Usage: node .claude/scripts/migrate-ledger-tasi.mjs [ledgerPath]
// Idempotent: after the first run no value is exactly "W1"/"W2"/"W3", so re-running changes 0 tags.
import { readFileSync, writeFileSync } from "node:fs";

const path = process.argv[2] || ".claude/outputs/saudi-tracker.jsonl";
const before = readFileSync(path, "utf8");
const RE = /"(source|first_source)":"W([123])"/g;
const changed = (before.match(RE) || []).length;
const after = before.replace(RE, '"$1":"TASI-W$2"');
writeFileSync(path, after);
console.log(`migrated ${changed} wave tag(s) (source + first_source) in ${path}`);
