"""
report_generator.py
Generates a detailed review report PDF with scores, suggestions, and changes made.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime


def build_review_report(analysis: dict, candidate_name: str = "Candidate") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=1.5*cm, bottomMargin=1.5*cm)

    PRIMARY = colors.HexColor("#1B2A4A")
    ACCENT  = colors.HexColor("#2E86AB")
    GREEN   = colors.HexColor("#27AE60")
    RED     = colors.HexColor("#E74C3C")
    AMBER   = colors.HexColor("#F39C12")
    LIGHT   = colors.HexColor("#EBF5FB")

    def sty(name, **kw):
        return ParagraphStyle(name, **kw)

    h1 = sty("h1", fontName="Helvetica-Bold", fontSize=20, textColor=PRIMARY,
              spaceAfter=4, alignment=TA_CENTER)
    h2 = sty("h2", fontName="Helvetica-Bold", fontSize=13, textColor=PRIMARY,
              spaceBefore=12, spaceAfter=6)
    sub = sty("sub", fontName="Helvetica-Oblique", fontSize=10,
              textColor=colors.HexColor("#555555"), spaceAfter=8, alignment=TA_CENTER)
    body = sty("body", fontName="Helvetica", fontSize=10,
               textColor=colors.HexColor("#333333"), spaceAfter=4, leading=14)
    bullet = sty("bullet", fontName="Helvetica", fontSize=10,
                  textColor=colors.HexColor("#333333"), leftIndent=14,
                  spaceAfter=3, leading=13)
    bold_label = sty("bold_label", fontName="Helvetica-Bold", fontSize=10,
                      textColor=PRIMARY, spaceAfter=2)

    story = []

    # Title
    story.append(Paragraph("📋 RESUME REVIEW REPORT", h1))
    story.append(Paragraph(
        f"Candidate: {candidate_name}  •  Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}",
        sub
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceAfter=10))

    # Overall Score Banner
    score = analysis.get("overall_score", 0)
    benchmark = analysis.get("benchmark", 70)
    passed = analysis.get("passed", False)
    score_color = GREEN if passed else (AMBER if score >= benchmark * 0.8 else RED)
    verdict_text = "✅ PASSED BENCHMARK" if passed else "❌ BELOW BENCHMARK"

    score_table = Table([
        [
            Paragraph(f"<b>{score}/100</b>", sty("sc", fontName="Helvetica-Bold",
                       fontSize=36, textColor=score_color, alignment=TA_CENTER)),
            Paragraph(
                f"<b>{verdict_text}</b><br/><br/>"
                f"Benchmark: {benchmark}/100<br/>"
                f"ATS Verdict: {analysis.get('ats_verdict', 'N/A')}",
                sty("sv", fontName="Helvetica-Bold", fontSize=12,
                     textColor=score_color, leading=18)
            )
        ]
    ], colWidths=[5*cm, 12*cm])
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 8))

    # Summary
    if analysis.get("summary"):
        story.append(Paragraph("OVERVIEW", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=4))
        story.append(Paragraph(analysis["summary"], body))

    # Section Scores
    section_scores = analysis.get("section_scores", {})
    if section_scores:
        story.append(Paragraph("SECTION-WISE SCORES", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=4))

        score_rows = [["Category", "Score", "Status"]]
        labels = {
            "skills_match": "Skills Match",
            "experience_relevance": "Experience Relevance",
            "education_fit": "Education Fit",
            "keywords_ats": "ATS Keywords",
            "formatting_clarity": "Formatting & Clarity"
        }
        for key, label in labels.items():
            val = section_scores.get(key, 0)
            status = "✅ Good" if val >= 70 else ("⚠️ Average" if val >= 50 else "❌ Needs Work")
            score_rows.append([label, f"{val}/100", status])

        tbl = Table(score_rows, colWidths=[8*cm, 3*cm, 5*cm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(tbl)

    # Strengths
    strengths = analysis.get("strengths", [])
    if strengths:
        story.append(Paragraph("✅ STRENGTHS", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=4))
        for s in strengths:
            story.append(Paragraph(f"▸  {s}", bullet))

    # Weaknesses
    weaknesses = analysis.get("weaknesses", [])
    if weaknesses:
        story.append(Paragraph("⚠️ AREAS FOR IMPROVEMENT", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=AMBER, spaceAfter=4))
        for w in weaknesses:
            story.append(Paragraph(f"▸  {w}", bullet))

    # Missing Keywords
    missing = analysis.get("missing_keywords", [])
    if missing:
        story.append(Paragraph("🔍 MISSING ATS KEYWORDS", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=RED, spaceAfter=4))
        story.append(Paragraph(
            "Add these keywords to improve ATS pass rate:", body
        ))
        story.append(Paragraph(
            "  •  ".join(missing),
            sty("kw", fontName="Helvetica-Bold", fontSize=9.5,
                 textColor=RED, spaceAfter=4)
        ))

    # Suggestions
    suggestions = analysis.get("suggestions", [])
    if suggestions:
        story.append(Paragraph("💡 ACTIONABLE SUGGESTIONS", h2))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=4))
        for i, sug in enumerate(suggestions, 1):
            section = sug.get("section", "General")
            issue = sug.get("issue", "")
            fix = sug.get("fix", "")

            sug_table = Table([
                [Paragraph(f"#{i}  [{section}]", sty("sn", fontName="Helvetica-Bold",
                            fontSize=10, textColor=PRIMARY))],
                [Paragraph(f"<b>Issue:</b> {issue}", body)],
                [Paragraph(f"<b>Fix:</b> {fix}", sty("fix", fontName="Helvetica",
                            fontSize=10, textColor=GREEN, spaceAfter=0, leading=14))]
            ], colWidths=[16*cm])
            sug_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#DDDDDD")),
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
            ]))
            story.append(sug_table)
            story.append(Spacer(1, 6))

    # Footer
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY))
    story.append(Paragraph(
        "Generated by Resume Reviewer Bot • Powered by Claude AI",
        sty("ft", fontName="Helvetica-Oblique", fontSize=8,
             textColor=colors.HexColor("#AAAAAA"), alignment=TA_CENTER, spaceBefore=6)
    ))

    doc.build(story)
    return buf.getvalue()
