"""Regenerates the three standalone design/user documents under
data/guidelines/Documents/ (User Guide, HLD, LLD) from content defined in this
script. These are project documentation, not RAG-ingested guideline data, and
have no other editable source - this script *is* the source of truth for them.
Run after any change that affects what these documents describe:

    python scripts/generate_platform_docs.py
"""

from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "guidelines", "Documents")

TITLE_BLUE = colors.HexColor("#1a6fa8")
MUTED = colors.HexColor("#5a5a5a")
INK = colors.HexColor("#111111")
BANNER_RED = colors.HexColor("#b03a2e")
TABLE_HEADER = colors.HexColor("#1b4f72")
TABLE_HEADER_TEXT = colors.white
GRIDLINE = colors.HexColor("#e1e0d9")
CALLOUT_BG = colors.HexColor("#fdf3d7")
CALLOUT_BORDER = colors.HexColor("#e9b949")
CODE_BG = colors.HexColor("#eef2f5")

PAGE_W, PAGE_H = letter
MARGIN = 0.7 * inch


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("DocTitle", fontName="Helvetica-Bold", fontSize=28, leading=34, textColor=TITLE_BLUE, alignment=1, spaceAfter=6))
    s.add(ParagraphStyle("DocSubtitle", fontName="Helvetica", fontSize=14, leading=18, textColor=MUTED, alignment=1, spaceAfter=4))
    s.add(ParagraphStyle("Meta", fontName="Helvetica", fontSize=10, textColor=MUTED, alignment=1, leading=15))
    s.add(ParagraphStyle("Banner", fontName="Helvetica-Bold", fontSize=10, textColor=colors.white, alignment=1, leading=13))
    s.add(ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=TITLE_BLUE, spaceBefore=16, spaceAfter=8))
    s.add(ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=TITLE_BLUE, spaceBefore=10, spaceAfter=6))
    s.add(ParagraphStyle("Body", fontName="Helvetica", fontSize=10, textColor=INK, leading=14, spaceAfter=8))
    s.add(ParagraphStyle("BulletItem", parent=s["Body"], leftIndent=14, spaceAfter=4))
    s.add(ParagraphStyle("Num", parent=s["Body"], leftIndent=16, spaceAfter=4))
    s.add(ParagraphStyle("Callout", fontName="Helvetica", fontSize=9.5, textColor=INK, leading=13))
    s.add(ParagraphStyle("Cell", fontName="Helvetica", fontSize=8.5, textColor=INK, leading=11))
    s.add(ParagraphStyle("CellHeader", parent=s["Cell"], fontName="Helvetica-Bold", textColor=TABLE_HEADER_TEXT))
    s.add(ParagraphStyle("CodeBlock", fontName="Courier", fontSize=8, textColor=INK, leading=11))
    return s


S = _styles()


def title_page(doc_type_title: str, doc_type_line: str, version: str, audience: str, companion: str | None = None) -> list:
    els = [Spacer(1, 2.2 * inch), Paragraph(doc_type_title, S["DocTitle"]), Paragraph("Prior Authorization Multi-Agent Platform", S["DocSubtitle"]), Spacer(1, 0.3 * inch)]

    banner = Table(
        [[Paragraph("DEMONSTRATION SYSTEM &mdash; SYNTHETIC DATA &mdash; NOT FOR CLINICAL<br/>OR COVERAGE USE", S["Banner"])]],
        colWidths=[4.6 * inch],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BANNER_RED),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    banner.hAlign = "CENTER"
    els.append(banner)
    els.append(Spacer(1, 0.5 * inch))

    meta_lines = [f"Document type: {doc_type_line}", f"Version {version}", f"Audience: {audience}"]
    if companion:
        meta_lines.append(f"Companion document: {companion}")
    els.append(Paragraph("<br/>".join(meta_lines), S["Meta"]))
    els.append(PageBreak())
    return els


def h1(text: str) -> Paragraph:
    return Paragraph(text, S["H1"])


def h2(text: str) -> Paragraph:
    return Paragraph(text, S["H2"])


def p(text: str) -> Paragraph:
    return Paragraph(text, S["Body"])


def bullets(items: list[str]) -> list:
    return [Paragraph(f"&bull;&nbsp;&nbsp;{t}", S["BulletItem"]) for t in items]


def numbered(items: list[str]) -> list:
    return [Paragraph(f"{i}.&nbsp;&nbsp;{t}", S["Num"]) for i, t in enumerate(items, 1)]


