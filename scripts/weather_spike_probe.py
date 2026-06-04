#!/usr/bin/env python3
"""Run PI5 Track D weather proof-of-access probes (not production ingest)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

from backend.app.spike.weather.constants import IMD_SAMPLE_OBJ_ID
from backend.app.spike.weather.imd import ImdAccessProbe
from backend.app.spike.weather.nasa_power import NasaPowerClient


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=("nasa", "imd", "all"),
        default="all",
        help="Which source to probe (default: all)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Lookback window for NASA POWER daily pull (default: 7)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report: dict[str, object] = {}

    if args.source in ("nasa", "all"):
        end = date.today() - timedelta(days=4)
        start = end - timedelta(days=max(args.days - 1, 0))
        client = NasaPowerClient()
        belt = client.fetch_telangana_cotton_belt(start, end)
        report["nasa_power"] = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "districts": {
                name: [
                    {
                        "date": point.observation_date.isoformat(),
                        "precipitation_mm": point.precipitation_mm,
                        "temperature_c": point.temperature_c,
                        "relative_humidity_pct": point.relative_humidity_pct,
                    }
                    for point in points
                ]
                for name, points in belt.items()
            },
        }

    if args.source in ("imd", "all"):
        probe = ImdAccessProbe()
        results = probe.probe_all()
        report["imd"] = {
            "sample_obj_id": IMD_SAMPLE_OBJ_ID,
            "endpoints": [
                {
                    "endpoint": result.endpoint,
                    "status_code": result.status_code,
                    "accessible": result.accessible,
                    "error_message": result.error_message,
                    "sample_record_count": result.sample_record_count,
                    "notes": result.notes,
                }
                for result in results
            ],
        }

    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
