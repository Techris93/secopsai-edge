from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from secopsai_api.models import Report


INK = colors.HexColor("#1F2933")
MUTED = colors.HexColor("#52606D")
LINE = colors.HexColor("#D9DED7")
PAPER = colors.HexColor("#F5F7F5")
SEA = colors.HexColor("#0F766E")
SEVERITY_COLORS = {
    "critical": colors.HexColor("#B42318"),
    "high": colors.HexColor("#C2410C"),
    "medium": colors.HexColor("#B7791F"),
    "low": colors.HexColor("#166534"),
    "info": MUTED,
}
FONT_REGULAR = "SecOpsSans"
FONT_BOLD = "SecOpsSans-Bold"


def _register_fonts() -> None:
    font_root = Path(reportlab.__file__).resolve().parent / "fonts"
    if FONT_REGULAR not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_REGULAR, font_root / "Vera.ttf"))
    if FONT_BOLD not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_BOLD, font_root / "VeraBd.ttf"))


def render_report_pdf(report: Report, site_name: str) -> bytes:
    _register_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=report.title,
        author="SecOpsAI",
        subject="SecOpsAI Edge security report",
        pageCompression=0,
    )
    styles = _styles()
    content = report.content if isinstance(report.content, dict) else {}
    findings = content.get("findings") if isinstance(content.get("findings"), list) else []
    actions = content.get("recommended_actions") if isinstance(content.get("recommended_actions"), list) else []
    metrics = content.get("metrics") if isinstance(content.get("metrics"), dict) else {}

    story = [
        Paragraph("SECOPSAI EDGE REPORT", styles["eyebrow"]),
        Spacer(1, 3 * mm),
        Paragraph(_safe(report.title), styles["title"]),
        Spacer(1, 3 * mm),
        Paragraph(_safe(report.summary), styles["summary"]),
        Spacer(1, 6 * mm),
        _meta_table(report, site_name, content, styles),
        Spacer(1, 7 * mm),
        Paragraph("Executive Metrics", styles["heading"]),
        Spacer(1, 3 * mm),
        _metrics_table(metrics, styles),
        Spacer(1, 7 * mm),
        Paragraph("Severity Summary", styles["heading"]),
        Spacer(1, 3 * mm),
        _severity_table(metrics, styles),
        Spacer(1, 7 * mm),
        Paragraph("Recommended Actions", styles["heading"]),
        Spacer(1, 2 * mm),
    ]

    if actions:
        for index, action in enumerate(actions, start=1):
            story.append(Paragraph(f"<b>{index}.</b> {_safe(action)}", styles["body"]))
            story.append(Spacer(1, 1.5 * mm))
    else:
        story.append(Paragraph("No recommended actions were included.", styles["body"]))

    if findings:
        for index, item in enumerate(findings):
            finding = item if isinstance(item, dict) else {}
            severity = str(finding.get("severity", "info")).lower()
            severity_color = SEVERITY_COLORS.get(severity, MUTED)
            status = str(finding.get("status", "open"))
            finding_type = str(finding.get("type", "finding"))
            finding_block = []
            if index == 0:
                finding_block.extend(
                    [
                        Spacer(1, 6 * mm),
                        Paragraph("Findings Included", styles["heading"]),
                        Spacer(1, 2 * mm),
                    ]
                )
            finding_block.extend(
                [
                    Paragraph(
                        f'<font color="{_color_hex(severity_color)}"><b>{_safe(severity.upper())}</b></font>'
                        f"  <b>{_safe(finding.get('title', 'Untitled finding'))}</b>",
                        styles["finding_title"],
                    ),
                    Paragraph(
                        f"{_safe(finding_type)} | {_safe(status)}",
                        styles["finding_meta"],
                    ),
                    Spacer(1, 1.5 * mm),
                    Paragraph(_safe(finding.get("summary", "No summary provided.")), styles["body"]),
                    Spacer(1, 3 * mm),
                    HRFlowable(width="100%", thickness=0.6, color=LINE),
                    Spacer(1, 3 * mm),
                ]
            )
            story.append(KeepTogether(finding_block))
    else:
        story.append(
            KeepTogether(
                [
                    Spacer(1, 6 * mm),
                    Paragraph("Findings Included", styles["heading"]),
                    Spacer(1, 2 * mm),
                    Paragraph("No active findings were included.", styles["body"]),
                ]
            )
        )

    technical_notes = content.get("technical_notes")
    if isinstance(technical_notes, list) and technical_notes:
        story.extend([Spacer(1, 5 * mm), Paragraph("Technical Notes", styles["heading"]), Spacer(1, 2 * mm)])
        for note in technical_notes:
            story.append(Paragraph(f"- {_safe(note)}", styles["body"]))

    story.extend(
        [
            Spacer(1, 7 * mm),
            Paragraph(
                "Privacy boundary: raw Nmap output, packet captures, packet payloads, and full scan logs are not included.",
                styles["privacy"],
            ),
        ]
    )

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle(
            "SecOpsEyebrow",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=SEA,
            spaceAfter=0,
        ),
        "title": ParagraphStyle(
            "SecOpsTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=27,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=0,
        ),
        "summary": ParagraphStyle(
            "SecOpsSummary",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#334155"),
        ),
        "heading": ParagraphStyle(
            "SecOpsHeading",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=INK,
            spaceBefore=0,
            spaceAfter=0,
        ),
        "body": ParagraphStyle(
            "SecOpsBody",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=9.5,
            leading=14,
            textColor=INK,
        ),
        "metric_label": ParagraphStyle(
            "SecOpsMetricLabel",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=9,
            textColor=MUTED,
        ),
        "metric_value": ParagraphStyle(
            "SecOpsMetricValue",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            textColor=INK,
        ),
        "finding_title": ParagraphStyle(
            "SecOpsFindingTitle",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=10,
            leading=14,
            textColor=INK,
        ),
        "finding_meta": ParagraphStyle(
            "SecOpsFindingMeta",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=9,
            textColor=MUTED,
        ),
        "privacy": ParagraphStyle(
            "SecOpsPrivacy",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=12,
            textColor=MUTED,
            borderColor=LINE,
            borderWidth=0.5,
            borderPadding=7,
            backColor=PAPER,
        ),
    }


