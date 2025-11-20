Submission folder for Round 1 replay

Files included:
- `Round_1.csv` (NOT included by default) - place the competition CSV here.
- `pair_scan_cuths.py` - dedicated pair backtester (standalone copy).
- `main.py` - minimal runner (calls pair runner when requested).
- `replay_best_pair.py` - replay script (already present).
- `best_pair_params_CUTHS_CASTLE_STOCKS_382_20251120_000651.json` - canonical params that produced +382.00 in an authoritative replay.

How to run (from inside this folder on Windows PowerShell):

python .\pair_scan_cuths.py

Or run the small runner to execute the canonical pair via `main.py`:

python .\main.py run_pair_demo

Notes:
- This folder contains the dedicated pair backtester and params JSON so it can be uploaded as a single folder for grading convenience. You must include `Round_1.csv` in this folder before running.
- If you prefer, zip this folder (including `Round_1.csv`) and upload the zip for the grader.
