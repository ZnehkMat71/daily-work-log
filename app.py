
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    send_file,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from database import DATABASE_PATH, get_connection, initialize_database
import csv
import io
from xml.sax.saxutils import escape


app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-before-deployment"
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

# Make sure the existing database and table are available.
initialize_database()


def is_valid_time(value):
    """Check whether a time uses the HH:MM format."""
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False


def validate_activity_form(form):
    """Return normalized activity fields and a validation error, if any."""
    activity_data = {
        "activity_date": form.get("activity_date", "").strip(),
        "activity_time": form.get("activity_time", "").strip(),
        "title": form.get("title", "").strip(),
        "notes": form.get("notes", "").strip(),
        "priority": form.get("priority", "Medium"),
        "status": form.get("status", "Pending"),
    }

    try:
        datetime.strptime(activity_data["activity_date"], "%Y-%m-%d")
    except ValueError:
        valid_date = False
    else:
        valid_date = True

    if not activity_data["title"]:
        error = "Please enter an activity title."
    elif len(activity_data["title"]) > 200:
        error = "The activity title must be 200 characters or fewer."
    elif not valid_date:
        error = "Please enter a valid activity date."
    elif activity_data["activity_date"] > date.today().isoformat():
        error = "The activity date cannot be in the future."
    elif activity_data["activity_time"] and not is_valid_time(
        activity_data["activity_time"]
    ):
        error = "Please enter a valid activity time."
    elif activity_data["priority"] not in ("Low", "Medium", "High"):
        error = "Please select a valid priority."
    elif activity_data["status"] not in (
        "Pending",
        "In Progress",
        "Completed",
    ):
        error = "Please select a valid status."
    else:
        error = None

    return activity_data, error


def get_history_return_params():
    """Get the current Work History search and pagination parameters."""
    return {
        "keyword": request.args.get("keyword", "").strip(),
        "filter_date": request.args.get("filter_date", "").strip(),
        "page": request.args.get("page", 1, type=int) or 1,
    }


