# Complete Home Advisors – Mortgage Rate Tracker

Live dashboard of average 30-year fixed rates for Conventional, FHA, VA and USDA loans.

- `index.html` – the dashboard (embedded on completehomeadvisors.com)
- `data.json` – the rates; rewritten automatically
- `scripts/update_rates.py` – downloads the Optimal Blue indices from FRED (St. Louis Fed)
- `.github/workflows/update-rates.yml` – runs the update every weekday morning and afternoon

To update right now: **Actions → Update mortgage rates → Run workflow**.
