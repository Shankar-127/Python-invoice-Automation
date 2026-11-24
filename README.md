# Python Invoice Automation

A complete local web application for creating invoices, calculating totals, generating PDF invoices, saving records in SQLite, and exporting CSV reports. Uses INR (₹) formatting and supports an optional tax/GST percentage.

## Features
- Customer name, email, phone, billing address and invoice date
- Multiple products/services per invoice
- Live subtotal, tax and grand-total calculation
- PDF invoice generation and download
- Persistent SQLite invoice and line-item records
- Dashboard with recent invoices and recorded revenue
- Full invoice report with CSV export
- Responsive interface for desktop and mobile

## Requirements
- Python 3.10 or newer
- pip

## Run on Windows
1. Extract the ZIP.
2. Open the extracted folder.
3. Double-click `run_windows.bat`, or run these commands in Command Prompt:

```bat
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## Run on macOS / Linux

```bash
chmod +x run_unix.sh
./run_unix.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

## Data storage
- SQLite database: `data/invoices.db`
- Generated PDFs: `data/invoices/`
- CSV report: use **Reports → Export CSV**

The `data` folder is created automatically on first run. Back it up regularly to preserve your records.

## Notes
- Tax is entered as a percentage (for example, enter `18` for 18%).
- Amounts are formatted in Indian Rupees. Configure your own business details/branding in `app.py` and the PDF layout before issuing invoices commercially.
- This is a local single-user starter application. Before exposing it to the internet or using it for multi-user production, add authentication, CSRF protection, backups, and appropriate business/tax compliance checks.