def get_stats():
    """Return task counts for the dashboard."""

    connection = get_connection()

    try:
        return connection.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(
                    CASE WHEN status = 'Completed'
                    THEN 1 ELSE 0 END
                ) AS completed,

                SUM(
                    CASE WHEN status = 'In Progress'
                    THEN 1 ELSE 0 END
                ) AS in_progress,

                SUM(
                    CASE WHEN status = 'Pending'
                    THEN 1 ELSE 0 END
                ) AS pending,

                SUM(
                    CASE WHEN activity_date = ?
                    THEN 1 ELSE 0 END
                ) AS today,

                CASE
                    WHEN COUNT(*) = 0 THEN 0
                    ELSE ROUND(
                        100.0 * SUM(
                            CASE WHEN status = 'Completed'
                            THEN 1 ELSE 0 END
                        ) / COUNT(*),
                        1
                    )
                END AS completion_rate

            FROM activities
            """,
            (date.today().isoformat(),)
        ).fetchone()

    finally:
        connection.close()


def get_dashboard_chart_data():
    """Return seven-day activity counts and priority distribution."""
    today = date.today()
    start_date = today - timedelta(days=6)
    connection = get_connection()

    try:
        daily_results = connection.execute(
            """
            SELECT activity_date, COUNT(*) AS total
            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            GROUP BY activity_date
            """,
            (start_date.isoformat(), today.isoformat()),
        ).fetchall()
        priority_results = connection.execute(
            """
            SELECT priority, COUNT(*) AS total
            FROM activities
            GROUP BY priority
            """
        ).fetchall()
    finally:
        connection.close()

    daily_counts = {
        row["activity_date"]: row["total"]
        for row in daily_results
    }
    daily_activity = []

    for day_offset in range(7):
        current_day = start_date + timedelta(days=day_offset)
        daily_activity.append({
            "date": current_day.isoformat(),
            "label": current_day.strftime("%a %b %d").replace(" 0", " "),
            "total": daily_counts.get(current_day.isoformat(), 0),
        })

    priority_counts = {"High": 0, "Medium": 0, "Low": 0}
    for row in priority_results:
        if row["priority"] in priority_counts:
            priority_counts[row["priority"]] = row["total"]

    return {
        "daily_activity": daily_activity,
        "priorities": priority_counts,
    }



def get_report_filters(args):
    """Return validated report filters from query parameters."""

    status = args.get("status", "").strip()
    priority = args.get("priority", "").strip()

    if status not in ("", "Completed", "In Progress", "Pending"):
        status = ""

    if priority not in ("", "High", "Medium", "Low"):
        priority = ""

    return {
        "status": status,
        "priority": priority,
        "search": args.get("search", "").strip(),
    }


def get_report_filter_clause(filters):
    """Build parameterized SQL conditions for report filters."""

    conditions = []
    parameters = []

    if filters["status"]:
        conditions.append("status = ?")
        parameters.append(filters["status"])

    if filters["priority"]:
        conditions.append("priority = ?")
        parameters.append(filters["priority"])

    if filters["search"]:
        conditions.append("(title LIKE ? COLLATE NOCASE OR notes LIKE ? COLLATE NOCASE)")
        search_pattern = f"%{filters['search']}%"
        parameters.extend((search_pattern, search_pattern))

    return conditions, parameters


def get_weekly_report(week_offset=0, filters=None):
    """Return activity statistics and records for a selected week."""

    filters = filters or {"status": "", "priority": "", "search": ""}
    today = date.today()

    # Calculate Monday and Sunday.
    week_start = today - timedelta(days=today.weekday())
    week_start = week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    filter_conditions, filter_parameters = get_report_filter_clause(filters)
    where_clause = "activity_date BETWEEN ? AND ?"
    if filter_conditions:
        where_clause += " AND " + " AND ".join(filter_conditions)
    query_parameters = [
        week_start.isoformat(),
        week_end.isoformat(),
        *filter_parameters,
    ]

    connection = get_connection()

    try:
        # Get weekly statistics.
        weekly_stats = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total,

                SUM(CASE WHEN status = 'Completed'
                    THEN 1 ELSE 0 END) AS completed,

                SUM(CASE WHEN status = 'In Progress'
                    THEN 1 ELSE 0 END) AS in_progress,

                SUM(CASE WHEN status = 'Pending'
                    THEN 1 ELSE 0 END) AS pending

            FROM activities
            WHERE {where_clause}
            """,
            query_parameters
        ).fetchone()

        # Get daily activity counts and status indicators.
        daily_results = connection.execute(
            f"""
            SELECT
                activity_date,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending
            FROM activities
            WHERE {where_clause}
            GROUP BY activity_date
            """,
            query_parameters
        ).fetchall()

        daily_counts = {
            row["activity_date"]: row
            for row in daily_results
        }

        # Build the seven-day breakdown.
        daily_activity = []

        for day_offset in range(7):
            current_day = week_start + timedelta(days=day_offset)
            daily_count = daily_counts.get(current_day.isoformat())

            daily_activity.append({
                "date": current_day.isoformat(),
                "day": current_day.strftime("%A"),
                "total": daily_count["total"] if daily_count else 0,
                "completed": daily_count["completed"] if daily_count else 0,
                "in_progress": daily_count["in_progress"] if daily_count else 0,
                "pending": daily_count["pending"] if daily_count else 0,
            })

        # Get individual activities for the selected week.
        activities = connection.execute(
            f"""
            SELECT
                id,
                activity_date,
                activity_time,
                title,
                notes,
                priority,
                status
            FROM activities
            WHERE {where_clause}
            ORDER BY activity_date DESC, id DESC
            """,
            query_parameters
        ).fetchall()

        return {
            "week_start": week_start,
            "week_end": week_end,
            "stats": weekly_stats,
            "daily_activity": daily_activity,
            "activities": activities
        }

    finally:
        connection.close()


