import uuid
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from backend.extractor import extract_from_file, format_date
from backend.models import Batch, OrderLine, SourceFile, db
from backend.writer import build_workbook

bp = Blueprint("main", __name__)


def _allowed(filename):
    return Path(filename).suffix.lower() in current_app.config["ALLOWED_EXTENSIONS"]


@bp.route("/")
def index():
    recent = Batch.query.order_by(Batch.created_at.desc()).limit(5).all()
    return render_template("index.html", recent=recent)


@bp.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    files = [f for f in files if f and f.filename]

    if not files:
        flash("Choose at least one .xlsx file first.", "error")
        return redirect(url_for("main.index"))

    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    batch = Batch(uploaded_by=request.form.get("uploaded_by") or None)
    db.session.add(batch)
    db.session.flush()  # get batch.id before commit

    all_rows = []
    ok_files = 0

    for f in files:
        safe_name = secure_filename(f.filename)
        if not _allowed(safe_name):
            db.session.add(
                SourceFile(
                    batch_id=batch.id,
                    filename=f.filename,
                    status="error",
                    error_message="Not a .xlsx/.xlsm file.",
                )
            )
            continue

        stored_name = f"{batch.id}_{uuid.uuid4().hex[:8]}_{safe_name}"
        stored_path = upload_dir / stored_name
        f.save(stored_path)

        result = extract_from_file(stored_path)

        if result.error:
            db.session.add(
                SourceFile(
                    batch_id=batch.id,
                    filename=f.filename,
                    status="error",
                    error_message=result.error,
                )
            )
            continue

        db.session.add(
            SourceFile(
                batch_id=batch.id,
                filename=f.filename,
                db_name=str(result.db_name) if result.db_name is not None else None,
                db_code=str(result.db_code) if result.db_code is not None else None,
                status="ok",
                line_count=len(result.rows),
            )
        )
        ok_files += 1
        all_rows.extend(result.rows)

    for row in all_rows:
        db.session.add(
            OrderLine(
                batch_id=batch.id,
                order_date=format_date(row.order_date),
                db_code=str(row.db_code) if row.db_code is not None else None,
                db_name=str(row.db_name) if row.db_name is not None else None,
                category=str(row.category) if row.category is not None else None,
                item_name=str(row.item_name) if row.item_name is not None else None,
                mrp=str(row.mrp) if row.mrp is not None else None,
                qty_in_cs=row.qty,
            )
        )

    output_dir = Path(current_app.config["OUTPUT_FOLDER"])
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"consolidated_order_batch_{batch.id}.xlsx"

    if all_rows:
        build_workbook(all_rows, output_dir / output_filename)
        batch.output_filename = output_filename

    batch.file_count = ok_files
    batch.line_count = len(all_rows)
    batch.total_qty = sum(r.qty for r in all_rows)

    db.session.commit()

    if not all_rows:
        flash(
            "No order lines were found across the uploaded file(s) — "
            "check the file details below.",
            "error",
        )

    return redirect(url_for("main.view_batch", batch_id=batch.id))


@bp.route("/batch/<int:batch_id>")
def view_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    return render_template("batch.html", batch=batch)


@bp.route("/download/<int:batch_id>")
def download(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    if not batch.output_filename:
        flash("This batch has no consolidated file to download.", "error")
        return redirect(url_for("main.view_batch", batch_id=batch.id))
    return send_from_directory(
        current_app.config["OUTPUT_FOLDER"],
        batch.output_filename,
        as_attachment=True,
        download_name="Consolidated Order Booking.xlsx",
    )


@bp.route("/history")
def history():
    batches = Batch.query.order_by(Batch.created_at.desc()).all()
    return render_template("history.html", batches=batches)
