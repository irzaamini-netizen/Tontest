import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .engine import scan, write_report
from .compare import compare
from .chain_audit import audit_wallet, write_chain_report
from .batch import audit_batch


def main():
    parser = argparse.ArgumentParser(prog="tonsec")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor")

    scan_parser = sub.add_parser("scan")
    scan_parser.add_argument("target")
    scan_parser.add_argument("--out", required=True)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--sentinel", required=True)
    compare_parser.add_argument("--ton", required=True)
    compare_parser.add_argument("--out", required=True)

    audit_parser = sub.add_parser("audit")
    audit_parser.add_argument("target")
    audit_parser.add_argument("--out")
    audit_parser.add_argument(
        "--enable-tonapi",
        action="store_true",
        help="Enable optional TonAPI collection (disabled by default)",
    )

    batch_parser = sub.add_parser("batch")
    batch_parser.add_argument("target")
    batch_parser.add_argument("--out", required=True)

    args = parser.parse_args()

    try:
        if args.cmd == "doctor":
            print(json.dumps({
                "status": "OK",
                "version": "0.2.0",
                "mode": "READ_ONLY",
                "python": sys.version.split()[0],
            }, indent=2))

        elif args.cmd == "scan":
            report = scan(args.target)
            print(write_report(report, args.out))
            print(json.dumps(report["summary"], indent=2))

        elif args.cmd == "compare":
            report = compare(args.sentinel, args.ton)
            out = Path(args.out)

            if out.exists() and any(out.iterdir()):
                raise FileExistsError(
                    "Refusing to overwrite non-empty directory: " + str(out)
                )

            out.mkdir(parents=True, exist_ok=True)
            target = out / "comparison.json"
            target.write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print(target)
            print(json.dumps(report["summary"], indent=2))

        elif args.cmd == "audit":
            output = args.out
            if output is None:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                output = str(Path.home() / ("tonsec-audit-" + stamp))

            report = audit_wallet(
                args.target,
                enable_tonapi=args.enable_tonapi,
            )
            print(write_chain_report(report, output))
            print(json.dumps({
                "collection": report["collection"],
                "account_observations": len(report["account_observations"]),
                "conflicts": len(report["conflicts"]),
                "transaction_counts": report["activity"]["transaction_counts"],
                "assessment": report["security_assessment"]["status"],
            }, indent=2, ensure_ascii=False))

        elif args.cmd == "batch":
            report = audit_batch(args.target, args.out)
            print(report["output_dir"])
            print(json.dumps(report["summary"], indent=2, ensure_ascii=False))

    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
