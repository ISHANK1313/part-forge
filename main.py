#!/usr/bin/env python3
"""PartForge CLI — raw catalogue CSV -> Unilog 252-col Delivery Format.

Usage:
  python main.py --input "Unihack_ Sample Dataset - Input.csv" --out out/
                 [--limit N] [--workers 16] [--no-llm]

Deterministic-first: LLM (Gemini) adds evidenced enrichment when a key is
present in .env; every failure degrades to deterministic fields + audit flags.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from partforge import attributes, classify, descriptions, emit, enrich, features  # noqa: E402
from partforge import identity, io_loader, llm, packaging  # noqa: E402


def process_row(idx: int, row: dict, use_llm: bool) -> tuple[dict, dict]:
    """Run the S0..S8 chain for one row. Returns (output_row, audit_info)."""
    r = dict(row)

    ident = identity.resolve(r)
    r.update(ident)

    cls = classify.classify_row(r)
    r.update(cls)

    attrs, attr_conf = attributes.extract(r, use_llm=False)
    shared = enrich.enrich_row(r, [t["label"] for t in attrs]) if use_llm else None
    if shared is not None:
        attrs, attr_conf = attributes.extract(r, shared=shared)
    r["_attributes"] = attrs

    features.apply(r, use_llm=False, shared=shared)
    r["_packaging"] = packaging.parse(r)
    r.update(descriptions.build(r))

    out = emit.assemble_row(r)
    issues = emit.fix_row(out)

    from partforge.conf import needs_review
    flag, reason = needs_review(ident.get("confidence", 0.0),
                                cls.get("classpath_verified", False), len(attrs))
    reasons = [reason] if reason else []
    for iss in issues:
        reasons.append(f"{iss.column}:{iss.code}")

    audit = {
        "row": idx,
        "mpn": r.get("Mfg_Part_Num", ""),
        "flag": flag or bool(issues),
        "reasons": reasons,
        "identity_conf": ident.get("confidence", 0.0),
        "signal": ident.get("signal", ""),
        "classpath": cls.get("classpath", ""),
        "classpath_verified": cls.get("classpath_verified", False),
        "attr_count": len(attrs),
        "llm": shared is not None,
        "issues": issues,
        "dup": row.get("_dup_flag", ""),
    }
    return out, audit


def main() -> int:
    ap = argparse.ArgumentParser(description="PartForge enrichment pipeline")
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", default="out/")
    ap.add_argument("--limit", type=int, default=0, help="process only first N rows")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--no-llm", action="store_true", help="deterministic-only mode")
    args = ap.parse_args()

    llm.load_env()
    use_llm = (not args.no_llm) and llm.available()
    print(f"[partforge] llm={'ON (' + llm.model_name() + ')' if use_llm else 'OFF'} "
          f"workers={args.workers}")

    df = io_loader.load_input(args.input)
    rows = df.to_dict("records")
    if args.limit:
        rows = rows[: args.limit]
    total = len(rows)
    print(f"[partforge] input rows: {total} | duplicates flagged: "
          f"{df.attrs.get('duplicate_rows', 0)}")

    outputs: list[tuple[int, dict, dict]] = []
    t0 = time.time()
    done = 0

    def job(i: int, rec: dict):
        return i, *process_row(i, rec, use_llm)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = [ex.submit(job, i, rec) for i, rec in enumerate(rows)]
        for fut in as_completed(futures):
            try:
                outputs.append(fut.result())
            except Exception as exc:  # never kill the run for one bad row
                print(f"[partforge] ROW ERROR: {exc}")
            done += 1
            if done % 25 == 0 or done == total or (total <= 200 and done % 5 == 0):
                rate = done / max(time.time() - t0, 1e-6)
                eta = (total - done) / rate if rate > 0 else float("inf")
                print(f"  {done}/{total} rows ({rate:.2f} rows/s, ETA {eta:.0f}s)")

    outputs.sort(key=lambda t: t[0])
    out_rows = [o for _, o, _ in outputs]
    audits = [a for _, _, a in outputs]

    paths = emit.write_outputs(out_rows, audits, args.out)

    flagged = sum(1 for a in audits if a["flag"])
    with_llm = sum(1 for a in audits if a["llm"])
    avg_attrs = (sum(a["attr_count"] for a in audits) / len(audits)) if audits else 0
    print("[partforge] DONE in {:.1f}s".format(time.time() - t0))
    print(f"  output : {paths['xlsx']}")
    print(f"           {paths['csv']}")
    print(f"  audit  : {paths['audit']}")
    print(f"  flagged NEEDS_REVIEW: {flagged}/{len(audits)} | llm-enriched: "
          f"{with_llm}/{len(audits)} | avg attrs/row: {avg_attrs:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
