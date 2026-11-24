from __future__ import annotations
import csv, io, os, sqlite3
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
INVOICE_DIR = DATA_DIR / "invoices"
DB_PATH = DATA_DIR / "invoices.db"
DATA_DIR.mkdir(exist_ok=True)
INVOICE_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        invoice_date TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_email TEXT,
        customer_phone TEXT,
        customer_address TEXT,
        subtotal TEXT NOT NULL,
        tax_rate TEXT NOT NULL,
        tax_amount TEXT NOT NULL,
        total TEXT NOT NULL,
        notes TEXT,
        pdf_path TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
        description TEXT NOT NULL,
        quantity TEXT NOT NULL,
        unit_price TEXT NOT NULL,
        amount TEXT NOT NULL
    )""")
    con.commit()
    return con

def money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def fmt(value):
    return f"₹{money(value):,.2f}"

def make_invoice_no():
    return "INV-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]

def build_pdf(invoice, items, destination):
    doc = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=18*mm,
                            leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("INVOICE", ParagraphStyle("InvoiceTitle", parent=styles["Title"],
                                                       textColor=colors.HexColor("#183153"), fontSize=25)))
    story.append(Paragraph(f"<b>Invoice:</b> {invoice['invoice_no']} &nbsp;&nbsp; "
                           f"<b>Date:</b> {invoice['invoice_date']}", styles["Normal"]))
    story.append(Spacer(1, 10))
    customer = f"<b>Bill To</b><br/>{invoice['customer_name']}<br/>"
    customer += (invoice.get("customer_address") or "").replace("\n", "<br/>")
    if invoice.get("customer_email"): customer += f"<br/>{invoice['customer_email']}"
    if invoice.get("customer_phone"): customer += f"<br/>{invoice['customer_phone']}"
    story.append(Paragraph(customer, styles["Normal"]))
    story.append(Spacer(1, 18))
    data = [["Description", "Qty", "Unit price", "Amount"]]
    for item in items:
        data.append([item["description"], item["quantity"], fmt(item["unit_price"]), fmt(item["amount"])])
    data += [["", "", "Subtotal", fmt(invoice["subtotal"])],
             ["", "", f"Tax ({invoice['tax_rate']}%)", fmt(invoice["tax_amount"])],
             ["", "", "TOTAL", fmt(invoice["total"])]]
    table = Table(data, colWidths=[91*mm, 18*mm, 35*mm, 35*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#183153")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-4), .4, colors.HexColor("#d8dee8")),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#eaf0f8")),
        ("FONTNAME", (2,-3), (-1,-1), "Helvetica-Bold"),
        ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story.append(table)
    if invoice.get("notes"):
        story.extend([Spacer(1, 18), Paragraph("<b>Notes</b>", styles["Heading3"]),
                      Paragraph(invoice["notes"].replace("\n", "<br/>"), styles["Normal"])])
    story.extend([Spacer(1, 28), Paragraph("Thank you for your business!", styles["Italic"])])
    doc.build(story)

@app.route("/")
def index():
    con = db()
    invoices = con.execute("SELECT * FROM invoices ORDER BY id DESC LIMIT 10").fetchall()
    stats = con.execute("SELECT COUNT(*) n, COALESCE(SUM(CAST(total AS REAL)),0) revenue FROM invoices").fetchone()
    con.close()
    return render_template("index.html", invoices=invoices, stats=stats, fmt=fmt)

@app.route("/new", methods=["GET", "POST"])
def new_invoice():
    if request.method == "GET":
        return render_template("new_invoice.html", today=date.today().isoformat())
    try:
        name = request.form.get("customer_name", "").strip()
        if not name: raise ValueError("Customer name is required.")
        invoice_date = request.form.get("invoice_date") or date.today().isoformat()
        tax_rate = Decimal(request.form.get("tax_rate", "0"))
        if tax_rate < 0 or tax_rate > 100: raise ValueError("Tax rate must be between 0 and 100.")
        descriptions = request.form.getlist("description[]")
        quantities = request.form.getlist("quantity[]")
        prices = request.form.getlist("unit_price[]")
        items = []
        subtotal = Decimal("0.00")
        for desc, qty_raw, price_raw in zip(descriptions, quantities, prices):
            desc = desc.strip()
            if not desc: continue
            qty, price = Decimal(qty_raw), money(price_raw)
            if qty <= 0 or price < 0: raise ValueError("Quantity must be positive and unit price cannot be negative.")
            amount = money(qty * price)
            subtotal += amount
            items.append({"description": desc, "quantity": str(qty), "unit_price": str(price), "amount": str(amount)})
        if not items: raise ValueError("Add at least one invoice item.")
        subtotal = money(subtotal)
        tax_amount = money(subtotal * tax_rate / Decimal("100"))
        total = money(subtotal + tax_amount)
        invoice = {
            "invoice_no": make_invoice_no(), "invoice_date": invoice_date,
            "customer_name": name, "customer_email": request.form.get("customer_email", "").strip(),
            "customer_phone": request.form.get("customer_phone", "").strip(),
            "customer_address": request.form.get("customer_address", "").strip(),
            "subtotal": str(subtotal), "tax_rate": str(tax_rate),
            "tax_amount": str(tax_amount), "total": str(total),
            "notes": request.form.get("notes", "").strip()
        }
        con = db()
        cur = con.execute("""INSERT INTO invoices
            (invoice_no,invoice_date,customer_name,customer_email,customer_phone,customer_address,
             subtotal,tax_rate,tax_amount,total,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            tuple(invoice[k] for k in ["invoice_no","invoice_date","customer_name","customer_email",
                "customer_phone","customer_address","subtotal","tax_rate","tax_amount","total","notes"]))
        invoice_id = cur.lastrowid
        for item in items:
            con.execute("INSERT INTO invoice_items (invoice_id,description,quantity,unit_price,amount) VALUES (?,?,?,?,?)",
                        (invoice_id, item["description"], item["quantity"], item["unit_price"], item["amount"]))
        pdf_path = INVOICE_DIR / f"{invoice['invoice_no']}.pdf"
        build_pdf(invoice, items, pdf_path)
        con.execute("UPDATE invoices SET pdf_path=? WHERE id=?", (str(pdf_path.relative_to(ROOT)), invoice_id))
        con.commit()
        con.close()
        flash("Invoice created and saved successfully.", "success")
        return redirect(url_for("view_invoice", invoice_id=invoice_id))
    except (ValueError, InvalidOperation, ArithmeticError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("new_invoice"))

