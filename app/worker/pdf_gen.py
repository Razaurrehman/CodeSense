"""Generate a PDF report from completed scan results using reportlab."""
import os
import re
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

REPORTS_DIR = "/reports"

TASK_LABELS = {
    "bug_scan":        "Bug Scan",
    "explain_code":    "Code Explanation",
    "refactor":        "Refactoring Analysis",
    "similar_bugs":    "Similar Bug Patterns",
    "generate_tests":  "Test Generation",
    "migration_plan":  "Migration Plan",
    "impact_analysis": "Impact Analysis",
    "version_bump":    "Dependency Version Bumps",
    "license_check":   "License Compliance",
    "vuln_scan":       "Vulnerability Scan",
    "pr_review":       "PR Review",
}

# Colour palette
BRAND_BLUE   = colors.HexColor("#3b82f6")
BRAND_DARK   = colors.HexColor("#0f172a")
BRAND_SLATE  = colors.HexColor("#64748b")
SEVERITY_RED = colors.HexColor("#ef4444")
SEVERITY_ORG = colors.HexColor("#f97316")
SEVERITY_YLW = colors.HexColor("#eab308")
SEVERITY_GRN = colors.HexColor("#22c55e")
LIGHT_GREY   = colors.HexColor("#f1f5f9")


def _styles():
    base = getSampleStyleSheet()
    normal = base["Normal"]
    return {
        "title": ParagraphStyle("cs_title", fontSize=28, leading=34,
                                textColor=BRAND_DARK, fontName="Helvetica-Bold",
                                alignment=TA_CENTER),
        "subtitle": ParagraphStyle("cs_subtitle", fontSize=13, leading=18,
                                   textColor=BRAND_SLATE, fontName="Helvetica",
                                   alignment=TA_CENTER),
        "section": ParagraphStyle("cs_section", fontSize=15, leading=20,
                                  textColor=BRAND_DARK, fontName="Helvetica-Bold",
                                  spaceAfter=6),
        "h3": ParagraphStyle("cs_h3", fontSize=12, leading=16,
                              textColor=BRAND_BLUE, fontName="Helvetica-Bold",
                              spaceBefore=8, spaceAfter=4),
        "h4": ParagraphStyle("cs_h4", fontSize=11, leading=14,
                              textColor=BRAND_DARK, fontName="Helvetica-Bold",
                              spaceBefore=6, spaceAfter=2),
        "body": ParagraphStyle("cs_body", fontSize=9, leading=13,
                               textColor=colors.HexColor("#1e293b"),
                               fontName="Helvetica", spaceAfter=4),
        "code": ParagraphStyle("cs_code", fontSize=8, leading=11,
                               textColor=colors.HexColor("#1e293b"),
                               fontName="Courier", spaceAfter=3,
                               backColor=LIGHT_GREY, leftIndent=8, rightIndent=8),
        "meta": ParagraphStyle("cs_meta", fontSize=9, leading=12,
                               textColor=BRAND_SLATE, fontName="Helvetica",
                               alignment=TA_CENTER),
        "badge_done":   ParagraphStyle("cs_badge_done",   fontSize=9, leading=12,
                                       textColor=SEVERITY_GRN, fontName="Helvetica-Bold"),
        "badge_failed": ParagraphStyle("cs_badge_failed", fontSize=9, leading=12,
                                       textColor=SEVERITY_RED, fontName="Helvetica-Bold"),
    }


