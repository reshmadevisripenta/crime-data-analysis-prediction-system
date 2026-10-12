import os
import logging
from datetime import datetime
import pandas as pd
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from crime_data.models import CrimeRecord

logger = logging.getLogger(__name__)


def get_report_data(report):
    """
    Queries CrimeRecord database based on filters configured in report instance.
    Returns dictionary with queryset, metrics, and aggregated summaries.
    """
    qs = CrimeRecord.objects.select_related('category', 'location').all()

    if report.location:
        qs = qs.filter(location=report.location)

    if report.category:
        qs = qs.filter(category=report.category)

    if report.date_from:
        qs = qs.filter(incident_date__gte=report.date_from)

    if report.date_to:
        qs = qs.filter(incident_date__lte=report.date_to)

    total_crimes = qs.count()
    critical_count = qs.filter(severity='critical').count()
    solved_count = qs.filter(status__in=['solved', 'closed']).count()

    return {
        'queryset': qs,
        'total_crimes': total_crimes,
        'critical_count': critical_count,
        'solved_count': solved_count,
        'report_name': report.name,
        'report_type': report.get_report_type_display(),
        'date_from': str(report.date_from) if report.date_from else 'All Time',
        'date_to': str(report.date_to) if report.date_to else 'Present',
    }


def generate_pdf_report(report, data):
    """
    Builds a professional PDF document using ReportLab.
    Saves PDF file to media/reports/ and returns the relative path.
    """
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"report_{report.id}_{int(datetime.now().timestamp())}.pdf"
    file_path = os.path.join(reports_dir, filename)

    doc = SimpleDocTemplate(file_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Custom styles adhering to project design system (#071B3A, #1769FF, #1C2940)
    primary_color = colors.HexColor('#071B3A')
    blue_accent = colors.HexColor('#1769FF')
    card_bg = colors.HexColor('#F4F7FC')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=10
    )

    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4A5568'),
        spaceAfter=15
    )

    heading2 = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=blue_accent,
        spaceBefore=15,
        spaceAfter=10
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1C2940')
    )

    # 1. Document Title
    elements.append(Paragraph(f"Crime Analysis Report: {report.name}", title_style))
    elements.append(Paragraph(
        f"<b>Type:</b> {data['report_type']} &nbsp;|&nbsp; "
        f"<b>Scope:</b> {data['date_from']} to {data['date_to']} &nbsp;|&nbsp; "
        f"<b>Generated on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        meta_style
    ))
    elements.append(Spacer(1, 10))

    # 2. Executive Summary Metrics Table
    summary_data = [
        ['Total Incidents', 'Critical Incidents', 'Solved / Closed Rate'],
        [
            str(data['total_crimes']),
            str(data['critical_count']),
            f"{round((data['solved_count'] / data['total_crimes'] * 100), 1) if data['total_crimes'] else 0}%"
        ]
    ]
    summary_table = Table(summary_data, colWidths=[180, 180, 180])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, 1), card_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 15))

    # 3. Incident Breakdown Table (Up to 50 records)
    elements.append(Paragraph("Incident Records Sample", heading2))

    table_rows = [
        ['ID', 'Category', 'Location', 'Date', 'Severity', 'Status']
    ]

    sample_qs = data['queryset'][:50]
    for r in sample_qs:
        table_rows.append([
            str(r.id),
            r.category.name[:20],
            r.location.name[:20],
            str(r.incident_date),
            r.severity.capitalize(),
            r.get_status_display()
        ])

    if len(table_rows) == 1:
        table_rows.append(['-', 'No records match filter parameters', '-', '-', '-', '-'])

    records_table = Table(table_rows, colWidths=[40, 110, 130, 80, 80, 100])
    records_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#102B52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, card_bg]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(records_table)

    # Build PDF
    doc.build(elements)
    logger.info(f"Generated PDF report at {file_path}")
    return os.path.join('reports', filename)


def generate_csv_report(report, data):
    """
    Generates tabular CSV report file using pandas.
    Saves CSV to media/reports/ and returns the relative path.
    """
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
    os.makedirs(reports_dir, exist_ok=True)

    filename = f"report_{report.id}_{int(datetime.now().timestamp())}.csv"
    file_path = os.path.join(reports_dir, filename)

    rows = []
    for r in data['queryset']:
        rows.append({
            'Record_ID': r.id,
            'Category': r.category.name,
            'Location': r.location.name,
            'City': r.location.city,
            'State': r.location.state,
            'Latitude': r.location.latitude,
            'Longitude': r.location.longitude,
            'Incident_Date': r.incident_date,
            'Incident_Time': r.incident_time,
            'Severity': r.severity,
            'Status': r.status,
            'Description': r.description,
            'Source': r.source,
        })

    df = pd.DataFrame(rows)
    df.to_csv(file_path, index=False)
    logger.info(f"Generated CSV report at {file_path}")
    return os.path.join('reports', filename)
