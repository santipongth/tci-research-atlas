"""Check corpus files against corpus.schema.json without installing the Atlas pipeline.

    pip install jsonschema
    python validate_jsonl.py /path/to/corpus            # every articles/**/*.jsonl and *.jsonl.gz
    python validate_jsonl.py part-0001.jsonl.gz         # one file

Prints "file:line: field: problem" for every line that does not match and a summary; exit 1 when any line fails.
The schema checks the shape of each field. `atlas profile` also checks the rules that span fields (year = year of
published, one of the 77 provinces, Buddhist Era years) — run it before the hand-over when you can.
"""
import gzip
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA = Path(__file__).with_name("corpus.schema.json")


def files_of(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    ok = (".jsonl", ".jsonl.gz", ".ndjson", ".ndjson.gz")
    return sorted(p for p in target.glob("articles/**/*") if p.is_file() and p.name.endswith(ok)
                  and not p.name.startswith("_"))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
    files = files_of(Path(argv[1]))
    if not files:
        print(f"no .jsonl files under {argv[1]} (expected articles/*.jsonl or *.jsonl.gz)")
        return 2
    lines = bad = 0
    for f in files:
        opener = gzip.open if f.name.endswith(".gz") else open
        with opener(f, "rt", encoding="utf-8-sig") as fh:
            for i, line in enumerate(fh, start=1):
                if not line.strip():
                    continue
                lines += 1
                try:
                    errors = list(validator.iter_errors(json.loads(line)))
                except json.JSONDecodeError as e:
                    errors = [f"not JSON: {e}"]
                if errors:
                    bad += 1
                    for e in errors[:3]:
                        where = "/".join(str(x) for x in getattr(e, "absolute_path", [])) or "(line)"
                        print(f"{f}:{i}: {where}: {getattr(e, 'message', e)}")
    print(f"{lines:,} lines checked, {bad:,} with problems ({bad / max(lines, 1):.2%})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