def get_activities(keyword="", filter_date=""):
    """Retrieve activities, optionally searching and filtering by date."""
    connection = get_connection()

    try:
        conditions = []
        parameters = []

        if keyword:
            conditions.append("(title LIKE ? OR notes LIKE ?)")
            search_term = f"%{keyword}%"
            parameters.extend([search_term, search_term])

        if filter_date:
            conditions.append("activity_date = ?")
            parameters.append(filter_date)

        query = "SELECT * FROM activities"

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY activity_date DESC, id DESC"

        return connection.execute(query, parameters).fetchall()
    finally:
        connection.close()


def get_paginated_activities(
    keyword="",
    filter_date="",
    limit=10,
    offset=0
):
    """Retrieve activities for one page."""

    connection = get_connection()

    try:
        conditions = []
        parameters = []

        # Search activity titles and notes.
        if keyword:
            conditions.append(
                "(title LIKE ? OR notes LIKE ?)"
            )

            search_term = f"%{keyword}%"

            parameters.extend([
                search_term,
                search_term
            ])

        # Filter activities by date.
        if filter_date:
            conditions.append(
                "activity_date = ?"
            )

            parameters.append(filter_date)

        # Build the SQL WHERE clause.
        where_clause = ""

        if conditions:
            where_clause = (
                " WHERE " + " AND ".join(conditions)
            )

        # Count matching activities.
        count_query = (
            "SELECT COUNT(*) FROM activities"
            + where_clause
        )

        total_count = connection.execute(
            count_query,
            parameters
        ).fetchone()[0]

        # Retrieve activities for the current page.
        activities_query = (
            "SELECT * FROM activities"
            + where_clause
            + " ORDER BY activity_date DESC, id DESC"
            + " LIMIT ? OFFSET ?"
        )

        activities = connection.execute(
            activities_query,
            parameters + [limit, offset]
        ).fetchall()

        return activities, total_count

    finally:
        connection.close()


@app.route("/")
def dashboard():
    """Show the overview and recent activities."""
    recent_activities = get_activities()[:5]
    chart_data = get_dashboard_chart_data()

    # Diagnostic messages to help find the display problem.
    print("Recent activities found:", len(recent_activities))
    print("Recent activities:", [dict(a) for a in recent_activities])

    return render_template(
        "index.html",
        page_title="Dashboard",
        active_page="dashboard",
        stats=get_stats(),
        recent_activities=recent_activities,
        dashboard_chart_data=chart_data,
        today=date.today().isoformat(),
    )


