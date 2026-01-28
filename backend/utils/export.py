from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import pandas as pd
import io
import os

def generate_compliance_pdf(organization, requirements):
    """
    Generate a PDF report of all compliance requirements
    """
    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=12
    )
    
    # Title
    title = Paragraph(f"Compliance Report<br/>{organization.name}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Report info
    report_date = Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal'])
    elements.append(report_date)
    elements.append(Spacer(1, 0.5*inch))
    
    # Summary section
    summary_heading = Paragraph("Compliance Summary", heading_style)
    elements.append(summary_heading)
    
    # Calculate summary stats
    total = len(requirements)
    compliant = sum(1 for r in requirements if r.status == 'compliant')
    expiring = sum(1 for r in requirements if r.status == 'expiring_soon')
    expired = sum(1 for r in requirements if r.status == 'expired')
    missing = sum(1 for r in requirements if r.status == 'missing')
    
    compliance_pct = round((compliant / total * 100), 1) if total > 0 else 0
    
    summary_data = [
        ['Metric', 'Count'],
        ['Total Requirements', str(total)],
        ['Compliant', str(compliant)],
        ['Expiring Soon', str(expiring)],
        ['Expired', str(expired)],
        ['Missing', str(missing)],
        ['Compliance Rate', f'{compliance_pct}%']
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Requirements detail section
    detail_heading = Paragraph("Requirements Detail", heading_style)
    elements.append(detail_heading)
    elements.append(Spacer(1, 0.2*inch))
    
    # Requirements table
    req_data = [['Requirement', 'Status', 'Expiration', 'Documents']]
    
    for req in requirements:
        status_emoji = {
            'compliant': '✓ Compliant',
            'expiring_soon': '⚠ Expiring Soon',
            'expired': '✗ Expired',
            'missing': '○ Missing'
        }.get(req.status, req.status)
        
        doc_count = len(req.documents)
        doc_text = f"{doc_count} file(s)" if doc_count > 0 else "None"
        
        req_data.append([
            req.name[:40],
            status_emoji,
            req.expiration_date.strftime('%m/%d/%Y'),
            doc_text
        ])
    
    req_table = Table(req_data, colWidths=[2.5*inch, 1.5*inch, 1.2*inch, 1*inch])
    req_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    
    elements.append(req_table)
    
    # Build PDF
    pdf_doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_compliance_csv(organization, requirements):
    """
    Generate a CSV export of all compliance requirements
    """
    data = []
    
    for req in requirements:
        # Get latest document info
        latest_doc = req.documents[-1] if req.documents else None
        
        data.append({
            'Organization': organization.name,
            'Requirement Name': req.name,
            'Description': req.description or '',
            'Status': req.status.replace('_', ' ').title(),
            'Expiration Date': req.expiration_date.strftime('%Y-%m-%d'),
            'Renewal Frequency': req.renewal_frequency or '',
            'Documents Count': len(req.documents),
            'Latest Document': latest_doc.filename if latest_doc else 'None',
            'Latest Upload Date': latest_doc.uploaded_at.strftime('%Y-%m-%d') if latest_doc else '',
            'Created Date': req.created_at.strftime('%Y-%m-%d'),
            'Last Updated': req.updated_at.strftime('%Y-%m-%d')
        })
    
    df = pd.DataFrame(data)
    
    # Create CSV in memory
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    
    return buffer

def generate_requirement_detail_pdf(requirement):
    """
    Generate a detailed PDF for a single requirement
    """
    buffer = io.BytesIO()
    pdf_doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20
    )
    
    # Title
    title = Paragraph(f"Compliance Requirement Detail", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Requirement info
    info_data = [
        ['Field', 'Value'],
        ['Requirement Name', requirement.name],
        ['Status', requirement.status.replace('_', ' ').title()],
        ['Expiration Date', requirement.expiration_date.strftime('%B %d, %Y')],
        ['Renewal Frequency', requirement.renewal_frequency or 'Not specified'],
        ['Description', requirement.description or 'No description'],
        ['Created', requirement.created_at.strftime('%B %d, %Y')],
        ['Last Updated', requirement.updated_at.strftime('%B %d, %Y')]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Documents section
    if requirement.documents:
        doc_heading = Paragraph("Attached Documents", styles['Heading2'])
        elements.append(doc_heading)
        elements.append(Spacer(1, 0.1*inch))
        
        doc_data = [['Filename', 'Version', 'Uploaded', 'Description']]
        
        for document in requirement.documents:
            doc_data.append([
                document.filename[:30],
                f"v{document.version}",
                document.uploaded_at.strftime('%m/%d/%Y'),
                (document.description or 'N/A')[:30]
            ])
        
        doc_table = Table(doc_data, colWidths=[2*inch, 0.8*inch, 1.2*inch, 2*inch])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('FONTSIZE', (0, 0), (-1, -1), 9)
        ]))
        
        elements.append(doc_table)
    else:
        elements.append(Paragraph("No documents attached", styles['Normal']))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer = Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles['Normal']
    )
    elements.append(footer)
    
    # Build PDF
    pdf_doc.build(elements)
    buffer.seek(0)
    return buffer
