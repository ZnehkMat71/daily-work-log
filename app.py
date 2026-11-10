
from datetime import date, datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, flash, Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database import get_connection, initialize_database
import csv
import io


app = Flask(__name__)
app.secret_key = "change-this-to-a-random-secret-before-deployment"

# Make sure the existing database and table are available.
initialize_database()


def is_valid_time(value):
    """Check whether a time uses the HH:MM format."""
    try:
        datetime.strptime(value, "%H:%M")
        return True
    except ValueError:
        return False

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
                ) AS today

            FROM activities
            """,
            (date.today().isoformat(),)
        ).fetchone()

    finally:
        connection.close()



def get_weekly_report(week_offset=0):
    """Return activity statistics and records for a selected week."""

    today = date.today()

    # Calculate Monday and Sunday.
    week_start = today - timedelta(days=today.weekday())
    week_start = week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    connection = get_connection()

    try:
        # Get weekly statistics.
        weekly_stats = connection.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(CASE WHEN status = 'Completed'
                    THEN 1 ELSE 0 END) AS completed,

                SUM(CASE WHEN status = 'In Progress'
                    THEN 1 ELSE 0 END) AS in_progress,

                SUM(CASE WHEN status = 'Pending'
                    THEN 1 ELSE 0 END) AS pending

            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            """,
            (week_start.isoformat(), week_end.isoformat())
        ).fetchone()

        # Get daily activity counts.
        daily_results = connection.execute(
            """
            SELECT
                activity_date,
                COUNT(*) AS total
            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            GROUP BY activity_date
            """,
            (week_start.isoformat(), week_end.isoformat())
        ).fetchall()

        daily_counts = {
            row["activity_date"]: row["total"]
            for row in daily_results
        }

        # Build the seven-day breakdown.
        daily_activity = []

        for day_offset in range(7):
            current_day = week_start + timedelta(days=day_offset)

            daily_activity.append({
                "date": current_day.isoformat(),
                "day": current_day.strftime("%A"),
                "total": daily_counts.get(
                    current_day.isoformat(), 0
                )
            })

        # Get individual activities for the selected week.
        activities = connection.execute(
            """
            SELECT
                id,
                activity_date,
                activity_time,
                title,
                notes,
                priority,
                status
            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            ORDER BY activity_date DESC, id DESC
            """,
            (week_start.isoformat(), week_end.isoformat())
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

    # Diagnostic messages to help find the display problem.
    print("Recent activities found:", len(recent_activities))
    print("Recent activities:", [dict(a) for a in recent_activities])

    return render_template(
        "index.html",
        page_title="Dashboard",
        active_page="dashboard",
        stats=get_stats(),
        recent_activities=recent_activities,
        today=date.today().isoformat(),
    )


@app.route("/activities/new", methods=["GET", "POST"])
def add_activity():
    """Display the form and save a new activity."""
    if request.method == "POST":
        activity_date = request.form.get("activity_date", "").strip()
        activity_time = request.form.get("activity_time", "").strip()
        title = request.form.get("title", "").strip()
        notes = request.form.get("notes", "").strip()
        priority = request.form.get("priority", "Medium")
        status = request.form.get("status", "Pending")

        try:
            datetime.strptime(activity_date, "%Y-%m-%d")
            valid_date = True
        except ValueError:
            valid_date = False

        if not title:
            flash("Please enter an activity title.", "error")
        elif len(title) > 200:
            flash("The activity title must be 200 characters or fewer.", "error")
        elif not valid_date:
            flash("Please enter a valid activity date.", "error")
        elif activity_date > date.today().isoformat():
            flash("The activity date cannot be in the future.", "error")
        elif activity_time and not is_valid_time(activity_time):
            flash("Please enter a valid activity time.", "error")
        elif priority not in ("Low", "Medium", "High"):
            flash("Please select a valid priority.", "error")
        elif status not in ("Pending", "In Progress", "Completed"):
            flash("Please select a valid status.", "error")
        else:
            connection = get_connection()

            try:
                connection.execute(
                    """
                    INSERT INTO activities
                    (activity_date, activity_time, title, notes, priority, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        activity_date,
                        activity_time or None,
                        title,
                        notes,
                        priority,
                        status,
                    ),
                )
                connection.commit()
            finally:
                connection.close()

            flash("Activity saved successfully!", "success")
            return redirect(url_for("work_history"))

    return render_template(
        "add_activity.html",
        page_title="Add Activity",
        active_page="add_activity",
        today=date.today().isoformat(),
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

    connection = get_connection()

    try:
        activity = connection.execute(
            "SELECT * FROM activities WHERE id = ?",
            (activity_id,),
        ).fetchone()

        # Check whether the activity exists.
        if activity is None:
            flash("Activity not found.", "error")
            return redirect(url_for("work_history"))

        # Process the submitted form.
        if request.method == "POST":

            activity_date = request.form.get(
                "activity_date", ""
            ).strip()

            activity_time = request.form.get(
                "activity_time", ""
            ).strip()

            title = request.form.get(
                "title", ""
            ).strip()

            notes = request.form.get(
                "notes", ""
            ).strip()

            priority = request.form.get(
                "priority", "Medium"
            )

            status = request.form.get(
                "status", "Pending"
            )

            # Validate the activity date.
            try:
                datetime.strptime(
                    activity_date,
                    "%Y-%m-%d"
                )
                valid_date = True

            except ValueError:
                valid_date = False

            # Validate the submitted information.
            if not title:
                flash(
                    "Please enter an activity title.",
                    "error"
                )

            elif len(title) > 200:
                flash(
                    "The activity title must be 200 characters or fewer.",
                    "error"
                )

            elif not valid_date:
                flash(
                    "Please enter a valid activity date.",
                    "error"
                )

            elif activity_date > date.today().isoformat():
                flash(
                    "The activity date cannot be in the future.",
                    "error"
                )

            elif activity_time and not is_valid_time(activity_time):
                flash(
                    "Please enter a valid activity time.",
                    "error"
                )

            elif priority not in ("Low", "Medium", "High"):
                flash(
                    "Please select a valid priority.",
                    "error"
                )

            elif status not in (
                "Pending",
                "In Progress",
                "Completed"
            ):
                flash(
                    "Please select a valid status.",
                    "error"
                )

            else:
                # Update the existing activity.
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
                        activity_date,
                        activity_time or None,
                        title,
                        notes,
                        priority,
                        status,
                        activity_id,
                    ),
                )

                connection.commit()

                flash(
                    "Activity updated successfully!",
                    "success"
                )

                return redirect(
                    url_for("work_history")
                )

        # Display the Edit Activity form.
        return render_template(
            "edit_activity.html",
            activity=activity,
            page_title="Edit Activity",
            active_page="work_history",
        )

    finally:
        connection.close()


@app.route("/activities/delete/<int:activity_id>", methods=["POST"])
def delete_activity(activity_id):
    """Delete an existing activity."""

    connection = get_connection()

    try:
        # Check whether the activity exists.
        activity = connection.execute(
            "SELECT id FROM activities WHERE id = ?",
            (activity_id,),
        ).fetchone()

        if activity is None:
            flash("Activity not found.", "error")

            return redirect(
                url_for("work_history")
            )

        # Delete the selected activity.
        connection.execute(
            "DELETE FROM activities WHERE id = ?",
            (activity_id,),
        )

        # Save the database changes.
        connection.commit()

        # Show a success message.
        flash(
            "Activity deleted successfully!",
            "success"
        )

        return redirect(
            url_for("work_history")
        )

    finally:
        connection.close()




@app.route("/reports")
def reports():
    """Display weekly and monthly reports."""

    # Determine the selected report tab.
    active_tab = request.args.get("tab", "weekly")

    # Weekly report navigation.
    week_offset = request.args.get("week", default=0, type=int)
    weekly_report = get_weekly_report(week_offset)

    # Monthly report navigation.
    month_offset = request.args.get("month", default=0, type=int)
    monthly_report = get_monthly_report(month_offset)

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

        # Monthly report data.
        monthly_report=monthly_report,
        month_offset=month_offset,
    )


def get_monthly_report(month_offset=0):
    """Return activity statistics for the selected month."""

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

    connection = get_connection()

    try:
        # Get monthly statistics.
        monthly_stats = connection.execute(
            """
            SELECT
                COUNT(*) AS total,

                SUM(CASE WHEN status = 'Completed'
                    THEN 1 ELSE 0 END) AS completed,

                SUM(CASE WHEN status = 'In Progress'
                    THEN 1 ELSE 0 END) AS in_progress,

                SUM(CASE WHEN status = 'Pending'
                    THEN 1 ELSE 0 END) AS pending

            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            """,
            (month_start.isoformat(), month_end.isoformat())
        ).fetchone()

        # Get daily activity counts.
        daily_results = connection.execute(
            """
            SELECT
                activity_date,
                COUNT(*) AS total
            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            GROUP BY activity_date
            """,
            (month_start.isoformat(), month_end.isoformat())
        ).fetchall()

        daily_counts = {
            row["activity_date"]: row["total"]
            for row in daily_results
        }

        # Build the monthly daily breakdown.
        daily_activity = []

        current_day = month_start

        while current_day <= month_end:
            daily_activity.append({
                "date": current_day.isoformat(),
                "day": current_day.strftime("%A"),
                "total": daily_counts.get(
                    current_day.isoformat(), 0
                )
            })

            current_day += timedelta(days=1)

        # Get individual activities for the selected month.
        activities = connection.execute(
            """
            SELECT
                id,
                activity_date,
                activity_time,
                title,
                notes,
                priority,
                status
            FROM activities
            WHERE activity_date BETWEEN ? AND ?
            ORDER BY activity_date DESC, id DESC
            """,
            (month_start.isoformat(), month_end.isoformat())
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

    if report_type == "weekly":
        week_offset = request.args.get("week", default=0, type=int)
        report = get_weekly_report(week_offset)
        filename = f"weekly_report_{report['week_start'].strftime('%Y-%m-%d')}.csv"

    elif report_type == "monthly":
        month_offset = request.args.get("month", default=0, type=int)
        report = get_monthly_report(month_offset)
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


def _get_report_export_data(report_type, week_offset=None, month_offset=None):
    """Return the selected report payload and filename details."""

    if report_type == "weekly":
        offset = int(week_offset or 0)
        report = get_weekly_report(offset)
        title = "Weekly Report"
        date_range = f"{report['week_start'].strftime('%B %d, %Y')} - {report['week_end'].strftime('%B %d, %Y')}"
        filename = f"weekly_report_{report['week_start'].strftime('%Y-%m-%d')}.pdf"
        return report, title, date_range, filename

    if report_type == "monthly":
        offset = int(month_offset or 0)
        report = get_monthly_report(offset)
        title = "Monthly Report"
        date_range = f"{report['month_start'].strftime('%B %d, %Y')} - {report['month_end'].strftime('%B %d, %Y')}"
        filename = f"monthly_report_{report['month_start'].strftime('%Y-%m')}.pdf"
        return report, title, date_range, filename

    raise ValueError("Invalid report type.")


def _build_pdf_report(report_type, week_offset=None, month_offset=None):
    """Generate a PDF document for the selected report."""

    report, title, date_range, filename = _get_report_export_data(
        report_type,
        week_offset=week_offset,
        month_offset=month_offset,
    )

    buffer = io.BytesIO()
    styles = getSampleStyleSheet()

    def page_setup(canvas_obj, doc):
        canvas_obj.saveState()
        canvas_obj.setFillColor(colors.HexColor("#111827"))
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(36, 780, "Daily Work Log & Task Tracker")
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawRightString(576, 780, f"{title} - {date_range}")
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#475569"))
        canvas_obj.drawString(36, 32, "Daily Work Log & Task Tracker")
        canvas_obj.drawRightString(576, 32, f"Page {canvas_obj.getPageNumber()}")
        canvas_obj.restoreState()

    summary_title_style = ParagraphStyle(
        "reportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#1D4ED8"),
        spaceAfter=8,
        leading=22,
    )

    heading_style = ParagraphStyle(
        "sectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=12,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "bodyText",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#1F2937"),
    )

    small_style = ParagraphStyle(
        "smallText",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#374151"),
    )

    story = [
        Paragraph("Daily Work Log & Task Tracker", summary_title_style),
        Paragraph(title, heading_style),
        Paragraph(f"Period: {date_range}", body_style),
        Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", small_style),
        Spacer(1, 18),
        Paragraph("Summary", heading_style),
    ]

    stats = report.get("stats") or {}
    summary_table = Table([
        ["Metric", "Value"],
        ["Total activities", str(stats["total"] if stats and "total" in stats.keys() else 0)],
        ["Completed", str(stats["completed"] if stats and "completed" in stats.keys() else 0)],
        ["In Progress", str(stats["in_progress"] if stats and "in_progress" in stats.keys() else 0)],
        ["Pending", str(stats["pending"] if stats and "pending" in stats.keys() else 0)],
    ], colWidths=[2.8 * 72, 1.4 * 72])

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
    story.append(Spacer(1, 20))
    story.append(Paragraph("Activity Details", heading_style))

    activities = report.get("activities") or []

    if not activities:
        story.append(Paragraph("No activities recorded for this report period.", body_style))
    else:
        table_rows = [["Date", "Time", "Activity", "Notes", "Priority", "Status"]]

        for activity in activities:
            notes = activity["notes"] if "notes" in activity.keys() else ""
            if not notes:
                notes = "No notes provided."

            table_rows.append([
                activity["activity_date"] if "activity_date" in activity.keys() else "",
                activity["activity_time"] if "activity_time" in activity.keys() else "-",
                Paragraph(activity["title"] if "title" in activity.keys() else "Untitled", body_style),
                Paragraph(notes, small_style),
                activity["priority"] if "priority" in activity.keys() else "",
                activity["status"] if "status" in activity.keys() else "",
            ])

        activity_table = Table(
            table_rows,
            repeatRows=1,
            colWidths=[0.65 * 72, 0.55 * 72, 1.1 * 72, 2.1 * 72, 0.7 * 72, 0.8 * 72],
        )

        activity_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))

        story.append(activity_table)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=48,
        bottomMargin=48,
    )

    doc.build(story, onFirstPage=page_setup, onLaterPages=page_setup)

    pdf_data = buffer.getvalue()
    buffer.close()

    return pdf_data, filename


@app.route("/reports/export/pdf")
def export_report_pdf():
    """Download the currently selected report as a PDF file."""

    report_type = request.args.get("type", "weekly", type=str).strip().lower()

    try:
        if report_type == "weekly":
            week_offset = request.args.get("week", default=0, type=int)
            pdf_data, filename = _build_pdf_report(report_type, week_offset=week_offset)
        elif report_type == "monthly":
            month_offset = request.args.get("month", default=0, type=int)
            pdf_data, filename = _build_pdf_report(report_type, month_offset=month_offset)
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