@app.route("/activities/new", methods=["GET", "POST"])
def add_activity():
    """Display the form and save a new activity."""
    form_data = None

    if request.method == "POST":
        form_data, validation_error = validate_activity_form(request.form)

        if validation_error:
            flash(validation_error, "error")
        else:
            try:
                connection = get_connection()
            except sqlite3.Error:
                flash("Unable to save the activity. Please try again.", "error")
            else:
                try:
                    connection.execute(
                        """
                        INSERT INTO activities
                        (activity_date, activity_time, title, notes, priority, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            form_data["activity_date"],
                            form_data["activity_time"] or None,
                            form_data["title"],
                            form_data["notes"],
                            form_data["priority"],
                            form_data["status"],
                        ),
                    )
                    connection.commit()
                except sqlite3.Error:
                    connection.rollback()
                    flash("Unable to save the activity. Please try again.", "error")
                else:
                    flash("Activity saved successfully!", "success")
                    return redirect(url_for("work_history"))
                finally:
                    connection.close()

    return render_template(
        "add_activity.html",
        page_title="Add Activity",
        active_page="add_activity",
        today=date.today().isoformat(),
        form_data=form_data,
    )



@app.route("/activities")
def work_history():
    """Show activities with search, date filtering, and pagination."""

    import math

    # Get search and date filter values.
    keyword = request.args.get("keyword", "").strip()
    filter_date = request.args.get("filter_date", "").strip()

    # Validate the selected date.
    if filter_date:
        try:
            datetime.strptime(filter_date, "%Y-%m-%d")
        except ValueError:
            filter_date = ""

    # Display 10 activities per page.
    per_page = 10

    # Get the requested page number.
    page = request.args.get("page", 1, type=int)

    # Prevent invalid page numbers.
    page = max(page or 1, 1)

    # Calculate the starting record.
    offset = (page - 1) * per_page

    # Retrieve activities for the current page.
    activities, total_count = get_paginated_activities(
        keyword=keyword,
        filter_date=filter_date,
        limit=per_page,
        offset=offset,
    )

    # Calculate the total number of pages.
    total_pages = math.ceil(total_count / per_page)

    # Redirect if the requested page is beyond the available pages.
    if total_pages > 0 and page > total_pages:
        return redirect(
            url_for(
                "work_history",
                keyword=keyword,
                filter_date=filter_date,
                page=total_pages,
            )
        )

    # Display the Work History page.
    return render_template(
        "work_history.html",
        page_title="Work History",
        active_page="work_history",
        activities=activities,
        keyword=keyword,
        filter_date=filter_date,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
    )




@app.route("/activities/edit/<int:activity_id>", methods=["GET", "POST"])
def edit_activity(activity_id):
    """Display the form and update an existing activity."""

    return_params = get_history_return_params()
    try:
        connection = get_connection()
    except sqlite3.Error:
        flash("Unable to load the activity. Please try again.", "error")
        return redirect(url_for("work_history", **return_params))

    try:
        try:
            activity = connection.execute(
                "SELECT * FROM activities WHERE id = ?",
                (activity_id,),
            ).fetchone()
        except sqlite3.Error:
            flash("Unable to load the activity. Please try again.", "error")
            return redirect(url_for("work_history", **return_params))

        # Check whether the activity exists.
        if activity is None:
            flash("Activity not found.", "error")
            return redirect(url_for("work_history", **return_params))

        form_data = None
        if request.method == "POST":
            form_data, validation_error = validate_activity_form(request.form)

            if validation_error:
                flash(validation_error, "error")
            else:
                try:
                    connection.execute(
                        """
                        UPDATE activities
                        SET activity_date = ?,
                            activity_time = ?,
                            title = ?,
                            notes = ?,
                            priority = ?,
                            status = ?
                        WHERE id = ?
                        """,
                        (
                            form_data["activity_date"],
                            form_data["activity_time"] or None,
                            form_data["title"],
                            form_data["notes"],
                            form_data["priority"],
                            form_data["status"],
                            activity_id,
                        ),
                    )
                    connection.commit()
                except sqlite3.Error:
                    connection.rollback()
                    flash(
                        "Unable to update the activity. Please try again.",
                        "error",
                    )
                else:
                    flash("Activity updated successfully!", "success")
                    return redirect(
                        url_for("work_history", **return_params)
                    )

        return render_template(
            "edit_activity.html",
            activity=activity,
            form_data=form_data,
            return_params=return_params,
            today=date.today().isoformat(),
            page_title="Edit Activity",
            active_page="work_history",
        )

    finally:
        connection.close()


@app.route("/activities/delete/<int:activity_id>", methods=["POST"])
def delete_activity(activity_id):
    """Delete an existing activity."""

    return_params = get_history_return_params()
    try:
        connection = get_connection()
    except sqlite3.Error:
        flash("Unable to delete the activity. Please try again.", "error")
        return redirect(url_for("work_history", **return_params))

    try:
        # Check whether the activity exists.
        try:
            activity = connection.execute(
                "SELECT id FROM activities WHERE id = ?",
                (activity_id,),
            ).fetchone()
        except sqlite3.Error:
            flash("Unable to delete the activity. Please try again.", "error")
            return redirect(url_for("work_history", **return_params))

        if activity is None:
            flash("Activity not found.", "error")
            return redirect(url_for("work_history", **return_params))

        try:
            connection.execute(
                "DELETE FROM activities WHERE id = ?",
                (activity_id,),
            )
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            flash("Unable to delete the activity. Please try again.", "error")
        else:
            flash("Activity deleted successfully!", "success")

        return redirect(url_for("work_history", **return_params))

    finally:
        connection.close()




@app.route("/reports")
def reports():
    """Display weekly and monthly reports."""

    # Determine the selected report tab.
    active_tab = request.args.get("tab", "weekly")
    if active_tab not in ("weekly", "monthly"):
        active_tab = "weekly"
    report_filters = get_report_filters(request.args)

    # Weekly report navigation.
    week_offset = request.args.get("week", default=0, type=int)
    weekly_report = get_weekly_report(week_offset, report_filters)

    # Monthly report navigation.
    month_offset = request.args.get("month", default=0, type=int)
    monthly_report = get_monthly_report(month_offset, report_filters)

    return render_template(
        "reports.html",
        page_title="Reports",
        active_page="reports",
        active_tab=active_tab,
        stats=get_stats(),

        # Current date for calendar highlighting.
        today=date.today().isoformat(),

        # Weekly report data.
        weekly_report=weekly_report,
        week_offset=week_offset,
        report_filters=report_filters,

        # Monthly report data.
        monthly_report=monthly_report,
        month_offset=month_offset,
    )


def get_monthly_report(month_offset=0, filters=None):
    """Return activity statistics for the selected month."""

    filters = filters or {"status": "", "priority": "", "search": ""}
    today = date.today()

    # Calculate the selected month.
    month_index = (today.year * 12 + today.month - 1) + month_offset
    year, month = divmod(month_index, 12)
    month += 1

    month_start = date(year, month, 1)

    # Calculate the last day of the selected month.
    next_month_index = year * 12 + month
    next_year, next_month = divmod(next_month_index, 12)
    next_month += 1

    next_month_start = date(next_year, next_month, 1)
    month_end = next_month_start - timedelta(days=1)

    filter_conditions, filter_parameters = get_report_filter_clause(filters)
    where_clause = "activity_date BETWEEN ? AND ?"
    if filter_conditions:
        where_clause += " AND " + " AND ".join(filter_conditions)
    query_parameters = [
        month_start.isoformat(),
        month_end.isoformat(),
        *filter_parameters,
    ]

    connection = get_connection()

    try:
        # Get monthly statistics.
        monthly_stats = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total,

                SUM(CASE WHEN status = 'Completed'
                    THEN 1 ELSE 0 END) AS completed,

                SUM(CASE WHEN status = 'In Progress'
                    THEN 1 ELSE 0 END) AS in_progress,

                SUM(CASE WHEN status = 'Pending'
                    THEN 1 ELSE 0 END) AS pending

            FROM activities
            WHERE {where_clause}
            """,
            query_parameters
        ).fetchone()

        # Get daily activity counts and status indicators.
        daily_results = connection.execute(
            f"""
            SELECT
                activity_date,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending
            FROM activities
            WHERE {where_clause}
            GROUP BY activity_date
            """,
            query_parameters
        ).fetchall()

        daily_counts = {
            row["activity_date"]: row
            for row in daily_results
        }

        # Build the monthly daily breakdown.
        daily_activity = []

        current_day = month_start

        while current_day <= month_end:
            daily_count = daily_counts.get(current_day.isoformat())
            daily_activity.append({
                "date": current_day.isoformat(),
                "day": current_day.strftime("%A"),
                "total": daily_count["total"] if daily_count else 0,
                "completed": daily_count["completed"] if daily_count else 0,
                "in_progress": daily_count["in_progress"] if daily_count else 0,
                "pending": daily_count["pending"] if daily_count else 0,
            })

            current_day += timedelta(days=1)

        # Get individual activities for the selected month.
        activities = connection.execute(
            f"""
            SELECT
                id,
                activity_date,
                activity_time,
                title,
                notes,
                priority,
                status
            FROM activities
            WHERE {where_clause}
            ORDER BY activity_date DESC, id DESC
            """,
            query_parameters
        ).fetchall()

        return {
            "month_start": month_start,
            "month_end": month_end,
            "stats": monthly_stats,
            "daily_activity": daily_activity,
            "activities": activities
        }

    finally:
        connection.close()