def _md_to_flowables(text: str, styles: dict) -> list:
    """Convert Markdown-ish output to reportlab flowables."""
    flowables = []
    in_code   = False
    code_buf  = []

    def _xml_escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _safe_para(text: str, style) -> object:
        try:
            return Paragraph(text, style)
        except Exception:
            try:
                return Paragraph(_xml_escape(text), style)
            except Exception:
                return Paragraph(" ", style)

    def flush_code():
        if code_buf:
            block = "\n".join(code_buf)
            for chunk in block.split("\n"):
                escaped = _xml_escape(chunk)
                flowables.append(_safe_para(escaped or " ", styles["code"]))
            code_buf.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_buf.append(line)
            continue

        # Strip inline markdown that reportlab can't render
        safe = (_xml_escape(line)
                .replace("**", ""))  # bold markers removed

        if safe.startswith("### "):
            flowables.append(_safe_para(safe[4:], styles["h3"]))
        elif safe.startswith("## "):
            flowables.append(_safe_para(safe[3:], styles["h3"]))
        elif safe.startswith("# "):
            flowables.append(_safe_para(safe[2:], styles["section"]))
        elif safe.startswith("---") or safe.startswith("==="):
            flowables.append(HRFlowable(width="100%", thickness=0.5,
                                        color=BRAND_SLATE, spaceAfter=4))
        elif safe.startswith("|"):
            flowables.append(_safe_para(safe, styles["code"]))
        elif safe.startswith("- ") or safe.startswith("* "):
            flowables.append(_safe_para("• " + safe[2:], styles["body"]))
        elif not safe.strip():
            flowables.append(Spacer(1, 0.15 * cm))
        else:
            flowables.append(_safe_para(safe, styles["body"]))

    flush_code()
    return flowables


def generate_pdf(job, results: list) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"scan_job_{job.id}.pdf")

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2 * cm,
    )

    sty   = _styles()
    story = []

    # ── Cover page ────────────────────────────────────────────────
    story.append(Spacer(1, 2 * cm))
    story.append(Paragraph("CodeSense", sty["title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("AI Code Intelligence Report", sty["subtitle"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(HRFlowable(width="80%", thickness=1.5, color=BRAND_BLUE,
                             hAlign="CENTER", spaceAfter=12))

    story.append(Paragraph(
        f"<b>Repository:</b> {job.repo_name}",
        ParagraphStyle("cover_repo", fontSize=13, leading=18,
                       textColor=BRAND_DARK, fontName="Helvetica",
                       alignment=TA_CENTER)
    ))
    story.append(Spacer(1, 0.4 * cm))

    generated = (job.completed_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M UTC")
    story.append(Paragraph(f"Generated: {generated}", sty["meta"]))
    story.append(Spacer(1, 1.5 * cm))

    # Summary table
    scan_types = [r for r in results]
    table_data = [["Scan Type", "Status"]]
    for r in scan_types:
        label  = TASK_LABELS.get(r.scan_type, r.scan_type)
        status = "✓ Done" if r.status == "done" else "✗ Failed" if r.status == "failed" else r.status.title()
        table_data.append([label, status])

    tbl = Table(table_data, colWidths=[11 * cm, 4 * cm], hAlign="CENTER")
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  BRAND_BLUE),
        ("TEXTCOLOR",   (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0),  10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("FONTSIZE",    (0, 1), (-1, -1),  9),
        ("FONTNAME",    (0, 1), (-1, -1),  "Helvetica"),
        ("GRID",        (0, 0), (-1, -1),  0.4, BRAND_SLATE),
        ("ALIGN",       (1, 0), (1, -1),   "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1),  "MIDDLE"),
        ("TOPPADDING",  (0, 0), (-1, -1),  5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ]))
    story.append(tbl)
    story.append(PageBreak())

    # ── One section per scan result ───────────────────────────────
    for result in results:
        label = TASK_LABELS.get(result.scan_type, result.scan_type)

        # Section header bar
        header_tbl = Table([[label]], colWidths=[doc.width])
        header_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), BRAND_BLUE),
            ("TEXTCOLOR",    (0, 0), (-1, -1), colors.white),
            ("FONTNAME",     (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 13),
            ("TOPPADDING",   (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
            ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        story.append(header_tbl)
        story.append(Spacer(1, 0.3 * cm))

        if result.status == "failed":
            err_text = (result.output or "unknown error").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(
                f"This scan did not complete: {err_text}",
                sty["badge_failed"]
            ))
        elif result.output:
            story.extend(_md_to_flowables(result.output, sty))
        else:
            story.append(Paragraph("No output captured.", sty["body"]))

        story.append(Spacer(1, 0.5 * cm))
        story.append(HRFlowable(width="100%", thickness=0.3, color=BRAND_SLATE))
        story.append(PageBreak())

    doc.build(story)
    return path