def _meta_table(
    report: Report,
    site_name: str,
    content: dict[str, object],
    styles: dict[str, ParagraphStyle],
) -> Table:
    generated = report.created_at.strftime("%Y-%m-%d %H:%M UTC")
    period_start = report.period_start.strftime("%Y-%m-%d") if report.period_start else "Not recorded"
    period_end = report.period_end.strftime("%Y-%m-%d") if report.period_end else report.created_at.strftime("%Y-%m-%d")
    provider = str(content.get("provider", "unknown"))
    model = str(content.get("model", "n/a"))
    values = [
        ("Site", site_name),
        ("Reporting period", f"{period_start} to {period_end}"),
        ("Overall risk", report.risk_level.upper()),
        ("Generated", generated),
        ("Provider", provider),
        ("Model", model),
    ]
    cells = [
        [Paragraph(_safe(label), styles["metric_label"]), Paragraph(_safe(value), styles["metric_value"])]
        for label, value in values
    ]
    table = Table(cells, colWidths=[34 * mm, 134 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _metrics_table(metrics: dict[str, object], styles: dict[str, ParagraphStyle]) -> Table:
    items = [
        ("Assets", metrics.get("assets_total", 0)),
        ("New devices", metrics.get("new_devices", 0)),
        ("Risky services", metrics.get("risky_services", 0)),
        ("Wi-Fi risks", metrics.get("wifi_security_findings", 0)),
        ("Open findings", metrics.get("open_findings", 0)),
        ("Acknowledged", metrics.get("acknowledged_findings", 0)),
        ("Resolved", metrics.get("resolved_findings", 0)),
        ("Scans completed", metrics.get("scans_completed", 0)),
    ]
    rows = []
    for offset in range(0, len(items), 4):
        row = []
        for label, value in items[offset : offset + 4]:
            row.append(
                [
                    Paragraph(_safe(label), styles["metric_label"]),
                    Paragraph(_safe(value), styles["metric_value"]),
                ]
            )
        rows.append(row)
    table = Table(rows, colWidths=[42 * mm] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPER),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _severity_table(metrics: dict[str, object], styles: dict[str, ParagraphStyle]) -> Table:
    severity = metrics.get("severity") if isinstance(metrics.get("severity"), dict) else {}
    levels = ["critical", "high", "medium", "low", "info"]
    cells = []
    for level in levels:
        color = SEVERITY_COLORS[level]
        cells.append(
            [
                Paragraph(f'<font color="{_color_hex(color)}"><b>{level.upper()}</b></font>', styles["metric_label"]),
                Paragraph(_safe(severity.get(level, 0)), styles["metric_value"]),
            ]
        )
    table = Table([cells], colWidths=[33.6 * mm] * 5)
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(document.leftMargin, 12 * mm, A4[0] - document.rightMargin, 12 * mm)
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(document.leftMargin, 8 * mm, "SecOpsAI Edge | Confidential pilot report")
    canvas.drawRightString(A4[0] - document.rightMargin, 8 * mm, f"Page {document.page}")
    canvas.restoreState()


def _safe(value: object) -> str:
    text = str(value if value is not None else "")
    text = " ".join(text.replace("\x00", "").split())
    return escape(text)


def _color_hex(color: colors.Color) -> str:
    return color.hexval().replace("0x", "#")
