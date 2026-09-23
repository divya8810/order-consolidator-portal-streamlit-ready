import sys
from datetime import datetime
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.extractor import extract_from_file  # noqa: E402


def make_sample_workbook(path, db_name="Test Distributor", db_code=12345):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Order Booking Format"

    ws.append(["", "Terrestrial Order Format"])
    ws.append(["DB Name:-", db_name, "", "", "", "", "Date ", datetime(2026, 9, 20)])
    ws.append(["DB Code:-", db_code])
    ws.append(["Customer State Type", "Super"])
    ws.append(
        ["Category", "Item Name", "Ladi / Cutting", "New Item Code", "Case Value",
         "MRP", "Order Qty in Cs", "Order Value"]
    )
    ws.append(["Snacks", "Widget A 50g", "Cutting", "X001", 100, "MRP 10", 25, 250])
    ws.append(["Snacks", "Widget B 50g", "Cutting", "X002", 100, "MRP 10", None, 0])
    ws.append(["Snacks", "Widget C 50g", "Cutting", "X003", 100, "MRP 10", 0, 0])

    wb.save(path)


def test_extracts_only_positive_qty_rows(tmp_path):
    file_path = tmp_path / "sample_order.xlsx"
    make_sample_workbook(file_path)

    result = extract_from_file(file_path)

    assert result.error is None
    assert result.db_name == "Test Distributor"
    assert result.db_code == 12345
    assert len(result.rows) == 1
    assert result.rows[0].item_name == "Widget A 50g"
    assert result.rows[0].qty == 25


def test_missing_order_table_reports_error(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Not", "An", "Order", "File"])
    file_path = tmp_path / "not_an_order_file.xlsx"
    wb.save(file_path)

    result = extract_from_file(file_path)

    assert result.error is not None
    assert result.rows == []
