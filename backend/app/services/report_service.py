import io
import json
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.db.models import OrchestrationRun, Patient

_INK = colors.HexColor("#0b0b0b")
_MUTED = colors.HexColor("#52514e")
_GRIDLINE = colors.HexColor("#e1e0d9")
_STATUS_COLORS = {
    "approved": colors.HexColor("#0ca30c"),
    "upheld": colors.HexColor("#0ca30c"),
    "met": colors.HexColor("#0ca30c"),
    "denied": colors.HexColor("#d03b3b"),
    "not_met": colors.HexColor("#d03b3b"),
    "pended": colors.HexColor("#fab219"),
    "overridden": colors.HexColor("#fab219"),
    "unknown": colors.HexColor("#fab219"),
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("ReportTitle", parent=styles["Title"], fontSize=17, spaceAfter=2))
    styles.add(ParagraphStyle("Notice", parent=styles["BodyText"], fontSize=8, textColor=_MUTED))
    styles.add(ParagraphStyle("SectionHeading", parent=styles["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle("CellMuted", parent=styles["Cell"], textColor=_MUTED))
    styles.add(ParagraphStyle("Disclaimer", parent=styles["BodyText"], fontSize=8, textColor=_MUTED, leading=11))
    return styles


def _status_badge(status: str, styles) -> Paragraph:
    color = _STATUS_COLORS.get(status.lower(), _MUTED)
    return Paragraph(f'<font color="{color.hexval()}"><b>{status.upper()}</b></font>', styles["Cell"])


def _summary_table(run: OrchestrationRun, patient: Patient, determination: str, styles) -> Table:
    rows = [
        ["Run ID", f"#{run.id}"],
        ["Patient", patient.patient_identifier if patient else f"Patient {run.patient_id}"],
        ["Requested service", run.requested_service or "-"],
        ["Service category", run.service_category or "-"],
        ["Urgency", run.urgency],
        ["Diagnosis code(s)", ", ".join(json.loads(run.diagnosis_codes or "[]")) or "-"],
        ["Submitted", run.created_at.strftime("%Y-%m-%d %H:%M UTC") if run.created_at else "-"],
    ]
    data = [[Paragraph(f"<b>{label}</b>", styles["CellMuted"]), Paragraph(str(value), styles["Cell"])] for label, value in rows]
    data.insert(0, [Paragraph("<b>Determination</b>", styles["CellMuted"]), _status_badge(determination, styles)])

    table = Table(data, colWidths=[150, 330])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _GRIDLINE),
            ]
        )
    )
    return table


def _criteria_table(criteria: list[dict], styles) -> Table:
    header = [
        Paragraph("<b>Status</b>", styles["Cell"]),
        Paragraph("<b>Criterion</b>", styles["Cell"]),
        Paragraph("<b>Evidence</b>", styles["Cell"]),
    ]
    rows = [header]
    for c in criteria:
        rows.append(
            [
                _status_badge(c.get("status", ""), styles),
                Paragraph(c.get("criterion", ""), styles["Cell"]),
                Paragraph(c.get("patient_evidence") or "-", styles["CellMuted"]),
            ]
        )
    table = Table(rows, colWidths=[62, 210, 208], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _GRIDLINE),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f7fafc")),
            ]
        )
    )
    return table


def _evidence_table(evidence: list[dict], styles) -> Table:
    header = [
        Paragraph("<b>Policy / Section</b>", styles["Cell"]),
        Paragraph("<b>Evidence</b>", styles["Cell"]),
        Paragraph("<b>Relevance</b>", styles["Cell"]),
    ]
    rows = [header]
    for e in evidence:
        rows.append(
            [
                Paragraph(f"{e.get('guideline', '')}<br/><i>{e.get('section', '')}</i>", styles["CellMuted"]),
                Paragraph(e.get("evidence", ""), styles["Cell"]),
                Paragraph(f"{round(e.get('relevance_score', 0) * 100)}%", styles["Cell"]),
            ]
        )
    table = Table(rows, colWidths=[130, 280, 70], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, _GRIDLINE),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f7fafc")),
            ]
        )
    )
    return table


