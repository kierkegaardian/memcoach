import csv
import io
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from db.database import get_db
from utils.auth import require_parent_session
from utils.grading import token_diff

router = APIRouter(dependencies=[Depends(require_parent_session)])
base_dir = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))


def _week_range(week_start: date) -> tuple[str, str]:
    start = week_start.isoformat()
    end = (week_start + timedelta(days=7)).isoformat()
    return start, end


def _escape_pdf_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _build_pdf_bytes(lines: list[str]) -> bytes:
    content_lines = []
    y = 720
    for line in lines:
        escaped = _escape_pdf_text(line)
        content_lines.append(f"72 {y} Td ({escaped}) Tj")
        content_lines.append("0 -16 Td")
        y -= 16
    content_stream = "BT /F1 12 Tf\n" + "\n".join(content_lines) + "\nET"
    content_bytes = content_stream.encode("utf-8")
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    )
    objects.append(
        f"4 0 obj << /Length {len(content_bytes)} >> stream\n".encode("utf-8")
        + content_bytes
        + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
    offsets = [0]
    pdf_body = b"%PDF-1.4\n"
    for obj in objects:
        offsets.append(len(pdf_body))
        pdf_body += obj
    xref_start = len(pdf_body)
    xref_entries = [b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref_entries.append(f"{offset:010d} 00000 n \n".encode("utf-8"))
    xref = b"xref\n0 %d\n" % (len(xref_entries)) + b"".join(xref_entries)
    trailer = (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%EOF"
        % (len(xref_entries), xref_start)
    )
    return pdf_body + xref + trailer


def _load_weekly_report(conn, week_start: date) -> dict:
    start, end = _week_range(week_start)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COALESCE(SUM(duration_seconds), 0) AS total_seconds
        FROM reviews
        WHERE ts >= ? AND ts < ?
        """,
        (start, end),
    )
    total_seconds = cursor.fetchone()[0] or 0
    minutes_practiced = round(total_seconds / 60, 1)

    cursor.execute(
        """
        SELECT
            COUNT(DISTINCT r.card_id) AS total_reviewed,
            SUM(CASE WHEN r.final_grade = 'fail' THEN 1 ELSE 0 END) AS fail_count
        FROM reviews r
        WHERE r.ts >= ? AND r.ts < ?
        """,
        (start, end),
    )
    review_row = cursor.fetchone() or (0, 0)
    total_reviewed = review_row[0] or 0
    fail_count = review_row[1] or 0

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM cards
        WHERE mastery_status = 'mastered' AND deleted_at IS NULL
        """,
    )
    mastered_total = cursor.fetchone()[0] or 0

    cursor.execute(
        """
        SELECT
            c.prompt,
            SUM(CASE WHEN r.final_grade = 'fail' THEN 1 ELSE 0 END) AS misses
        FROM reviews r
        JOIN cards c ON c.id = r.card_id
        WHERE r.ts >= ? AND r.ts < ?
        GROUP BY r.card_id
        HAVING misses > 0
        ORDER BY misses DESC, c.prompt
        LIMIT 10
        """,
        (start, end),
    )
    most_missed = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT c.full_text, r.user_text
        FROM reviews r
        JOIN cards c ON c.id = r.card_id
        WHERE r.ts >= ? AND r.ts < ? AND r.user_text IS NOT NULL AND r.user_text != ''
        """,
        (start, end),
    )
    token_counts: dict[str, int] = {}
    for row in cursor.fetchall():
        diff = token_diff(row[0] or "", row[1] or "")
        for item in diff["expected"]:
            if item["status"] in {"missing", "substitution"}:
                token = item["token"].strip().lower()
                if not token:
                    continue
                token_counts[token] = token_counts.get(token, 0) + 1
    most_missed_tokens = sorted(
        ({"token": token, "misses": count} for token, count in token_counts.items()),
        key=lambda entry: (-entry["misses"], entry["token"]),
    )[:10]

    return {
        "week_start": week_start,
        "week_end": week_start + timedelta(days=6),
        "minutes_practiced": minutes_practiced,
        "cards_mastered": mastered_total,
        "cards_slipping": fail_count,
        "cards_reviewed": total_reviewed,
        "most_missed": most_missed,
        "most_missed_tokens": most_missed_tokens,
    }


@router.get("/weekly", response_class=HTMLResponse)
async def weekly_report(
    request: Request,
    week_start: date = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    conn=Depends(get_db),
):
    report = _load_weekly_report(conn, week_start)
    return templates.TemplateResponse(
        "reports/weekly.html",
        {
            "request": request,
            "report": report,
        },
    )


@router.get("/weekly/export")
async def weekly_report_export(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    week_start: date = Query(default_factory=lambda: date.today() - timedelta(days=7)),
    conn=Depends(get_db),
):
    report = _load_weekly_report(conn, week_start)
    if format == "pdf":
        lines = [
            "MemCoach Weekly Report",
            f"Week of {report['week_start']} - {report['week_end']}",
            "",
            f"Minutes practiced: {report['minutes_practiced']}",
            f"Cards reviewed: {report['cards_reviewed']}",
            f"Cards mastered: {report['cards_mastered']}",
            f"Cards slipping: {report['cards_slipping']}",
            "",
            "Most missed cards:",
        ]
        if report["most_missed"]:
            lines.extend(
                f"- {item['prompt']} ({item['misses']} misses)" for item in report["most_missed"]
            )
        else:
            lines.append("- None")
        lines.append("")
        lines.append("Most missed tokens:")
        if report["most_missed_tokens"]:
            lines.extend(
                f"- {item['token']} ({item['misses']} misses)"
                for item in report["most_missed_tokens"]
            )
        else:
            lines.append("- None")
        data = _build_pdf_bytes(lines)
        filename = f"memcoach-weekly-report-{report['week_start']}.pdf"
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Week Start", report["week_start"]])
    writer.writerow(["Week End", report["week_end"]])
    writer.writerow(["Minutes Practiced", report["minutes_practiced"]])
    writer.writerow(["Cards Reviewed", report["cards_reviewed"]])
    writer.writerow(["Cards Mastered", report["cards_mastered"]])
    writer.writerow(["Cards Slipping", report["cards_slipping"]])
    writer.writerow([])
    writer.writerow(["Most Missed Prompt", "Misses"])
    for item in report["most_missed"]:
        writer.writerow([item["prompt"], item["misses"]])
    writer.writerow([])
    writer.writerow(["Most Missed Token", "Misses"])
    for item in report["most_missed_tokens"]:
        writer.writerow([item["token"], item["misses"]])
    data = output.getvalue().encode("utf-8")
    filename = f"memcoach-weekly-report-{report['week_start']}.csv"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