@app.route("/reports/export")
def export_report():
    """Export the currently selected weekly or monthly report as CSV."""

    report_type = request.args.get("type", "weekly", type=str).strip().lower()
    report_filters = get_report_filters(request.args)

    if report_type == "weekly":
        week_offset = request.args.get("week", default=0, type=int)
        report = get_weekly_report(week_offset, report_filters)
        filename = f"weekly_report_{report['week_start'].strftime('%Y-%m-%d')}.csv"

    elif report_type == "monthly":
        month_offset = request.args.get("month", default=0, type=int)
        report = get_monthly_report(month_offset, report_filters)
        filename = f"monthly_report_{report['month_start'].strftime('%Y-%m')}.csv"

    else:
        return "Invalid report type.", 400

    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")

    writer.writerow([
        "Date",
        "Time",
        "Activity",
        "Notes",
        "Priority",
        "Status"
    ])

    for activity in report.get("activities", []):
        writer.writerow([
            activity["activity_date"] if "activity_date" in activity.keys() else "",
            activity["activity_time"] if "activity_time" in activity.keys() else "",
            activity["title"] if "title" in activity.keys() else "",
            activity["notes"] if "notes" in activity.keys() else "",
            activity["priority"] if "priority" in activity.keys() else "",
            activity["status"] if "status" in activity.keys() else ""
        ])

    csv_data = output.getvalue().encode("utf-8-sig")

    return Response(
        csv_data,
        content_type="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


def _get_report_export_data(
    report_type,
    week_offset=None,
    month_offset=None,
    filters=None,
):
    """Return the selected report payload and filename details."""

    if report_type == "weekly":
        offset = int(week_offset or 0)
        report = get_weekly_report(offset, filters)
        title = "Weekly Report"
        date_range = f"{report['week_start'].strftime('%B %d, %Y')} - {report['week_end'].strftime('%B %d, %Y')}"
        filename = f"weekly_report_{report['week_start'].strftime('%Y-%m-%d')}.pdf"
        return report, title, date_range, filename

    if report_type == "monthly":
        offset = int(month_offset or 0)
        report = get_monthly_report(offset, filters)
        title = "Monthly Report"
        date_range = f"{report['month_start'].strftime('%B %d, %Y')} - {report['month_end'].strftime('%B %d, %Y')}"
        filename = f"monthly_report_{report['month_start'].strftime('%Y-%m')}.pdf"
        return report, title, date_range, filename

    raise ValueError("Invalid report type.")


def _build_pdf_report(
    report_type,
    week_offset=None,
    month_offset=None,
    filters=None,
):
    """Generate a PDF document for the selected report."""

    report, title, date_range, filename = _get_report_export_data(
        report_type,
        week_offset=week_offset,
        month_offset=month_offset,
        filters=filters,
    )

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    def page_setup(canvas_obj, doc):
        page_width, page_height = doc.pagesize
        left_edge = doc.leftMargin
        right_edge = page_width - doc.rightMargin

        canvas_obj.saveState()
        canvas_obj.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas_obj.setLineWidth(0.7)
        canvas_obj.line(left_edge, page_height - 34, right_edge, page_height - 34)
        canvas_obj.setFillColor(colors.HexColor("#0F172A"))
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(left_edge, page_height - 26, "Daily Work Log & Task Tracker")
        canvas_obj.setFillColor(colors.HexColor("#475569"))
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(right_edge, page_height - 26, title)
        canvas_obj.line(left_edge, 42, right_edge, 42)
        canvas_obj.setFillColor(colors.HexColor("#475569"))
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(left_edge, 29, "Daily Work Log & Task Tracker")
        canvas_obj.drawRightString(right_edge, 29, f"Page {canvas_obj.getPageNumber()}")
        canvas_obj.restoreState()

    summary_title_style = ParagraphStyle(
        "reportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        alignment=0,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=5,
        leading=24,
    )

    period_style = ParagraphStyle(
        "reportPeriod",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1D4ED8"),
    )

    heading_style = ParagraphStyle(
        "sectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=8,
        spaceAfter=10,
    )

    body_style = ParagraphStyle(
        "bodyText",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#1F2937"),
        splitLongWords=1,
    )

    small_style = ParagraphStyle(
        "smallText",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#374151"),
        splitLongWords=1,
    )

    table_header_style = ParagraphStyle(
        "tableHeader",
        parent=small_style,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = [
        Paragraph(escape(title), summary_title_style),
        Paragraph(escape(date_range), period_style),
        Paragraph(
            f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            small_style,
        ),
        Spacer(1, 20),
        Paragraph("Summary", heading_style),
    ]

    stats = report.get("stats") or {}
    summary_table = Table([
        ["Metric", "Value"],
        ["Total activities", str(stats["total"] if stats and "total" in stats.keys() else 0)],
        ["Completed", str(stats["completed"] if stats and "completed" in stats.keys() else 0)],
        ["In Progress", str(stats["in_progress"] if stats and "in_progress" in stats.keys() else 0)],
        ["Pending", str(stats["pending"] if stats and "pending" in stats.keys() else 0)],
    ], colWidths=[3.6 * 72, 1.2 * 72], hAlign="LEFT")

    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 22))
    story.append(Paragraph("Activity Details", heading_style))

    activities = report.get("activities") or []

    if not activities:
        empty_message = "No activities were recorded during this report period."
        if filters and any(filters.values()):
            empty_message = "No activities matched this report period and its filters."

        empty_style = ParagraphStyle(
            "emptyReport",
            parent=body_style,
            textColor=colors.HexColor("#475569"),
            spaceAfter=0,
        )
        empty_state = Table(
            [[Paragraph(escape(empty_message), empty_style)]],
            colWidths=[7.5 * 72],
            hAlign="LEFT",
        )
        empty_state.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
            ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(empty_state)
    else:
        table_rows = [[
            Paragraph("Date", table_header_style),
            Paragraph("Time", table_header_style),
            Paragraph("Activity", table_header_style),
            Paragraph("Notes", table_header_style),
            Paragraph("Priority", table_header_style),
            Paragraph("Status", table_header_style),
        ]]

        for activity in activities:
            notes = activity["notes"] if "notes" in activity.keys() else ""
            if not notes:
                notes = "No notes provided."
            activity_time = activity["activity_time"] if "activity_time" in activity.keys() else None

            table_rows.append([
                Paragraph(escape(str(activity["activity_date"] if "activity_date" in activity.keys() else "")), small_style),
                Paragraph(escape(str(activity_time or "—")), small_style),
                Paragraph(escape(str(activity["title"] if "title" in activity.keys() else "Untitled")), body_style),
                Paragraph(escape(str(notes)).replace("\n", "<br/>"), small_style),
                Paragraph(escape(str(activity["priority"] if "priority" in activity.keys() else "")), small_style),
                Paragraph(escape(str(activity["status"] if "status" in activity.keys() else "")), small_style),
            ])

        activity_table = LongTable(
            table_rows,
            repeatRows=1,
            splitByRow=1,
            splitInRow=0,
            colWidths=[0.78 * 72, 0.58 * 72, 1.35 * 72, 2.65 * 72, 0.82 * 72, 1.32 * 72],
            hAlign="LEFT",
        )

        activity_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))

        story.append(activity_table)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=56,
        bottomMargin=56,
    )

    doc.build(story, onFirstPage=page_setup, onLaterPages=page_setup)

    pdf_data = buffer.getvalue()
    buffer.close()

    return pdf_data, filename


@app.route("/reports/export/pdf")
def export_report_pdf():
    """Download the currently selected report as a PDF file."""

    report_type = request.args.get("type", "weekly", type=str).strip().lower()
    report_filters = get_report_filters(request.args)

    try:
        if report_type == "weekly":
            week_offset = request.args.get("week", default=0, type=int)
            pdf_data, filename = _build_pdf_report(
                report_type,
                week_offset=week_offset,
                filters=report_filters,
            )
        elif report_type == "monthly":
            month_offset = request.args.get("month", default=0, type=int)
            pdf_data, filename = _build_pdf_report(
                report_type,
                month_offset=month_offset,
                filters=report_filters,
            )
        else:
            return "Invalid report type.", 400
    except ValueError:
        return "Invalid report type.", 400
    except Exception:
        return "Unable to generate the PDF report right now.", 500

    return Response(
        pdf_data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

if __name__ == "__main__":
    app.run(debug=True)
