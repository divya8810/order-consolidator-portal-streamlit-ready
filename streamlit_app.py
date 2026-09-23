"""Streamlit frontend for the Order Consolidator Portal.

The existing Flask backend/business logic is intentionally reused. This file
provides a modern UI for uploading, analysing, previewing and downloading
consolidated orders as Excel or CSV.
"""
from __future__ import annotations

import io
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
from werkzeug.utils import secure_filename

from backend.app import create_app
from backend.extractor import extract_from_file, format_date
from backend.models import Batch, OrderLine, SourceFile, db
from backend.writer import build_workbook


APP_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Order Consolidator",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
        .hero { padding: 1.4rem 1.6rem; border-radius: 18px; background: linear-gradient(135deg, #0f2742 0%, #174d75 100%); color: white; margin-bottom: 1.2rem; }
        .hero h1 { margin: 0; font-size: 2rem; }
        .hero p { margin: .45rem 0 0; opacity: .88; }
        .metric-card { border: 1px solid #e5e7eb; border-radius: 14px; padding: 1rem; background: #fff; min-height: 110px; }
        .metric-label { color: #64748b; font-size: .85rem; }
        .metric-value { color: #0f172a; font-size: 1.65rem; font-weight: 700; margin-top: .25rem; }
        .success-box { border-left: 5px solid #16a34a; padding: .8rem 1rem; background: #f0fdf4; border-radius: 8px; }
        .error-box { border-left: 5px solid #dc2626; padding: .8rem 1rem; background: #fef2f2; border-radius: 8px; }
        section[data-testid="stSidebar"] { border-right: 1px solid #e5e7eb; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric(label, value):
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def get_flask_app():
    if "flask_app" not in st.session_state:
        st.session_state.flask_app = create_app()
    return st.session_state.flask_app


def rows_to_dataframe(rows):
    return pd.DataFrame(
        [
            {
                "Date": format_date(r.order_date),
                "DB Code": r.db_code,
                "DB Name": r.db_name,
                "Category": r.category,
                "Item Name": r.item_name,
                "MRP": r.mrp,
                "Qty in Cs": r.qty,
            }
            for r in rows
        ]
    )


def dataframe_from_batch(batch):
    return pd.DataFrame(
        [
            {
                "Date": r.order_date,
                "DB Code": r.db_code,
                "DB Name": r.db_name,
                "Category": r.category,
                "Item Name": r.item_name,
                "MRP": r.mrp,
                "Qty in Cs": r.qty_in_cs,
            }
            for r in batch.lines
        ]
    )


def build_excel_bytes(rows):
    buffer = io.BytesIO()
    build_workbook(rows, buffer)
    buffer.seek(0)
    return buffer.getvalue()


def build_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def process_files(uploaded_files, uploaded_by):
    app = get_flask_app()
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    output_dir = Path(app.config["OUTPUT_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        batch = Batch(uploaded_by=uploaded_by or None)
        db.session.add(batch)
        db.session.flush()

        all_rows = []
        file_results = []

        for uploaded in uploaded_files:
            original_name = uploaded.name
            safe_name = secure_filename(original_name)
            suffix = Path(safe_name).suffix.lower()

            if suffix not in app.config["ALLOWED_EXTENSIONS"]:
                message = "Not a .xlsx/.xlsm file."
                db.session.add(SourceFile(
                    batch_id=batch.id,
                    filename=original_name,
                    status="error",
                    error_message=message,
                ))
                file_results.append({
                    "File": original_name, "DB Name": "", "DB Code": "",
                    "Status": "Error", "Lines": 0, "Message": message,
                })
                continue

            stored_name = f"{batch.id}_{uuid.uuid4().hex[:8]}_{safe_name}"
            stored_path = upload_dir / stored_name
            stored_path.write_bytes(uploaded.getvalue())

            result = extract_from_file(stored_path)
            if result.error:
                db.session.add(SourceFile(
                    batch_id=batch.id,
                    filename=original_name,
                    status="error",
                    error_message=result.error,
                ))
                file_results.append({
                    "File": original_name,
                    "DB Name": str(result.db_name or ""),
                    "DB Code": str(result.db_code or ""),
                    "Status": "Error",
                    "Lines": 0,
                    "Message": result.error,
                })
                continue

            db.session.add(SourceFile(
                batch_id=batch.id,
                filename=original_name,
                db_name=str(result.db_name) if result.db_name is not None else None,
                db_code=str(result.db_code) if result.db_code is not None else None,
                status="ok",
                line_count=len(result.rows),
            ))
            all_rows.extend(result.rows)
            file_results.append({
                "File": original_name,
                "DB Name": str(result.db_name or ""),
                "DB Code": str(result.db_code or ""),
                "Status": "Success",
                "Lines": len(result.rows),
                "Message": "Processed successfully",
            })

        for row in all_rows:
            db.session.add(OrderLine(
                batch_id=batch.id,
                order_date=format_date(row.order_date),
                db_code=str(row.db_code) if row.db_code is not None else None,
                db_name=str(row.db_name) if row.db_name is not None else None,
                category=str(row.category) if row.category is not None else None,
                item_name=str(row.item_name) if row.item_name is not None else None,
                mrp=str(row.mrp) if row.mrp is not None else None,
                qty_in_cs=row.qty,
            ))

        output_filename = f"consolidated_order_batch_{batch.id}.xlsx"
        if all_rows:
            build_workbook(all_rows, output_dir / output_filename)
            batch.output_filename = output_filename

        batch.file_count = sum(1 for x in file_results if x["Status"] == "Success")
        batch.line_count = len(all_rows)
        batch.total_qty = sum(r.qty for r in all_rows)
        db.session.commit()

        return batch.id, file_results, rows_to_dataframe(all_rows), build_excel_bytes(all_rows)


def render_dashboard():
    st.markdown(
        '<div class="hero"><h1>📦 Order Consolidator</h1>'
        '<p>Upload distributor order files, analyse them and download one consolidated order file.</p></div>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("Controls")
        uploaded_by = st.text_input("Uploaded by", placeholder="Your name")
        st.caption("Supported formats: .xlsx and .xlsm")
        st.divider()
        st.info("The original Excel files are stored locally in the portal's uploads folder.")

    uploaded_files = st.file_uploader(
        "Upload Order Files",
        type=["xlsx", "xlsm"],
        accept_multiple_files=True,
        help="You can select multiple distributor order files at once.",
    )

    if uploaded_files:
        st.write(f"**{len(uploaded_files)} file(s) selected**")
        st.dataframe(
            pd.DataFrame({"Selected files": [f.name for f in uploaded_files]}),
            use_container_width=True,
            hide_index=True,
        )

    if st.button("🔍 Analyse & Consolidate Orders", type="primary", use_container_width=True, disabled=not uploaded_files):
        with st.spinner("Reading files and consolidating orders..."):
            batch_id, file_results, df, excel_bytes = process_files(uploaded_files, uploaded_by)
        st.session_state.analysis = {
            "batch_id": batch_id,
            "file_results": file_results,
            "df": df,
            "excel": excel_bytes,
        }
        st.rerun()

    analysis = st.session_state.get("analysis")
    if not analysis:
        st.subheader("How it works")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 1. Upload")
            st.write("Select one or more distributor Excel files.")
        with c2:
            st.markdown("### 2. Analyse")
            st.write("The portal extracts DB details and ordered item lines.")
        with c3:
            st.markdown("### 3. Download")
            st.write("Download the consolidated result as Excel or CSV.")
        return

    df = analysis["df"]
    results_df = pd.DataFrame(analysis["file_results"])
    successful = int((results_df["Status"] == "Success").sum()) if not results_df.empty else 0
    failed = int((results_df["Status"] == "Error").sum()) if not results_df.empty else 0
    db_count = int(df["DB Code"].dropna().astype(str).nunique()) if not df.empty else 0
    total_qty = float(df["Qty in Cs"].sum()) if not df.empty else 0

    st.success(f"Batch #{analysis['batch_id']} analysed successfully.")
    m = st.columns(5)
    for col, label, value in zip(
        m,
        ["Files uploaded", "Processed", "Errors", "Order lines", "Total Qty (Cs)"],
        [len(results_df), successful, failed, len(df), f"{total_qty:,.0f}"],
    ):
        with col:
            metric(label, value)

    st.markdown("### File Processing Status")
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    if failed:
        st.warning("Some files could not be processed. Check the Message column before using the consolidated output.")

    st.markdown("### Consolidated Orders")
    if df.empty:
        st.error("No positive order quantities were found in the uploaded files.")
        return

    c1, c2 = st.columns([1, 1])
    with c1:
        st.download_button(
            "⬇️ Download Excel",
            data=analysis["excel"],
            file_name=f"Consolidated_Order_Batch_{analysis['batch_id']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "⬇️ Download CSV",
            data=build_csv_bytes(df),
            file_name=f"Consolidated_Order_Batch_{analysis['batch_id']}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.dataframe(df, use_container_width=True, height=500, hide_index=True)


def render_history():
    st.markdown("### 🕘 Batch History")
    app = get_flask_app()
    with app.app_context():
        batches = Batch.query.order_by(Batch.created_at.desc()).all()
        if not batches:
            st.info("No previous batches found.")
            return

        history = pd.DataFrame([b.to_dict() for b in batches])
        st.dataframe(history, use_container_width=True, hide_index=True)

        selected = st.number_input(
            "Enter batch ID to view/download",
            min_value=1,
            value=int(batches[0].id),
            step=1,
        )
        batch = Batch.query.get(int(selected))
        if not batch:
            st.warning("Batch ID not found.")
            return

        df = dataframe_from_batch(batch)
        st.markdown(f"#### Batch #{batch.id}")
        if df.empty:
            st.info("This batch has no order lines.")
            return

        excel = build_excel_bytes([
            type("Row", (), {
                "order_date": r.order_date,
                "db_code": r.db_code,
                "db_name": r.db_name,
                "category": r.category,
                "item_name": r.item_name,
                "mrp": r.mrp,
                "qty": r.qty_in_cs,
            })() for r in batch.lines
        ])
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "⬇️ Download Excel",
                data=excel,
                file_name=f"Consolidated_Order_Batch_{batch.id}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key=f"history_excel_{batch.id}",
            )
        with c2:
            st.download_button(
                "⬇️ Download CSV",
                data=build_csv_bytes(df),
                file_name=f"Consolidated_Order_Batch_{batch.id}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"history_csv_{batch.id}",
            )
        st.dataframe(df, use_container_width=True, hide_index=True)


def main():
    inject_css()
    st.sidebar.title("Order Consolidator")
    page = st.sidebar.radio("Navigation", ["Analyse Orders", "Batch History"], label_visibility="collapsed")
    if page == "Analyse Orders":
        render_dashboard()
    else:
        render_history()


if __name__ == "__main__":
    main()
