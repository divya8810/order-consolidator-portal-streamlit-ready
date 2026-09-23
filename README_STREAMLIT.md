# Order Consolidator Portal — Streamlit UI

This version keeps the existing Flask/business logic and adds a modern Streamlit frontend.

## Features

- Upload multiple `.xlsx` / `.xlsm` distributor order files
- Analyse and consolidate all valid order lines
- Show file-level success/error status
- Show summary metrics: files, processed files, errors, order lines and total quantity
- Preview the consolidated order table
- Download the result as **Excel** or **CSV**
- View previous batches and download them again
- Existing SQLite database and Excel output logic are reused

## Run in VS Code / PowerShell

Activate your virtual environment first:

```powershell
& D:/Virtual_Envs/mlops/mlops/Scripts/Activate.ps1
```

Install the updated requirements:

```powershell
python -m pip install -r requirements.txt
```

Start Streamlit:

```powershell
python -m streamlit run streamlit_app.py
```

Then open:

`http://localhost:8501`

You can also double-click `run_streamlit.bat` on Windows.

## Existing Flask portal

The original Flask portal is still available:

```powershell
python run.py
```

It runs on `http://127.0.0.1:5000`.

## Important

Both interfaces use the same `backend/portal.db`, `uploads/`, and `outputs/` folders. If you already have data from the Flask portal, the Streamlit Batch History can access the same batches.
