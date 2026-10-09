# LESCO Smart Energy

Local FYP application: Flask, SQLite, Python/OpenCV/Pillow/Tesseract, vanilla browser UI.

## Run in Visual Studio Code

Open this folder. Use Python 3.11+ and select `.venv` as the interpreter.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# macOS: brew install tesseract
# Ubuntu: sudo apt install tesseract-ocr
# Windows: install Tesseract and add its executable directory to PATH.
python app.py
```

Open http://127.0.0.1:5055. VS Code's included launch configuration also runs the application. The app creates `data/lesco.sqlite3` automatically. This is a single-user local application; do not expose it on a public interface without authentication, CSRF protection and deployment hardening. It does not upload photos to an external OCR service. OCR crop previews remain in the browser response; raw OCR, candidate metadata and confirmed readings are stored locally.

## Flow

Enter previous cumulative reading and month, upload a photo, optionally supply crop coordinates, run OCR, inspect the crop and candidates, select/correct the current kWh register, and confirm. Save the result. When OCR is unavailable or ambiguous, select **Manual-reading fallback** and enter a verified reading. OCR never selects a candidate merely because it exceeds the previous reading.

Consumer setup and explicitly dated history are reusable. The six-month baseline checks the six preceding calendar months AND current use at ≤200 kWh; this convention is provisional. Missing history is not zero; a known disqualifying month can fail the baseline test despite other missing months. Twelve or more months may be stored, but lifeline rules remain unverified. Raw units are never normalized. An ordinary-month scenario must be explicitly selected for provisional classification.

## Evidence and limitations

`data/tariff.json` contains draft bands with null rates. No official bill total is currently available. Do not promote a draft by changing a status flag: implement and test the complete verified conditions, category mapping, effective dates, slab benefit, taxes, adjustment periods, rounding and fixed charges first. The supplied official snapshot remains incomplete. `services/tariffs.py` executes explicitly verified all-unit/progressive energy, fixed-per-kW, adjustment and tax rules with effective-period and missing-value checks. No supplied configuration is activated. Explicitly labelled custom flat scenarios produce totals. They do not reproduce progressive/slab billing.

NEPRA index access returned HTTP 403 during implementation. User-supplied PDF evidence is tracked separately. Publication dates alone do not prove September 2026 applicability. The profile tariff code is stored, not guessed into a category. Lifeline, load eligibility, nonstandard cycles, multipliers other than 1, solar, ToU and replacement workflows are not enabled. Raw consumption is shown separately from billed units (null until verified). Estimated appliance consumption is watts × hours/day × days × quantity / 1000; custom budget estimates do not account for nonlinear tariffs or appliance duty cycles.

Database tables: `profiles`, `ocr`, `bills`, `observations` (reserved for user bill observations; no reconciliation UI yet). Bills preserve the input, tariff snapshot and OCR audit. Synthetic values occur only in tests, never in the official tariff configuration.

## Modules and checks

- `services/billing.py`: pure Decimal-based calculations and provisional classification.
- `services/ocr.py`: orientation correction, display-shaped contour crop proposal or explicit crop, enlargement, CLAHE, threshold variant, Tesseract candidates. Automatic crop is heuristic and must be reviewed; register labels remain unverified.
- `app.py`: routes and SQLite persistence.
- `static/`, `templates/`: responsive application UI.

```sh
python -m unittest discover -s tests -v
```

Tests cover the exact dated window, threshold 200, missing and duplicate history, known disqualifying months, unsupported profiles, zero and negative differences, nonfinite input, verification, decimal arithmetic and appliance budgets. OCR needs the external binary and real meter-photo validation. Font loading is optional; local sans-serif fallbacks work offline.

## Quick energy estimate

The main form now needs only previous reading, a photo or manually entered current reading, and confirmation. Billing month defaults to the device's current month. Load, profile, history and crop settings are tucked into More options. They are not required to see a cost comparison.

`services/estimate.py` computes explicitly labelled February-document energy scenarios from `data/supplied-evidence.json`. It leaves the official total null and does not activate the draft tariff. At up to 200 units it shows both protected and unprotected alternatives; at up to 100 it also shows a conditional lifeline alternative. Above 200 it shows the unprotected ordinary-month scenario. None asserts actual eligibility. Fixed charges appear separately only when load is supplied; headline figures exclude all fixed/minimum charges, taxes, adjustments, fees and arrears. Known unsupported arrangements or load outside the source schedule are rejected. This is a historical-document comparison, not confirmed pricing for the selected month.

## Dates, observed bill and limit planner

Pakistan local date is populated automatically. The next issuance date follows the user's stated 15th-of-month schedule; this is not treated as the meter-reading cutoff. The user's Rs. 48,837 / 744 kWh observation is stored as unverified bill evidence with unknown billing month, not converted into a tariff or tax rate. The limit planner saves a rupee target and optional user-chosen reserve. It uses the highest displayed energy scenario when category is unknown and gives an illustrative remaining rupee allowance per day until issuance. It is not a full bill forecast or a guaranteed cap.

## Appliance guide and bill reference correction

The supplied Rs. 48,837 bill is reference evidence only and is no longer rendered on the main screen. Its summary is stored separately in `data/reference-bill-september-2026.json`: Rs. 38,020.85 electricity charges plus Rs. 10,816.14 taxes, rounded from Rs. 48,836.99. The February-document base-energy comparison is Rs. 35,116.80. The Rs. 2,904.05 difference before taxes remains unallocated because the photo does not itemize surcharges/adjustments; it is not a fitted tariff.

The daily appliance guide prices the entire planned cycle at the highest source energy band (Rs. 47.20/kWh), subtracts entered units, and divides remaining units by days to the user-stated issuance date. This avoids treating only extra units as expensive after a band crossing. It is deliberately a conservative base-energy illustration, not an official bill cap. An optional user reserve remains necessary for unknown other charges. Starter assumptions: one fridge at 1.2 kWh/day (cycling), one 60 W fan for 8 hours, four 10 W LEDs for 5 hours; remaining allowance goes to one AC at editable 1500 W average power. AC minutes are rounded down. If essentials exceed the allowance the UI explicitly flags the shortfall instead of advising refrigeration shutdown. Other appliances need energy deducted from this shared allocation. Actual cycle alignment is unverified; an issuance date is not a meter-reading cutoff.

## Request and tariff-rule validation

Malformed/non-object JSON, invalid nested reading/profile/history shapes and
invalid OCR crops return 400 instead of uncaught server errors. Explicit crop
coordinates must be four finite whole numbers: nonnegative x/y and positive
width/height within the oriented image. Images above 20 million pixels are
rejected before decoding their full pixel data. Arithmetic that exceeds Decimal
precision returns 400 without storing a bill.

Progressive synthetic/verified rule configurations must have contiguous,
non-overlapping bands starting at zero; invalid coverage produces an incomplete
configuration result rather than silently missing or double-charging units.
These checks do not establish that a configuration is an official tariff.

SQLite connections now close after reads/writes and roll back failed
transactions. `LESCO_DB_PATH` can select a different existing database location;
its parent directory must exist. No schema migration is required.

GitHub Actions runs the regression suite on Python 3.12. OCR tests use generated
images and mocked Tesseract output to verify crop/candidate handling. A local
synthetic-image smoke check can exercise the installed Tesseract binary; this
does not establish real meter-photo accuracy. Current-month tariff applicability
and adjustments remain unverified; the February document stays a labelled
historical comparison and the official snapshot stays draft.
