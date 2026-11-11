# Daily Work Log & Task Tracker

A local dashboard for recording daily work, tracking task status and priority,
reviewing activity history, and generating weekly and monthly reports.

## Purpose

The application provides a simple, private way to organize work activities in a
local SQLite database. It is designed for a single user running the Flask server
on their own computer.

## Features

- Dashboard statistics, recent activities, completion rate, and charts.
- Add, edit, and delete activities with server-side validation.
- Work History search, date filtering, and pagination.
- Weekly and monthly reports with status, priority, and keyword filters.
- Interactive monthly calendar and report charts.
- CSV and PDF report downloads, plus print-ready weekly and monthly reports.
- Browser printing and Save as PDF with the selected period and report filters.
- SQLite database backup and restore, including validation and a pre-restore
  safety backup.
- Session-bound CSRF protection for state-changing forms.

## Technology

- Python 3.15
- Flask 3.1.3 and Jinja2
- SQLite (Python standard library)
- HTML5, CSS3, and JavaScript
- Chart.js 4.4.7 (loaded from a CDN)
- ReportLab 4.2.5 (PDF reports)

## Project structure

```text
Daily Work Log/
├── app.py
├── database.py
├── requirements.txt
├── daily_work_log.db          # Created locally; excluded from Git
├── database_backups/          # Created for pre-restore safety backups; excluded
├── static/
│   ├── dashboard.js
│   ├── reports.js
│   └── style.css
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── add_activity.html
│   ├── edit_activity.html
│   ├── work_history.html
│   ├── reports.html
│   └── database_management.html
├── README.md
└── PROJECT_STATUS.md
```

## Windows setup

Open PowerShell in the project folder.

1. Install Python 3.15 if it is not already installed.
2. Create and activate a virtual environment:

   ```powershell
   py -3.15 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use the virtual environment's interpreter
   directly with `.venv\Scripts\python.exe`.

3. Install project dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. Initialize the SQLite database:

   ```powershell
   python database.py
   ```

   The database is created as `daily_work_log.db` beside `database.py` if it
   does not already exist. Initialization does not replace an existing database.

5. Start the local application:

   ```powershell
   python app.py
   ```

6. Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

On first startup, the app generates a stable `.flask_secret_key` file in the
project folder. This file is excluded from Git and is used to sign sessions and
CSRF tokens. Keep it private and do not delete it while existing sessions need
to remain valid. Alternatively, set `FLASK_SECRET_KEY` to a private random value
of at least 32 characters before starting the application.

## Database backup and restore

Open **Database** in the sidebar.

- Select **Download Database Backup** to download a timestamped SQLite snapshot.
- To restore, choose a compatible `.sqlite`, `.sqlite3`, or `.db` backup and
  confirm the warning. Restore replaces current data; the app first stores a
  safety backup under the ignored `database_backups/` directory.
- Uploads are limited to 64 MB and checked for SQLite integrity and the required
  application table and columns.

The management endpoints are restricted to loopback clients, and `python app.py`
binds to `127.0.0.1`. Do not expose this single-user application or its restore
feature to a network without adding authentication and access control.

## Print reports

Open **Reports**, select the weekly or monthly tab and period, and choose
**Print Report**. The browser print dialog can send the report to a printer or
save it as a PDF. The printed report keeps the selected period and filters;
this is separate from the existing downloadable PDF export.

## Screenshots

Screenshots are not included yet. Add portfolio images here when available:

- `[Dashboard screenshot placeholder](screenshots/dashboard.png)`
- `[Weekly report screenshot placeholder](screenshots/weekly-report.png)`
- `[Monthly calendar screenshot placeholder](screenshots/monthly-report.png)`
- `[Database management screenshot placeholder](screenshots/database-management.png)`

## Known limitations

- This is a local, single-user application and does not provide user accounts.
- Chart.js is fetched from jsDelivr, so charts require network access unless the
  library is served locally.
- Browser print and Save as PDF output can vary with browser and print-dialog
  paper, margin, and scale settings.
- No automated test suite is included in the repository; see
  `PROJECT_STATUS.md` for the manual and isolated-database checks performed.
