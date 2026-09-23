# Order Consolidator Portal

A small internal web portal: someone uploads several "Order Booking Format"
Excel files, the portal reads the DB Name / DB Code / Date from each file's
header block and the ordered item lines from its order table, stores
everything in a database, and hands back one consolidated workbook in the
format:

`Date | DB Code | DB Name | Category | Item Name | MRP | Qty in Cs`

Every upload is kept as a **batch** in the database, so anyone in the
department can come back later and re-download a past batch instead of
re-uploading files.

## Folder structure

```
order-consolidator-portal/
├── run.py                     # entry point — python run.py
├── requirements.txt
├── .env.example                # copy to .env and edit if needed
├── backend/
│   ├── app.py                 # Flask app factory, wires everything together
│   ├── config.py               # settings (paths, DB URL, upload limits)
│   ├── models.py                # SQLAlchemy models: Batch, OrderLine
│   ├── extractor.py             # core parsing logic (the actual "business logic")
│   └── routes.py                # HTTP routes / views
├── frontend/
│   ├── templates/               # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html           # upload form + recent batches
│   │   ├── batch.html           # one batch's preview + download
│   │   └── history.html         # full batch history
│   └── static/
│       ├── css/style.css
│       └── js/app.js            # drag-and-drop + client-side file list
├── uploads/                     # raw uploaded files land here (gitignored)
├── outputs/                     # generated consolidated workbooks (gitignored)
└── tests/
    └── test_extractor.py        # unit tests for the parsing logic
```

`uploads/`, `outputs/`, and the SQLite database file are all gitignored —
they're runtime data, not code, so they shouldn't go into the repo.

## Running it locally (VS Code)

1. Open this folder in VS Code.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run it:
   ```bash
   python run.py
   ```
4. Open **http://127.0.0.1:5000** in a browser.

The first run creates `portal.db` (SQLite) automatically — nothing else to
set up.

## Putting it on GitHub

From this folder:
```bash
git init
git add .
git commit -m "Initial commit: order consolidator portal"
git branch -M main
git remote add origin https://github.com/<your-org>/<repo-name>.git
git push -u origin main
```

Anyone in the other department can then:
```bash
git clone https://github.com/<your-org>/<repo-name>.git
cd <repo-name>
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python run.py
```

## How the parsing works (backend/extractor.py)

Each input file is expected to follow the same "Terrestrial Order Format"
layout your team already uses:
- A header block near the top with `DB Name:-`, `DB Code:-`, and `Date`
  labels, each followed by its value in the next cell.
- Further down, a table whose header row starts with `Category` and also
  contains `Item Name`, `MRP`, and `Order Qty in Cs`.

`extractor.py` finds that table by scanning for the header row (it doesn't
assume a fixed row number, so minor layout shifts between files still work),
reads the DB info from the rows above it, then keeps only item rows where
`Order Qty in Cs` is a number greater than zero. If a file doesn't match
this shape, the portal reports which file failed and why, rather than
silently skipping it.

## Moving beyond SQLite

SQLite (via `backend/portal.db`) is enough for a single small team on one
machine. If this portal grows to serve many people at once or needs to run
on a shared server, swap the database URL in `backend/config.py` (`DATABASE_URL`)
for a Postgres/MySQL connection string — the SQLAlchemy models don't need to
change.

## Tests

```bash
pip install pytest
pytest tests/
```

## Streamlit frontend

A modern Streamlit frontend is included in `streamlit_app.py`. It reuses the
same backend extraction/database logic and adds multi-file upload, analysis
metrics, file-level status, consolidated data preview, and Excel/CSV download.

Run it with:

```bash
python -m streamlit run streamlit_app.py
```

Windows users can also double-click `run_streamlit.bat`.

The Streamlit UI runs on `http://localhost:8501` by default. The original Flask
portal remains available with `python run.py` on port 5000.