def generate_determination_report(run: OrchestrationRun, patient: Patient | None) -> bytes:
    """Renders the stored final response (+ human review outcome, if any) for this
    run into a PDF determination report. Pulls only from data already persisted at
    completion/review time - the PDF is a rendering of the audit trail, not a new
    computation."""
    styles = _styles()
    final_response = json.loads(run.final_response_json or "{}")
    determination = run.final_determination or run.determination or "pended"

    elements: list = []
    elements.append(Paragraph("Prior Authorization Determination Report", styles["ReportTitle"]))
    elements.append(
        Paragraph(
            "SYNTHETIC DEMONSTRATION DOCUMENT — generated by a decision-support platform using synthetic "
            "data and synthetic payer policies. This is not an actual coverage determination.",
            styles["Notice"],
        )
    )
    elements.append(Spacer(1, 10))
    elements.append(_summary_table(run, patient, determination, styles))

    elements.append(Paragraph("Rationale", styles["SectionHeading"]))
    elements.append(Paragraph(run.decision_rationale or "No rationale was recorded.", styles["Cell"]))

    criteria = final_response.get("criteria_evaluated", [])
    elements.append(Paragraph("Criteria Evaluated", styles["SectionHeading"]))
    if criteria:
        elements.append(_criteria_table(criteria, styles))
    else:
        elements.append(Paragraph("No specific coverage criteria were evaluated for this request.", styles["Cell"]))

    evidence = final_response.get("guideline_evidence", [])
    if evidence:
        elements.append(Paragraph("Retrieved Policy Evidence", styles["SectionHeading"]))
        elements.append(_evidence_table(evidence, styles))

    safety_flags = final_response.get("safety_flags", [])
    if safety_flags:
        elements.append(Paragraph("Safety Flags", styles["SectionHeading"]))
        for flag in safety_flags:
            elements.append(Paragraph(f"&bull; {flag}", styles["Cell"]))

    elements.append(Paragraph("Human Review", styles["SectionHeading"]))
    if run.review_status == "reviewed":
        review_rows = [
            [Paragraph("<b>Reviewer</b>", styles["CellMuted"]), Paragraph(run.reviewer_name or "-", styles["Cell"])],
            [Paragraph("<b>Decision</b>", styles["CellMuted"]), _status_badge(run.reviewer_decision or "-", styles)],
            [Paragraph("<b>Final determination</b>", styles["CellMuted"]), _status_badge(run.final_determination or determination, styles)],
            [
                Paragraph("<b>Reviewed at</b>", styles["CellMuted"]),
                Paragraph(run.reviewed_at.strftime("%Y-%m-%d %H:%M UTC") if run.reviewed_at else "-", styles["Cell"]),
            ],
            [Paragraph("<b>Notes</b>", styles["CellMuted"]), Paragraph(run.reviewer_notes or "-", styles["Cell"])],
        ]
        review_table = Table(review_rows, colWidths=[150, 330])
        review_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, _GRIDLINE),
                ]
            )
        )
        elements.append(review_table)
    else:
        elements.append(
            Paragraph(
                "This determination has not yet been reviewed by a clinical reviewer and is not final.",
                styles["Cell"],
            )
        )

    elements.append(Spacer(1, 16))
    elements.append(HRFlowable(width="100%", color=_GRIDLINE))
    elements.append(Spacer(1, 8))
    elements.append(
        Paragraph(
            final_response.get(
                "disclaimer",
                "This platform is a prior-authorization decision-support demonstration using synthetic data "
                "and synthetic payer policies. It is not a substitute for professional clinical or "
                "utilization-management judgment. Final coverage decisions must be made by an appropriately "
                "qualified clinical reviewer using authoritative, current payer policy.",
            ),
            styles["Disclaimer"],
        )
    )
    elements.append(
        Paragraph(f"Report generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.", styles["Disclaimer"])
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        title=f"Prior Authorization Determination Report #{run.id}",
    )
    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
