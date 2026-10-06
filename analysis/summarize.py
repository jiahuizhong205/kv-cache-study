"""Summarize existing benchmark output; do not invent missing measurements."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    data = json.loads(args.result.read_text(encoding="utf-8"))
    keys = ["completed", "failed", "duration", "request_throughput",
            "output_throughput", "median_ttft_ms", "p95_ttft_ms",
            "median_tpot_ms", "p95_tpot_ms", "median_itl_ms"]
    print("| Metric | Value |\n| --- | --- |")
    for key in keys:
        print(f"| {key} | {data.get(key, 'N/A')} |")
    print("\nN/A means unavailable. Check raw output, failures and units.")


if __name__ == "__main__":
    main()