def callout(text: str) -> Table:
    t = Table([[Paragraph(text, S["Callout"])]], colWidths=[6.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CALLOUT_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 3, CALLOUT_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def code(text: str) -> Table:
    t = Table([[Preformatted(text, S["CodeBlock"])]], colWidths=[6.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return t


def data_table(header: list[str], rows: list[list[str]], col_widths: list[float]) -> Table:
    data = [[Paragraph(h, S["CellHeader"]) for h in header]]
    for row in rows:
        data.append([Paragraph(cell, S["Cell"]) for cell in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, GRIDLINE),
            ]
        )
    )
    return t


def make_footer(doc_title_line: str):
    def _draw(c, _doc):
        c.saveState()
        c.setStrokeColor(GRIDLINE)
        c.line(MARGIN, 0.62 * inch, PAGE_W - MARGIN, 0.62 * inch)
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawString(MARGIN, 0.45 * inch, doc_title_line)
        c.drawRightString(PAGE_W - MARGIN, 0.45 * inch, f"Page {c.getPageNumber()}")
        c.restoreState()

    return _draw


def build_pdf(filename: str, footer_title: str, elements: list) -> None:
    path = os.path.join(OUT_DIR, filename)
    doc = SimpleDocTemplate(
        path,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=0.8 * inch,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        title=footer_title,
    )
    footer = make_footer(footer_title)
    doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------
# User Guide
# ---------------------------------------------------------------------------

def build_user_guide() -> list:
    e = title_page(
        "User Guide",
        "User Guide &mdash; features, workflow, and benefits",
        "1.1",
        "clinical reviewers, providers/administrators, and evaluators of the platform",
    )

    e.append(h1("1. Welcome"))
    e.append(p(
        "This platform is a demonstration of how a prior authorization (PA) request can move from submission to "
        "a fully explained, evidence-backed determination &mdash; with a real human always making the final call. "
        "This guide walks through every screen, explains what each feature does, and why it matters."
    ))
    e.append(callout(
        "Every patient and every payer policy in this system is synthetic. Nothing here is a real coverage "
        "decision, and the platform says so on every screen. It exists to demonstrate the workflow, not to make "
        "real determinations."
    ))

    e.append(h1("2. What This Platform Gives You"))
    e.append(data_table(
        ["Feature", "Benefit"],
        [
            ["Structured request intake", "No more free-text guesswork &mdash; requested service, diagnosis codes, urgency, and prior treatments are captured explicitly, up front."],
            ["Live multi-agent pipeline", "Watch each step of the evaluation happen in real time instead of waiting on a single opaque spinner &mdash; you see exactly what the system is doing and when."],
            ["Criterion-by-criterion evidence", "Every individual policy rule is shown as MET, NOT MET, or UNKNOWN with the specific patient fact that justified it &mdash; never a black-box \"denied\"."],
            ["Deterministic, reproducible decisions", "The same request always produces the same determination &mdash; the outcome is a rules engine, not a guess, so it can be explained and defended."],
            ["AI-assisted plain-language rationale", "A clear paragraph explaining the decision, optionally drafted by Anthropic Claude or OpenAI (whichever provider is configured) &mdash; but the AI never makes the decision itself, only explains it."],
            ["Mandatory human review", "Nothing is final until a clinical reviewer signs off &mdash; every determination, whether approved, denied, or pended, goes through this gate."],
            ["Full audit trail", "Every step, every criterion, every reviewer decision is recorded and can be downloaded as a PDF report at any time."],
            ["Operational visibility", "A dashboard shows volume, outcomes, how often reviewers override the AI, per-agent performance, and (if enabled) real AI cost &mdash; filterable to the last 7 days, 30 days, 1 month, or 1 year, all in one place."],
        ],
        [175, 330],
    ))

    e.append(h1("3. Getting Started"))
    e.append(p(
        "Once the platform is running (see the project README for setup), open the frontend in your browser. "
        "You will see four sections in the top navigation:"
    ))
    e += bullets([
        "<b>Patients</b> &mdash; browse synthetic patients and submit new requests.",
        "<b>Review Queue</b> &mdash; determinations waiting for a clinical reviewer's sign-off.",
        "<b>Policy Search</b> &mdash; search the payer policy library directly.",
        "<b>Observability</b> &mdash; system health and operational metrics.",
    ])

    e.append(h1("4. Submitting a Prior Authorization Request"))
    e += numbered([
        "From the <b>Patients</b> page, click a patient card to open their record.",
        "Review the patient's demographics, vitals/labs, history, medications, and allergies at the top of the page.",
        "Scroll to <b>New prior authorization request</b> and fill in:",
    ])
    e.append(data_table(
        ["Field", "What to enter"],
        [
            ["Requested service *", "The procedure, medication, or equipment being requested (e.g. \"Bariatric surgery\", \"Lumbar spine MRI\"). Required."],
            ["Service category", "imaging / surgery / medication / therapy / dme / other."],
            ["Urgency", "routine / urgent / emergent."],
            ["Diagnosis codes", "Comma-separated ICD-10 codes or plain descriptions. Auto-filled from the patient's documented history when you open their record (e.g. a patient with \"type_2_diabetes, hypertension\" pre-fills \"E11.9, I10\") &mdash; add or remove codes to match this specific request."],
            ["Prior treatments tried", "Comma-separated list of what's already been attempted (e.g. \"physical therapy for 8 weeks\")."],
            ["Additional clinical justification", "Optional free-text context for the reviewer."],
        ],
        [150, 355],
    ))
    e += numbered(["Click <b>Submit for determination</b>."])
    e.append(callout(
        "The Requested service field is required. If you submit without it, the field is outlined in red and "
        "focused automatically so you can fill it in immediately &mdash; nothing is lost."
    ))

    e.append(h1("5. Watching the Multi-Agent Pipeline"))
    e.append(p(
        "After you submit, a <b>Multi-agent orchestration</b> panel appears and lights up step by step, live, as "
        "each of the six agents actually finishes its work on the server &mdash; this is not a simulated animation. "
        "Below it, a growing <b>Live agent details</b> log shows the exact input and output each agent produced, "
        "the moment it produced it."
    ))
    e.append(data_table(
        ["Step", "In plain terms"],
        [
            ["Clinical Intake", "Checks the patient record and the request are complete enough to proceed."],
            ["Guideline Retrieval", "Finds the one payer policy document that actually applies to this request."],
            ["Risk Stratification", "Summarizes the patient's overall clinical risk factors for context."],
            ["Criteria Matching", "Checks the request against every individual rule in that policy, one at a time."],
            ["Determination", "Decides approve / deny / pend from the criteria results, and drafts a plain-language explanation."],
            ["Safety Validation", "Double-checks the decision and evidence before handing it off for human review."],
        ],
        [150, 355],
    ))
    e.append(p(
        "If information is critically incomplete, the pipeline stops right after Clinical Intake and returns a "
        "\"pended\" result asking for more information, rather than guessing."
    ))

    e.append(h1("6. Understanding Your Determination"))
    e.append(p("Once the pipeline finishes, a result card appears with:"))
    e += bullets([
        "<b>Determination badge</b> &mdash; Approved (green), Denied (red), or Pended (amber, needs more information or human judgment).",
        "<b>Rationale</b> &mdash; a plain-language explanation, labeled as either AI-drafted (with the provider, model name, and token count) or from the deterministic template (when no AI provider is configured).",
        "<b>Risk factors &amp; identified conditions</b> &mdash; clinical context pulled from the patient's record.",
        "<b>Criteria evaluated</b> &mdash; every policy rule that was checked, each tagged MET, NOT MET, or UNKNOWN, with the specific patient evidence behind that tag.",
        "<b>Retrieved policy evidence</b> &mdash; the actual policy text the determination is grounded in, with a relevance score.",
        "<b>Safety flags</b> &mdash; anything the system wants a human to pay particular attention to (e.g. an allergy/medication overlap, high risk, or evidence it couldn't fully verify).",
    ])
    e.append(callout(
        "Every determination &mdash; even an Approved one &mdash; is explicitly marked as requiring clinical "
        "reviewer sign-off. A banner links straight to that request's entry in the Review Queue."
    ))

    e.append(h1("7. Reviewing a Determination (Human-in-the-Loop)"))
    e.append(p(
        "This is the safety net at the center of the platform: no determination is ever presented as final "
        "without a person confirming it."
    ))
    e += numbered([
        "Open the <b>Review Queue</b> from the top navigation. Every completed determination awaiting sign-off is listed, oldest first, with the patient, requested service, and the AI's determination.",
        "Click a card to open its full detail &mdash; the complete determination (exactly as shown in step 6) alongside a review form.",
        "Enter your name.",
        "Choose <b>Uphold</b> to accept the AI's determination as-is, or <b>Override</b> to replace it.",
        "If overriding, you must select the correct final determination and write a note explaining why &mdash; this is enforced, not optional, so every override is accountable.",
        "Click submit. The request leaves the queue and is now final.",
    ])
    e.append(p(
        "Once reviewed, the reviewer's name, decision, final determination, and notes are permanently attached "
        "to that request and visible on its detail page and in its PDF report."
    ))

    e.append(h1("8. Downloading a PDF Report"))
    e.append(p(
        "From either the request's result screen or its review page, click <b>Download PDF report</b>. The PDF "
        "includes the full determination summary, rationale, every criterion evaluated with its evidence, the "
        "retrieved policy text it's grounded in, any safety flags, and &mdash; once reviewed &mdash; the "
        "reviewer's name, decision, and notes. It is a rendering of exactly what was decided and recorded, "
        "suitable for sharing or filing."
    ))

    e.append(h1("9. The Observability Dashboard"))
    e.append(p("The Observability tab answers \"is the system healthy, and is it working well?\" at a glance."))
    e.append(p(
        "A period selector next to the page title &mdash; <b>Last 7 days</b>, <b>Last 30 days</b>, "
        "<b>Last 1 month</b>, <b>Last 1 year</b>, or <b>All time</b> &mdash; scopes system health, volume &amp; "
        "value, review stats, per-agent stats, and recent requests to that trailing window."
    ))
    e.append(data_table(
        ["Section", "What it tells you"],
        [
            ["System health", "Whether the database, the policy search index, and the AI integration (and which provider &mdash; Anthropic or OpenAI &mdash; it's using) are up."],
            ["Volume & value", "How many requests have come in, how many completed, average turnaround time, and the approve/deny/pend split as a chart."],
            ["Human-in-the-loop review", "How many requests are waiting for review, how many have been reviewed, and the override rate &mdash; how often a human actually disagreed with the AI. This is a key trust indicator."],
            ["Per-agent latency", "How long each of the six agents takes on average and at the slow end (p95), on a chart, so a slow step is easy to spot."],
            ["Per-agent reliability", "How often each agent succeeds versus errors, per agent."],
            ["LLM usage & cost", "If a provider is configured: how many times it was called, how many tokens it used, and an estimated cost. If not configured, it clearly states that a deterministic template is being used instead, and names which environment variable (ANTHROPIC_API_KEY or OPENAI_API_KEY) to set."],
            ["Cost per execution", "A separate filter (Last 7 days / Last 30 days / This month / This year / Custom range) drives a spend trend chart and a per-run cost breakdown, independent of the page-wide period selector above."],
            ["Recent requests", "A quick table of the latest activity within the selected period."],
        ],
        [150, 355],
    ))

    e.append(h1("10. Searching the Policy Library"))
    e.append(p(
        "The <b>Policy Search</b> tab lets you search the payer policy corpus directly &mdash; useful for "
        "understanding what criteria exist for a given service before submitting a request. Enter a query (e.g. "
        "\"bariatric surgery BMI criteria\"), choose how many results to return, and the matching policy sections "
        "appear with their relevance score and source document."
    ))

    e.append(h1("11. Frequently Asked Questions"))
    faq = [
        ("Why did my request come back \"pended\" instead of approved or denied?",
         "Either critical information was missing from the request/patient record, or at least one policy "
         "criterion could not be confidently evaluated (UNKNOWN) &mdash; both route to a human for judgment "
         "rather than a guess."),
        ("Can the AI model deny a request on its own?",
         "No. The approve/deny/pend decision is always produced by a deterministic rules engine from the "
         "evaluated criteria. The AI model, when configured, only writes the explanation for a decision that "
         "has already been made."),
        ("Which AI provider does this use?",
         "Either Anthropic Claude or OpenAI &mdash; selected by the LLM_PROVIDER setting. Only the selected "
         "provider's API key needs to be configured; both are used purely to phrase an already-decided outcome, "
         "never to make it."),
        ("What happens if I try to review the same request twice?",
         "The system rejects it &mdash; a request can only be reviewed once. If a mistake was made, it should "
         "be corrected through your organization's normal correction process, not a second review submission."),
        ("Why do I have to enter notes when I override?",
         "So every disagreement with the AI is accountable and explained &mdash; this is enforced by the "
         "system, not left optional."),
        ("Is any of this real patient or policy data?",
         "No. Every patient and every policy document in this system is synthetic and clearly labeled as "
         "demonstration data throughout the platform and in every generated document."),
    ]
    for q, a in faq:
        e.append(KeepTogether([Paragraph(f"<b>{q}</b>", S["Body"]), Paragraph(a, S["Body"])]))

    e.append(h1("12. Glossary"))
    e.append(data_table(
        ["Term", "Meaning"],
        [
            ["Determination", "The approve / deny / pend outcome for a request."],
            ["Criterion", "One individual rule from a payer policy (e.g. a BMI threshold)."],
            ["MET / NOT MET / UNKNOWN", "Whether a criterion is satisfied, not satisfied, or cannot be confidently evaluated from the information given."],
            ["Uphold", "A reviewer accepts the AI's determination as final."],
            ["Override", "A reviewer replaces the AI's determination with their own, with required notes."],
            ["Override rate", "How often reviewers override the AI &mdash; a trust/quality signal shown on the dashboard."],
            ["Rationale", "The plain-language explanation of why a determination was reached."],
            ["LLM provider", "Which AI vendor drafts the rationale/scenario text &mdash; Anthropic Claude or OpenAI, selected via the LLM_PROVIDER setting."],
        ],
        [150, 355],
    ))

    return e


# ---------------------------------------------------------------------------
# High-Level Design
# ---------------------------------------------------------------------------

def build_hld() -> list:
    e = title_page(
        "High-Level Design",
        "High-Level Design (HLD)",
        "1.1",
        "architects, engineering leads, technical stakeholders",
    )

    e.append(h1("1. Purpose & Scope"))
    e.append(p(
        "This document describes the high-level architecture of the Prior Authorization Multi-Agent Platform: "
        "what problem it solves, how its major components fit together, the technology choices behind it, and "
        "the key design decisions that shape its behavior. It is written for readers who need to understand the "
        "system's shape before diving into implementation detail (covered separately in the companion Low-Level "
        "Design document)."
    ))
    e.append(callout(
        "This is a demonstration platform built on entirely synthetic patients and synthetic payer policies. It "
        "is not connected to any real payer, EHR, or claims system, and no output from it should be treated as "
        "an actual coverage determination."
    ))

    e.append(h1("2. Problem Statement"))
    e.append(p(
        "Prior authorization (PA) is one of the highest-friction workflows in healthcare administration. A "
        "provider requests a procedure, medication, or piece of equipment on behalf of a patient; a payer must "
        "check the request against coverage criteria &mdash; BMI thresholds, step-therapy requirements, "
        "documentation requirements, exclusions &mdash; before approving it. In practice this process is slow, "
        "often opaque to the provider and patient, and prone to inconsistent manual interpretation of policy "
        "text. Delays and unclear denials directly translate into delayed or denied patient care."
    ))
    e.append(p("The platform demonstrates an alternative shape for this workflow:"))
    e += bullets([
        "Every criterion in the applicable policy is evaluated individually and explicitly, not just a single opaque yes/no.",
        "The actual coverage decision is produced by a deterministic, reproducible rules engine &mdash; never by an LLM &mdash; so the same inputs always produce the same decision.",
        "A large language model is used only to explain a decision that has already been made, never to make it.",
        "No determination is ever presented as final without passing through a human clinical reviewer.",
        "Every step &mdash; every agent's input and output, every criterion evaluated, every review decision &mdash; is captured in a durable, queryable audit trail.",
    ])

    e.append(h1("3. System Overview"))
    e.append(p(
        "The platform is a two-tier web application: a React single-page frontend and a Python/FastAPI backend. "
        "The backend runs a sequential pipeline of six purpose-built agents over each incoming request, backed "
        "by a local retrieval-augmented generation (RAG) index of synthetic payer policy documents. The "
        "pipeline's output &mdash; an approve/deny/pend determination with full supporting evidence &mdash; is "
        "queued for mandatory human review before it is considered final. Every run is recorded for both "
        "compliance auditing and operational observability."
    ))
    e.append(h2("3.1 Architecture Diagram"))
    e.append(code(
        "React + TypeScript Frontend (Vite)\n"
        "  Patients | Review Queue | Policy Search | Observability\n"
        "            |\n"
        "            v  (REST + NDJSON streaming, CORS-enabled)\n"
        "  FastAPI REST API (/api/v1)\n"
        "            |\n"
        "            v\n"
        "  Multi-Agent Orchestration Workflow\n"
        "  +---------+----------+----------+-----------+--------------+----------+\n"
        "  | Intake  |Retrieval | Risk     | Criteria  | Determination| Safety   |\n"
        "  | Agent   | Agent    | Agent    | Matching  | Agent (LLM-  | Agent    |\n"
        "  |         |          |          | Agent     | assisted)    |          |\n"
        "  +---------+----+-----+----------+-----------+--------------+----------+\n"
        "                 |\n"
        "                 v\n"
        "      FAISS vector index  <-  Sentence-Transformer embeddings\n"
        "                 |\n"
        "      Synthetic payer policy chunks + metadata (SQLite)\n\n"
        "  Final Response Orchestrator\n"
        "            |\n"
        "            v\n"
        "  Structured determination + criteria + rationale + disclaimer\n"
        "            |\n"
        "            v\n"
        "  Human-in-the-Loop Review Queue  --->  Reviewer uphold / override\n"
        "            |\n"
        "            v\n"
        "  SQLite audit trail (runs, agent trace, criteria, reviews)\n"
        "            |\n"
        "            v\n"
        "  Observability API (period-filterable) + Downloadable PDF Determination Report"
    ))

    e.append(h2("3.2 Major Components"))
    e.append(data_table(
        ["Component", "Responsibility"],
        [
            ["Frontend (React/TypeScript)", "Patient management, PA request submission (with history-informed diagnosis-code pre-fill), live pipeline visualization, review queue UI, observability dashboard, policy search."],
            ["FastAPI Backend", "REST + streaming API surface; routes requests to services; owns the exception-to-HTTP-status mapping."],
            ["Multi-Agent Orchestration", "Six-agent sequential pipeline that turns a request into an evidence-grounded determination."],
            ["RAG / Retrieval Layer", "FAISS vector index over chunked synthetic payer policy documents; sentence-transformer embeddings."],
            ["LLM Integration (optional, pluggable)", "Anthropic Claude or OpenAI call (provider selected via LLM_PROVIDER) that drafts the natural-language rationale and approval-path suggestion for an already-decided outcome; degrades gracefully to a template when unconfigured."],
            ["Persistence (SQLite)", "Patients, guidelines/chunks, orchestration runs, per-agent trace, per-criterion audit records."],
            ["Human-in-the-Loop Review", "Durable review queue; uphold/override workflow; enforced before a determination is final."],
            ["Observability", "Aggregated health, volume, outcome, per-agent reliability/latency, review throughput, and LLM token/cost metrics; scoped by a trailing 7d/30d/month/year window or full history."],
            ["Reporting", "Server-rendered PDF determination report reflecting the stored audit trail."],
        ],
        [175, 330],
    ))

    e.append(h1("4. Technology Stack"))
    e.append(data_table(
        ["Layer", "Technology"],
        [
            ["Backend language/framework", "Python 3.11+, FastAPI, Uvicorn, Pydantic v2"],
            ["Data layer", "SQLAlchemy 2.0 ORM over SQLite"],
            ["Vector search", "FAISS (IndexFlatIP on normalized embeddings)"],
            ["Embeddings", "Sentence-Transformers (all-MiniLM-L6-v2, configurable)"],
            ["LLM", "Anthropic Claude API or OpenAI API (optional; provider selectable via LLM_PROVIDER; official Python SDKs for both)"],
            ["PDF generation", "ReportLab"],
            ["Frontend", "React 18 + TypeScript, built with Vite, React Router"],
            ["Charts", "Recharts (agent latency/reliability, cost trend) + hand-built stacked bars (outcome breakdowns)"],
            ["Testing", "Pytest + pytest-asyncio + FastAPI TestClient (backend); tsc + Vite build (frontend)"],
            ["Deployment", "Docker + docker-compose (backend + nginx-served frontend)"],
        ],
        [175, 330],
    ))

    e.append(h1("5. High-Level Data Flow"))
    e.append(p("A single prior authorization request moves through the system as follows:"))
    e += numbered([
        "A user submits a structured request (requested service, category, diagnosis codes, urgency, prior treatments tried) for a specific patient via the frontend; diagnosis codes are pre-filled from the patient's documented history and remain editable.",
        "The backend streams the request through six agents in sequence, each contributing to a shared workflow state.",
        "The Guideline Retrieval Agent embeds the request and retrieves the single most relevant synthetic payer policy from the FAISS index.",
        "The Criteria Matching Agent extracts every individual numbered criterion from that policy and evaluates each as MET, NOT_MET, or UNKNOWN against the patient/request.",
        "The Determination Agent applies a deterministic rule to the criteria evaluation to decide approve, deny, or pend &mdash; then optionally asks the configured LLM provider to draft the rationale for that decision.",
        "The Safety Agent independently re-derives what the determination should be from the same criteria and flags any mismatch, plus verifies every cited criterion is grounded in retrieved text.",
        "The complete result is persisted (run record, per-agent trace, per-criterion audit rows) and placed into the human review queue.",
        "A clinical reviewer opens the queue, inspects the full AI response, and either upholds or overrides the determination with a required rationale.",
        "The final, reviewed outcome can be downloaded at any time as a PDF report and is reflected in the observability dashboard.",
    ])

    e.append(h1("6. Deployment Architecture"))
    e.append(p(
        "The system ships as two containers orchestrated by docker-compose: a FastAPI backend (port 8000) and "
        "an nginx-served static build of the React frontend (port 3000). The backend downloads and caches its "
        "embedding model on first startup and idempotently builds its FAISS index and seeds demonstration "
        "patients if the database is empty. An optional Anthropic or OpenAI API key (selected via LLM_PROVIDER) "
        "can be supplied as environment variables to enable real LLM-drafted rationales; without either, the "
        "system runs fully offline with a deterministic templated rationale."
    ))
    e.append(code(
        "docker compose up --build\n"
        "  backend  -> http://localhost:8000  (Swagger: /docs)\n"
        "  frontend -> http://localhost:3000"
    ))

    e.append(h1("7. Key Design Decisions & Rationale"))
    e.append(data_table(
        ["Decision", "Rationale"],
        [
            ["The coverage decision is always deterministic; the LLM only drafts rationale text.", "Keeps the actual outcome reproducible and auditable even when the LLM is unavailable, misconfigured, or wrong &mdash; a regulated-adjacent workflow cannot depend on a non-deterministic component for its core decision."],
            ["The LLM provider is pluggable (Anthropic or OpenAI) behind one internal call.", "Avoids a hard dependency on a single model vendor for a component that never makes the actual decision, and keeps both call sites (rationale + approval-path suggestion) provider-agnostic."],
            ["Every completed determination requires human review before being final.", "Mirrors real utilization-management practice and gives the system's own disclaimer (requires_clinician_review) an actual enforced mechanism instead of being just a flag."],
            ["A request is evaluated against exactly one dominant policy, not every policy that scored above the retrieval threshold.", "Prevents unrelated policies (e.g. durable medical equipment criteria) from leaking into an unrelated request (e.g. imaging) purely because a chunk scored reasonably well."],
            ["Negated/exclusion-style criteria never resolve to a confident denial from lexical overlap alone.", "A wrong guess in the 'deny' direction blocks needed care; the safer failure mode is to flag the criterion UNKNOWN and let a human resolve it."],
            ["Every agent's input/output and every criterion evaluated is persisted, not just the final answer.", "Enables both the operator-facing observability dashboard (including its trailing-window filters) and root-cause debugging of any individual determination after the fact."],
            ["The frontend streams per-agent completion events (NDJSON) instead of waiting for the whole pipeline.", "Makes the multi-agent orchestration genuinely visible to the user in real time rather than behind a single opaque spinner."],
        ],
        [200, 305],
    ))

    e.append(h1("8. Non-Functional Considerations"))
    e.append(h2("8.1 Auditability & Compliance-style Traceability"))
    e.append(p(
        "Every run, every agent execution, every evaluated criterion, and every review decision is written to "
        "durable storage with timestamps. A determination's PDF report is a rendering of this stored audit "
        "trail, not a fresh computation, so what a reviewer saw is always reproducible."
    ))
    e.append(h2("8.2 Observability"))
    e.append(p(
        "System health, request volume, outcome mix, per-agent latency/reliability (avg and p95), review-queue "
        "throughput, override rate, and real LLM token/cost usage are all aggregated from the same audit tables "
        "and exposed via a dashboard with proper chart forms (not decorative pie charts) and a validated, "
        "CVD-safe color palette. The request/outcome/agent sections can be scoped to a trailing 7-day, 30-day, "
        "1-month, or 1-year window (or left as full history) independently of the dedicated LLM-cost date "
        "filter, which has its own 7d/30d/month/year/custom range."
    ))
    e.append(h2("8.3 Security & Scope Boundaries"))
    e += bullets([
        "No authentication/authorization layer exists &mdash; the platform is scoped for local/demo use, not multi-tenant production deployment.",
        "No real payer, EHR, or claims (X12 278 / FHIR PriorAuth) integration exists.",
        "All patient and policy data is synthetic and clearly labeled as such throughout the UI and generated documents.",
    ])
    e.append(h2("8.4 Resilience"))
    e.append(p(
        "Agents never crash the workflow: a failure inside any single agent is caught, recorded with status "
        "\"error\" in its trace entry, and the pipeline continues with the remaining agents, degrading "
        "gracefully toward a pended determination with a safety flag rather than a hard failure."
    ))

    e.append(h1("9. Limitations & Future Roadmap"))
    e.append(p("<b>Current limitations</b>"))
    e += bullets([
        "Criteria matching uses lexical heuristics (with a few rule tiers for numeric/step-therapy/exclusion patterns), not a full clinical-NLP or logic-graph engine.",
        "The synthetic policy corpus is small (five documents) and not representative of real-world payer policy volume or complexity.",
        "No authentication, multi-tenancy, or real payer/EHR integration.",
        "LLM cost figures are illustrative estimates, not billing-accurate.",
        "Diagnosis-code pre-fill maps a small, controlled vocabulary of documented conditions to representative ICD-10 codes; it is not a full ICD-10 lookup/autocomplete service.",
    ])
    e.append(p("<b>Roadmap</b>"))
    e += bullets([
        "A logic-aware criteria model with explicit AND/OR grouping between criteria.",
        "Deeper negation/conditional-criteria resolution beyond lexical overlap.",
        "Role-based access control, audit logging, and multi-tenant isolation for a real deployment.",
        "Frontend automated test coverage (component/E2E).",
        "Streaming the LLM-drafted rationale token-by-token, in addition to the existing per-agent pipeline streaming.",
        "A full ICD-10 typeahead/autocomplete for diagnosis codes beyond the current history-based pre-fill.",
    ])

    e.append(h1("10. Glossary"))
    e.append(data_table(
        ["Term", "Meaning"],
        [
            ["PA", "Prior Authorization &mdash; payer approval required before a service is covered."],
            ["Determination", "The approve / deny / pend outcome produced by the platform for a request."],
            ["Criterion", "One individually evaluable rule extracted from a payer policy document."],
            ["HITL", "Human-in-the-Loop &mdash; the mandatory reviewer sign-off gate before a determination is final."],
            ["RAG", "Retrieval-Augmented Generation &mdash; retrieving relevant text before generating/reasoning over it."],
            ["NDJSON", "Newline-Delimited JSON &mdash; one JSON object per line, used for the streaming run endpoint."],
            ["Upheld / Overridden", "Reviewer decision to keep the AI determination as-is, or replace it with their own."],
        ],
        [150, 355],
    ))

    return e


# ---------------------------------------------------------------------------
# Low-Level Design
# ---------------------------------------------------------------------------

def build_lld() -> list:
    e = title_page(
        "Low-Level Design",
        "Low-Level Design (LLD)",
        "1.1",
        "engineers implementing, extending, or maintaining the system",
        companion="High-Level Design (HLD)",
    )

    e.append(h1("1. Module & Package Structure"))
    e.append(h2("1.1 Backend (backend/app/)"))
    e.append(code(
        "app/\n"
        "  api/            health, patients, guidelines, search,\n"
        "                  orchestration, review, observability\n"
        "  core/           config.py (settings incl. LLM_PROVIDER + both\n"
        "                  provider configs), logging.py, exceptions.py\n"
        "  db/             models.py (SQLAlchemy ORM), database.py\n"
        "                  (engine/session), repositories.py\n"
        "  schemas/        Pydantic request/response models (patient,\n"
        "                  guideline, orchestration, response, review,\n"
        "                  observability)\n"
        "  agents/         base.py (BaseAgent), intake_agent,\n"
        "                  retrieval_agent, risk_agent,\n"
        "                  criteria_matching_agent, determination_agent,\n"
        "                  safety_agent\n"
        "  orchestration/  state.py, workflow.py, orchestrator.py,\n"
        "                  determination_rules.py\n"
        "  rag/            embeddings.py, chunker.py, faiss_store.py,\n"
        "                  ingestion.py, retriever.py\n"
        "  services/       orchestration_service, review_service,\n"
        "                  metrics_service, llm_client, report_service,\n"
        "                  patient_service, guideline_service\n"
        "  utils/          text.py, validators.py"
    ))
    e.append(h2("1.2 Frontend (frontend/src/)"))
    e.append(code(
        "src/\n"
        "  api/            client.ts (typed REST client), types.ts\n"
        "                  (mirrors backend schemas)\n"
        "  agentPipeline.ts  live pipeline step defs + pure\n"
        "                    state-transition helpers\n"
        "  charts/         colors.ts, ChartTooltip.tsx, StackedOutcomeBar.tsx,\n"
        "                  AgentLatencyChart.tsx, AgentReliabilityChart.tsx,\n"
        "                  CostTrendChart.tsx\n"
        "  components/     Badge.tsx, SafetyBanner, AssessmentResult, AgentPipeline,\n"
        "                  AgentTraceView, PatientForm\n"
        "  pages/          PatientsPage, PatientDetailPage, GuidelineSearchPage,\n"
        "                  ReviewQueuePage, ReviewDetailPage, ObservabilityPage\n"
        "  App.tsx, main.tsx, index.css"
    ))

    e.append(h1("2. Data Model"))
    e.append(p("SQLite via SQLAlchemy 2.0 ORM. Six tables:"))
    e.append(data_table(
        ["Table", "Key columns", "Purpose"],
        [
            ["patients", "id, patient_identifier (unique), age, gender, vitals/labs, medical_history (JSON), current_medications (JSON), allergies (JSON)", "Synthetic patient records."],
            ["guidelines", "id, guideline_id (unique), title, organization, version, condition, source_file", "One row per ingested synthetic payer policy document."],
            ["guideline_chunks", "id, guideline_id (FK), chunk_id (unique), text, section, page, metadata_json", "Chunked policy text; mirrored 1:1 into the FAISS index by insertion order."],
            ["orchestration_runs", "id, patient_id (FK), requested_service, service_category, diagnosis_codes (JSON), urgency, prior_treatments_tried (JSON), status, determination, decision_rationale, final_response_json, review_status, reviewer_name, reviewer_decision, final_determination, reviewer_notes, reviewed_at, created_at, completed_at", "One row per PA request/run &mdash; both AI-processing state and human-review state live here (two separate dimensions)."],
            ["agent_outputs", "id, run_id (FK), agent_name, status, input_json, output_json, execution_time_ms, created_at", "Full per-agent trace: one row per agent execution per run."],
            ["criteria_evaluations", "id, run_id (FK), criterion, status, patient_evidence, guideline, section, source, created_at", "Durable, independently queryable audit trail of every criterion evaluated (separate from the JSON blob)."],
        ],
        [95, 235, 195],
    ))
    e.append(h2("2.1 Notes on orchestration_runs"))
    e += bullets([
        "<b>status</b> (running / completed / insufficient_information) tracks whether the agent pipeline finished; it is set once, synchronously, within the request/stream call.",
        "<b>review_status</b> (pending_review / reviewed) is a separate dimension: whether a human has signed off. Every completed run starts as pending_review.",
        "<b>determination</b> is the AI's decision; <b>final_determination</b> is what a reviewer confirmed (equal to determination on uphold, reviewer-chosen on override).",
        "<b>final_response_json</b> stores the complete FinalClinicalResponse payload exactly as produced at completion time, so the review screen and the PDF report always reflect what was actually decided, not a re-computation.",
    ])

    e.append(h1("3. Agent Design"))
    e.append(p(
        "All agents implement <b>BaseAgent.execute(state)</b>, which times the call, catches any exception "
        "(recording status=\"error\" instead of propagating), and appends an AgentTrace to the shared "
        "ClinicalWorkflowState. Agents never crash the workflow."
    ))
    e.append(h2("3.1 clinical_intake_agent"))
    e.append(p(
        "Computes BMI if missing (from weight/height). Builds a list of human-readable extracted facts. "
        "Validates required clinical fields and flags a request as missing \"diagnosis code(s)\" if none were "
        "supplied."
    ))
    e.append(h2("3.2 guideline_retrieval_agent"))
    e.append(p(
        "Builds a retrieval query from requested_service + diagnosis_codes + clinical_question + patient "
        "medical_history + prior_treatments_tried. Embeds it (off the event loop via asyncio.to_thread &mdash; "
        "see &sect;7.3), searches FAISS with top_k (default 8), and discards results below "
        "MIN_RELEVANCE_SCORE = 0.15."
    ))
    e.append(h2("3.3 risk_stratification_agent"))
    e.append(p(
        "Deterministic threshold-based classification (blood pressure, lipids, glycemic status, BMI, smoking, "
        "cardiovascular history) into low / moderate / high, used as contextual signal for the "
        "reasoning/rationale steps."
    ))
    e.append(h2("3.4 criteria_matching_agent"))
    e.append(p("The core evaluation engine. Key steps:"))
    e += numbered([
        "Restricts evaluation to the single <b>dominant guideline</b>: the guideline_id whose best-scoring retrieved chunk has the highest score, so unrelated policies never contribute criteria to this request.",
        "Extracts every \"Criterion N: ...\" sentence from the dominant guideline's retrieved chunks via regex.",
        "Classifies each criterion through ordered tiers and evaluates it:",
    ])
    e.append(data_table(
        ["Tier", "Trigger", "Evaluation"],
        [
            ["Numeric (BMI)", "Criterion text contains \"BMI\"", "Parses threshold number(s) from the text and compares directly against the patient's actual BMI value &rarr; MET / NOT_MET / UNKNOWN (if BMI undocumented)."],
            ["Exclusion (negated)", "Text matches an exclusion-hint phrase (e.g. \"is not considered\")", "Never asserts NOT_MET from lexical overlap. Overlap &ge; 2 tokens &rarr; UNKNOWN (flag for reviewer); otherwise not surfaced."],
            ["Step-therapy / documentation", "Text matches a step-therapy hint (e.g. \"conservative therapy\", \"documented participation\")", "MET if the request's prior_treatments_tried overlaps the criterion text; otherwise UNKNOWN (never NOT_MET &mdash; absence of documentation is a gap, not a denial)."],
            ["Default / general", "Everything else", "Token overlap &ge; 2 with patient/request facts &rarr; MET; overlap == 1 &rarr; UNKNOWN; 0 &rarr; not surfaced."],
        ],
        [95, 190, 240],
    ))
    e.append(h2("3.4.1 Design note: two correctness fixes found via live testing"))
    e.append(callout(
        "(1) BMI criteria are alternative qualifying bands (e.g. \"BMI &ge; 40\" OR \"BMI 35-39.9 with a "
        "comorbidity\"), not a checklist every band must pass &mdash; see determination_rules.py, &sect;4. (2) "
        "The exclusion tier was originally allowed to assert NOT_MET from overlap, which could confidently deny "
        "a patient who actually satisfied the negated condition; it now only ever produces UNKNOWN. Both are "
        "covered by dedicated regression tests."
    ))
    e.append(h2("3.5 determination_agent"))
    e.append(p("Deterministically decides the outcome, then optionally drafts the rationale via the configured LLM provider:"))
    e.append(code(
        "not_met = blocking_not_met_criteria(criteria)  # BMI-aware, see below\n"
        "if not_met:          determination = \"denied\"\n"
        "elif any UNKNOWN:    determination = \"pended\"\n"
        "elif any MET:        determination = \"approved\"\n"
        "else:                determination = \"pended\"\n\n"
        "rationale = llm_client.generate_determination_rationale(\n"
        "    requested_service, determination, criteria_evaluated, patient_summary,\n"
        ")  # Anthropic or OpenAI (per LLM_PROVIDER) explains the decision; it never\n"
        "   # changes it. Falls back to a deterministic template if no key is\n"
        "   # configured for the selected provider, or the call fails."
    ))
    e.append(p(
        "Also runs a simple allergy/current-medication substring overlap check and appends a safety flag if one "
        "is found."
    ))
    e.append(h2("3.6 safety_validation_agent"))
    e.append(p(
        "Independently re-derives the expected determination from the same criteria (via the shared "
        "determination_rules.expected_determination()) and flags a mismatch; verifies every cited criterion "
        "string is actually a substring of some retrieved chunk's text; flags missing information and high "
        "overall risk; always sets requires_clinician_review = True."
    ))

    e.append(h1("4. Shared Decision Rules (determination_rules.py)"))
    e.append(p(
        "Both the determination agent (to decide) and the safety agent (to independently re-check) call the "
        "same two functions, so they can never silently diverge on what \"not met\" means:"
    ))
    e.append(code(
        "def blocking_not_met_criteria(criteria):\n"
        "    bmi_has_met = any(\n"
        "        \"bmi\" in c.criterion.lower() and c.status == \"MET\"\n"
        "        for c in criteria\n"
        "    )\n"
        "    return [\n"
        "        c for c in criteria if c.status == \"NOT_MET\"\n"
        "        and not (bmi_has_met and \"bmi\" in c.criterion.lower())\n"
        "    ]\n\n"
        "def expected_determination(criteria):\n"
        "    not_met = blocking_not_met_criteria(criteria)\n"
        "    if not_met:\n"
        "        return \"denied\"\n"
        "    if any(c.status == \"UNKNOWN\" for c in criteria):\n"
        "        return \"pended\"\n"
        "    if any(c.status == \"MET\" for c in criteria):\n"
        "        return \"approved\"\n"
        "    return \"pended\""
    ))

    e.append(h1("5. Orchestration Workflow"))
    e.append(h2("5.1 Agent sequence & routing"))
    e.append(p(
        "ClinicalWorkflow.run_steps(state) is an async generator &mdash; the single source of truth for the "
        "agent sequence &mdash; consumed both by the synchronous POST /orchestration/run (drains it fully) and "
        "the streaming endpoint (yields after each step):"
    ))
    e.append(code(
        "1. clinical_intake_agent\n"
        "   -> if critical fields missing OR missing_information >= 6:\n"
        "        HALT, determination = \"pended\"\n"
        "2. guideline_retrieval_agent\n"
        "3. risk_stratification_agent\n"
        "4. criteria_matching_agent\n"
        "5. determination_agent\n"
        "6. safety_validation_agent"
    ))
    e.append(h2("5.2 Streaming protocol"))
    e.append(p(
        "POST /orchestration/run/stream returns newline-delimited JSON, one object per agent as it completes, "
        "then a final object:"
    ))
    e.append(code(
        "{\"type\": \"agent\", \"agent\": \"clinical_intake_agent\", \"status\": \"success\",\n"
        " \"input\": {...}, \"output\": {...}, \"execution_time_ms\": 0.03}\n"
        "... one line per agent ...\n"
        "{\"type\": \"final\", \"run_id\": 1, \"determination\": \"approved\", ...FinalClinicalResponse}"
    ))
    e.append(callout(
        "Implementation detail with real impact: the embedding call inside guideline_retrieval_agent is "
        "synchronous, CPU-bound work. Left inline, it fully blocks the asyncio event loop &mdash; on Windows' "
        "default ProactorEventLoop this silently prevented any previously-yielded chunk from actually reaching "
        "the client until the blocking call returned, turning \"streaming\" into one buffered burst. Fixed by "
        "wrapping the call in asyncio.to_thread(...) in retrieval_agent.py."
    ))

    e.append(h1("6. API Specification"))
    e.append(data_table(
        ["Method & Path", "Purpose"],
        [
            ["GET /api/v1/health", "DB + vector store liveness."],
            ["POST /api/v1/patients", "Create a synthetic patient."],
            ["GET /api/v1/patients", "List patients."],
            ["GET /api/v1/patients/{id}", "Get one patient."],
            ["GET /api/v1/guidelines", "List ingested policy documents."],
            ["POST /api/v1/guidelines/search", "Semantic search over the policy corpus (query, top_k)."],
            ["POST /api/v1/orchestration/run", "Run the full pipeline synchronously; returns FinalClinicalResponse."],
            ["POST /api/v1/orchestration/run/stream", "Same pipeline, NDJSON streamed per-agent."],
            ["GET /api/v1/orchestration/runs/{id}", "Run summary (status, determination, timestamps)."],
            ["GET /api/v1/orchestration/runs/{id}/trace", "Full per-agent trace for a run."],
            ["GET /api/v1/orchestration/runs/{id}/report.pdf", "Downloadable PDF rendering of the stored determination + review outcome."],
            ["GET /api/v1/review/queue", "Runs with review_status = pending_review, oldest first."],
            ["GET /api/v1/review/{id}", "Full AI response + review state for one run."],
            ["POST /api/v1/review/{id}", "Submit uphold/override; override requires final_determination + notes."],
            ["GET /api/v1/observability/metrics", "Aggregated health/volume/outcome/agent/LLM/review metrics. Accepts ?period=7d|30d|month|year|all (default all) to scope every section to a trailing window."],
            ["GET /api/v1/observability/costs", "LLM spend per execution and by call type. Accepts ?period=7d|30d|month|year|custom (default 30d; custom requires start_date/end_date) and an optional ?model= filter."],
        ],
        [230, 295],
    ))

    e.append(h2("6.1 OrchestrationRunRequest (request body)"))
    e.append(data_table(
        ["Field", "Type", "Notes"],
        [
            ["patient_id", "int", "Required."],
            ["requested_service", "str", "Required, min length 1."],
            ["service_category", "str", "Default \"other\" (imaging / surgery / medication / therapy / dme / other)."],
            ["diagnosis_codes", "list[str]", "Default []."],
            ["urgency", "str", "Default \"routine\" (routine / urgent / emergent)."],
            ["prior_treatments_tried", "list[str]", "Default []."],
            ["clinical_question", "str", "Optional free-text additional context."],
        ],
        [140, 110, 275],
    ))
    e.append(h2("6.2 SubmitReviewRequest (request body)"))
    e.append(data_table(
        ["Field", "Type", "Notes"],
        [
            ["reviewer_name", "str", "Required, min length 1."],
            ["decision", "\"uphold\" | \"override\"", "Required."],
            ["final_determination", "\"approved\"|\"denied\"|\"pended\"", "Required if decision = override; server-validated."],
            ["notes", "str", "Required (non-blank) if decision = override; optional on uphold."],
        ],
        [120, 145, 260],
    ))
    e.append(p(
        "Server-side guards: a run already in review_status = reviewed returns HTTP 400 on a second review "
        "attempt; an override without notes or without final_determination returns HTTP 400."
    ))

    e.append(h1("7. RAG Pipeline Detail"))
    e.append(h2("7.1 Chunking"))
    e.append(p(
        "Policy .txt files are parsed by \"SECTION:\" headers (chunker.py), then each section is split into "
        "&le;600-character sentence-aligned sub-chunks so individual \"Criterion N:\" sentences are never "
        "truncated mid-sentence."
    ))
    e.append(h2("7.2 Embedding & Indexing"))
    e.append(p(
        "A lazily-loaded, process-cached Sentence-Transformers model (default all-MiniLM-L6-v2) embeds chunks "
        "and queries; vectors are L2-normalized and stored in a faiss.IndexFlatIP (inner product on normalized "
        "vectors = cosine similarity), with a JSON metadata sidecar in the same order as the index."
    ))
    e.append(h2("7.3 Retrieval"))
    e.append(p(
        "GuidelineRetrievalAgent.run() calls retriever.search() via asyncio.to_thread(...) (see &sect;5.2 "
        "note). Results below MIN_RELEVANCE_SCORE = 0.15 are discarded before being handed to the criteria "
        "matching agent."
    ))

    e.append(h1("8. LLM Integration (llm_client.py)"))
    e.append(p(
        "generate_determination_rationale() and generate_approval_path_suggestion() are called with the "
        "already-decided determination, the full criteria evaluation, and a short patient summary. Both build "
        "a prompt, then delegate to a single dispatcher:"
    ))
    e.append(code(
        "def _call_llm(prompt, settings) -> tuple[str, LlmUsage]:\n"
        "    if settings.llm_provider == \"openai\":\n"
        "        import openai\n"
        "        client = openai.OpenAI(api_key=settings.openai_api_key)\n"
        "        response = client.chat.completions.create(\n"
        "            model=settings.openai_model,\n"
        "            max_completion_tokens=settings.llm_max_tokens,\n"
        "            messages=[{\"role\": \"user\", \"content\": prompt}],\n"
        "        )\n"
        "        ...  # returns (text, LlmUsage(model, prompt_tokens, completion_tokens))\n\n"
        "    import anthropic\n"
        "    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)\n"
        "    response = client.messages.create(\n"
        "        model=settings.anthropic_model,\n"
        "        max_tokens=settings.llm_max_tokens,\n"
        "        messages=[{\"role\": \"user\", \"content\": prompt}],\n"
        "    )\n"
        "    ...  # returns (text, LlmUsage(model, input_tokens, output_tokens))"
    ))
    e.append(p(
        "The prompt explicitly instructs the model not to change the determination or invent facts beyond what "
        "is listed. On success, the caller returns the drafted text plus an LlmUsage(model, input_tokens, "
        "output_tokens) taken directly from the active provider's response usage field. On any failure &mdash; "
        "no API key for the selected provider, SDK import error, network/API error &mdash; it returns a "
        "deterministic templated rationale built from the same criteria list, sets usage = None, and records "
        "the failure reason, so the pipeline never fails because of this call."
    ))
    e.append(data_table(
        ["Setting", "Default", "Purpose"],
        [
            ["LLM_PROVIDER", "anthropic", "Selects which key/SDK is used below &mdash; \"anthropic\" or \"openai\"."],
            ["ANTHROPIC_API_KEY", "\"\" (disabled)", "Enables the Anthropic path when LLM_PROVIDER=anthropic."],
            ["ANTHROPIC_MODEL", "claude-haiku-4-5-20251001", "Model used for rationale/scenario drafting on Anthropic."],
            ["OPENAI_API_KEY", "\"\" (disabled)", "Enables the OpenAI path when LLM_PROVIDER=openai."],
            ["OPENAI_MODEL", "gpt-4o-mini", "Model used for rationale/scenario drafting on OpenAI."],
            ["LLM_MAX_TOKENS", "500", "Cap on rationale/scenario length."],
            ["LLM_INPUT/OUTPUT_COST_PER_MILLION", "1.0 / 5.0", "Illustrative $/1M-token rates used only for the observability cost estimate."],
        ],
        [150, 150, 225],
    ))

    e.append(h1("9. Human-in-the-Loop Review Detail"))
    e.append(p("State machine on orchestration_runs.review_status:"))
    e.append(code(
        "pending_review\n"
        "  --(POST /review/{id}, decision=uphold)-->\n"
        "  reviewed (decision=upheld, final_determination = AI's)\n\n"
        "pending_review\n"
        "  --(POST /review/{id}, decision=override)-->\n"
        "  reviewed (decision=overridden,\n"
        "            final_determination = reviewer's choice)\n\n"
        "reviewed\n"
        "  --(any further POST)--> 400 Bad Request (no re-review)"
    ))
    e.append(p(
        "review_service.ReviewService encapsulates this; ReviewRepository methods (list_pending_review, "
        "submit_review) are the only writers of these columns."
    ))

    e.append(h1("10. PDF Report Generation (report_service.py)"))
    e.append(p(
        "generate_determination_report(run, patient) renders run.final_response_json (the exact stored "
        "response) plus the run's review columns into a ReportLab Platypus document: a summary table, "
        "rationale, a criteria-evaluated table, a retrieved-evidence table, safety flags, and a human-review "
        "section (reviewer/decision/notes when reviewed, or a not-yet-reviewed notice). This is a pure "
        "rendering step &mdash; it performs no new computation and cannot diverge from what a reviewer actually "
        "saw. Exposed via GET /orchestration/runs/{id}/report.pdf."
    ))
    e.append(p(
        "The platform's standalone design/user documents (this LLD, the HLD, and the User Guide) are generated "
        "the same way, from backend/scripts/generate_platform_docs.py &mdash; a separate ReportLab script, "
        "run manually when these documents' content changes, rather than from live run data."
    ))

    e.append(h1("11. Frontend Component Design"))
    e.append(data_table(
        ["Piece", "Responsibility"],
        [
            ["api/client.ts", "Typed fetch wrapper; runOrchestrationStream() is an async generator that reads the NDJSON response body incrementally via the Streams API."],
            ["agentPipeline.ts", "Canonical 6-step definition (mirrors the backend sequence) + pure functions buildInitialPipeline / applyAgentEvent / finalizePipeline driving the live pipeline UI purely from streamed events &mdash; no polling."],
            ["PatientDetailPage", "PA request form; pre-fills diagnosis codes from the patient's documented medical_history (via a small condition-to-ICD-10 lookup), still freely editable; consumes the stream; renders AgentPipeline + AgentTraceView live, then AssessmentResult on completion."],
            ["AssessmentResult", "Renders a FinalClinicalResponse: determination badge, rationale (+ LLM/template provenance), criteria table, evidence, safety flags, and the PDF download link."],
            ["ReviewQueuePage / ReviewDetailPage", "Lists pending_review runs; detail page reuses AssessmentResult and adds the uphold/override form with client + server-side validation."],
            ["ObservabilityPage + charts/", "Fetches /observability/metrics with a page-level period selector (7d/30d/month/year/all) that re-queries the whole dashboard; separately fetches /observability/costs with its own 7d/30d/month/year/custom filter for the cost trend chart and per-run cost table. Renders health pills, stat tiles, two hand-built stacked-bar charts (status-colored part-to-whole), and Recharts grouped/stacked/line charts (agent latency on a log scale, agent reliability, cost trend) with a shared, palette-validated color module and a shared tooltip component."],
        ],
        [140, 385],
    ))

    e.append(h1("12. Error Handling"))
    e.append(data_table(
        ["Exception", "HTTP status", "Trigger"],
        [
            ["PatientNotFoundError", "404", "Unknown patient_id."],
            ["OrchestrationRunNotFoundError", "404", "Unknown run_id."],
            ["InvalidPayloadError", "400", "Duplicate patient identifier; already-reviewed run; override missing notes/final_determination; report requested for an incomplete run; unknown observability period."],
            ["VectorStoreUnavailableError", "503 (or caught by BaseAgent &rarr; trace status=\"error\")", "FAISS index missing/unreadable."],
            ["EmbeddingModelUnavailableError", "503", "Model failed to load."],
            ["Pydantic validation error", "422", "Malformed request body (e.g. blank requested_service)."],
        ],
        [150, 130, 245],
    ))
    e.append(p(
        "All AppError subclasses are mapped to a JSON body of the shape {error, message, "
        "requires_clinician_review} by a single FastAPI exception handler in main.py."
    ))

    e.append(h1("13. Testing Strategy"))
    e.append(p(
        "65 backend tests (pytest + pytest-asyncio + FastAPI TestClient), fully offline via a deterministic "
        "hashed bag-of-words embedding stand-in (tests/fake_embeddings.py):"
    ))
    e += bullets([
        "Patients: CRUD + validation.",
        "Guidelines: ingestion + search, including a no-relevant-result path.",
        "Each agent in isolation, including the two regression tests for the BMI-alternative-band and negated-exclusion fixes.",
        "Full streaming workflow: event ordering, halted/pended path, agent-failure resilience.",
        "Human-in-the-loop: queue listing, uphold, override, double-review rejection, validation guards.",
        "PDF report: generation for a completed run, a reviewed run, and 404 for a missing run.",
        "LLM provider selection (Anthropic vs. OpenAI) and graceful template fallback on missing key/SDK/call failure.",
        "Observability metrics service: aggregation correctness, empty-history edge case, period-filter scoping (including exclusion of out-of-range runs), and cost-endpoint named/custom period handling.",
    ])
    e.append(p(
        "Frontend correctness is verified via tsc --noEmit, a full Vite production build, and &mdash; for "
        "UI-affecting changes in this project's history &mdash; live runs against the actual dev servers rather "
        "than mocks."
    ))

    return e


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    build_pdf(
        "Prior_Authorization_Platform_User_Guide.pdf",
        "Prior Authorization Multi-Agent Platform \u2014 User Guide",
        build_user_guide(),
    )
    build_pdf(
        "Prior_Authorization_Platform_HLD.pdf",
        "Prior Authorization Multi-Agent Platform \u2014 High-Level Design",
        build_hld(),
    )
    build_pdf(
        "Prior_Authorization_Platform_LLD.pdf",
        "Prior Authorization Multi-Agent Platform \u2014 Low-Level Design",
        build_lld(),
    )


if __name__ == "__main__":
    main()
