from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Batch(db.Model):
    """One consolidation run: a set of files uploaded and processed together."""

    __tablename__ = "batches"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by = db.Column(db.String(120), nullable=True)

    file_count = db.Column(db.Integer, default=0)
    line_count = db.Column(db.Integer, default=0)
    total_qty = db.Column(db.Float, default=0)

    output_filename = db.Column(db.String(255), nullable=True)

    source_files = db.relationship(
        "SourceFile", backref="batch", cascade="all, delete-orphan"
    )
    lines = db.relationship(
        "OrderLine", backref="batch", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.strftime("%d-%m-%Y %H:%M"),
            "uploaded_by": self.uploaded_by,
            "file_count": self.file_count,
            "line_count": self.line_count,
            "total_qty": self.total_qty,
            "output_filename": self.output_filename,
        }


class SourceFile(db.Model):
    """One uploaded file within a batch, and whether it parsed cleanly."""

    __tablename__ = "source_files"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=False)

    filename = db.Column(db.String(255), nullable=False)
    db_name = db.Column(db.String(255), nullable=True)
    db_code = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(16), nullable=False)  # "ok" | "error"
    error_message = db.Column(db.String(500), nullable=True)
    line_count = db.Column(db.Integer, default=0)


class OrderLine(db.Model):
    """One consolidated order line (only lines with an order quantity)."""

    __tablename__ = "order_lines"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("batches.id"), nullable=False)

    order_date = db.Column(db.String(32), nullable=True)
    db_code = db.Column(db.String(64), nullable=True)
    db_name = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(255), nullable=True)
    item_name = db.Column(db.String(500), nullable=True)
    mrp = db.Column(db.String(64), nullable=True)
    qty_in_cs = db.Column(db.Float, nullable=False)