@app.route("/invoice/<int:invoice_id>")
def view_invoice(invoice_id):
    con = db()
    invoice = con.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    if not invoice: con.close(); abort(404)
    items = con.execute("SELECT * FROM invoice_items WHERE invoice_id=?", (invoice_id,)).fetchall()
    con.close()
    return render_template("invoice.html", invoice=invoice, items=items, fmt=fmt)

@app.route("/invoice/<int:invoice_id>/pdf")
def download_pdf(invoice_id):
    con = db()
    invoice = con.execute("SELECT pdf_path FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    con.close()
    if not invoice: abort(404)
    path = ROOT / invoice["pdf_path"]
    if not path.exists(): abort(404)
    return send_file(path, as_attachment=True, download_name=path.name)

@app.route("/reports")
def reports():
    con = db()
    invoices = con.execute("SELECT * FROM invoices ORDER BY invoice_date DESC, id DESC").fetchall()
    con.close()
    return render_template("reports.html", invoices=invoices, fmt=fmt)

@app.route("/reports/export.csv")
def export_csv():
    con = db()
    rows = con.execute("SELECT invoice_no,invoice_date,customer_name,customer_email,customer_phone,subtotal,tax_rate,tax_amount,total FROM invoices ORDER BY invoice_date DESC").fetchall()
    con.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice No", "Date", "Customer", "Email", "Phone", "Subtotal (INR)", "Tax Rate (%)", "Tax (INR)", "Total (INR)"])
    writer.writerows([tuple(row) for row in rows])
    return send_file(io.BytesIO(output.getvalue().encode("utf-8-sig")), mimetype="text/csv",
                     as_attachment=True, download_name="invoice_report.csv")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
