"""Download a reviewable public-data bundle; does not change live accounts.

PYTHONPATH=. python scripts/bootstrap_nifty_iv.py --as-of 2026-09-29 --output /tmp/nifty-iv.json
TLS verification is required. SSL_CERT_FILE can select a trusted CA bundle.
"""
import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from options_lab import nse_history as n
from options_lab.iv_history import derive_daily
from options_lab.paper_agents import IST


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.as_of > datetime.now(IST).date():
        parser.error('as-of must not be in the future')
    observations, skipped = [], []
    for offset in range(1, 121):
        day = args.as_of-timedelta(days=offset)
        if day.weekday() > 4:
            continue
        try:
            rows = n.fetch_bhavcopy(day, timeout=25)
            item = derive_daily(rows, day.isoformat(), datetime.now(timezone.utc).isoformat())
            observations.append(item)
            print(f'{day}: {item["iv"]:.4f}% ({len(observations)}/30)', flush=True)
        except (n.NseHistoryError, ValueError) as error:
            skipped.append(dict(day=day.isoformat(), reason=str(error)[:200]))
        if len(observations) >= 30:
            break
    if len(observations) < 20:
        raise SystemExit(f'Only {len(observations)} eligible observations; refusing to publish a ready bundle')
    args.output.write_text(json.dumps(dict(schema=1, underlying='NIFTY',
        generated_at=datetime.now(timezone.utc).isoformat(),
        observations=sorted(observations, key=lambda x:x['day']), skipped=skipped), indent=2)+'\n')


if __name__ == '__main__':
    main()
