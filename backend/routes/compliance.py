from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, send_file
from flask_login import login_required, current_user
from backend.database.database import db
from backend.models.compliance import ComplianceRequirement, ComplianceDocument
from backend.utils.status import update_requirement_status, update_all_statuses
from backend.utils.export import generate_compliance_pdf, generate_compliance_csv, generate_requirement_detail_pdf
from datetime import datetime
from werkzeug.utils import secure_filename
import os

comp_bp = Blueprint('compliance', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'jpeg', 'png', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@comp_bp.route('/', methods=['GET'])
@login_required
def compliance():
    if not current_user.organization:
        return redirect(url_for('auth.login'))
    
    # Auto-update all statuses before displaying
    update_all_statuses(current_user.organization_id)
    
    requirements = ComplianceRequirement.query.filter_by(
        organization_id=current_user.organization_id
    ).order_by(ComplianceRequirement.expiration_date).all()
    
    return render_template('requirements.html', requirements=requirements)

@comp_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_requirement():
    if not current_user.organization:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        expiration_date = request.form.get('expiration_date')
        renewal_frequency = request.form.get('renewal_frequency')
        
        if not name or not expiration_date:
            flash('Name and expiration date are required', 'error')
            return render_template('add_requirement.html')
        
        requirement = ComplianceRequirement(
            name=name,
            description=description,
            expiration_date=datetime.strptime(expiration_date, '%Y-%m-%d').date(),
            renewal_frequency=renewal_frequency,
            organization_id=current_user.organization_id,
            status='missing'
        )
        
        # Set initial status
        update_requirement_status(requirement)
        
        db.session.add(requirement)
        db.session.commit()
        
        flash('Requirement added successfully!', 'success')
        return redirect(url_for('compliance.compliance'))
    
    return render_template('add_requirement.html')

@comp_bp.route('/<int:requirement_id>', methods=['GET'])
@login_required
def view_requirement(requirement_id):
    requirement = ComplianceRequirement.query.get_or_404(requirement_id)
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    # Update status before viewing
    update_requirement_status(requirement)
    db.session.commit()
    
    return render_template('requirement_detail.html', requirement=requirement)

@comp_bp.route('/<int:requirement_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_requirement(requirement_id):
    requirement = ComplianceRequirement.query.get_or_404(requirement_id)
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    if request.method == 'POST':
        requirement.name = request.form.get('name')
        requirement.description = request.form.get('description')
        requirement.expiration_date = datetime.strptime(request.form.get('expiration_date'), '%Y-%m-%d').date()
        requirement.renewal_frequency = request.form.get('renewal_frequency')
        requirement.updated_at = datetime.utcnow()
        
        # Update status based on new expiration date
        update_requirement_status(requirement)
        
        db.session.commit()
        
        flash('Requirement updated successfully!', 'success')
        return redirect(url_for('compliance.view_requirement', requirement_id=requirement.id))
    
    return render_template('edit_requirement.html', requirement=requirement)

@comp_bp.route('/<int:requirement_id>/delete', methods=['POST'])
@login_required
def delete_requirement(requirement_id):
    requirement = ComplianceRequirement.query.get_or_404(requirement_id)
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    # Delete associated files
    for doc in requirement.documents:
        try:
            os.remove(doc.file_path)
        except OSError:
            pass
    
    db.session.delete(requirement)
    db.session.commit()
    
    flash('Requirement deleted successfully', 'success')
    return redirect(url_for('compliance.compliance'))

@comp_bp.route('/<int:requirement_id>/upload', methods=['GET', 'POST'])
@login_required
def upload_document(requirement_id):
    requirement = ComplianceRequirement.query.get_or_404(requirement_id)
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        description = request.form.get('description', '')
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{requirement_id}_{timestamp}_{filename}"
            
            # Save file
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Get next version number
            latest_doc = ComplianceDocument.query.filter_by(
                requirement_id=requirement_id
            ).order_by(ComplianceDocument.version.desc()).first()
            
            next_version = (latest_doc.version + 1) if latest_doc else 1
            
            # Create document record
            document = ComplianceDocument(
                requirement_id=requirement_id,
                filename=filename,
                file_path=file_path,
                description=description,
                version=next_version
            )
            
            db.session.add(document)
            requirement.updated_at = datetime.utcnow()
            
            # Auto-update status after upload
            update_requirement_status(requirement)
            
            db.session.commit()
            
            flash('Document uploaded successfully!', 'success')
            return redirect(url_for('compliance.view_requirement', requirement_id=requirement_id))
        else:
            flash('Invalid file type. Allowed: PDF, DOC, DOCX, XLS, XLSX, JPG, PNG, TXT', 'error')
    
    return render_template('upload_document.html', requirement=requirement)

@comp_bp.route('/document/<int:document_id>/download')
@login_required
def download_document(document_id):
    document = ComplianceDocument.query.get_or_404(document_id)
    requirement = document.requirement
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    return send_from_directory(
        current_app.config['UPLOAD_FOLDER'],
        os.path.basename(document.file_path),
        as_attachment=True,
        download_name=document.filename
    )

@comp_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    document = ComplianceDocument.query.get_or_404(document_id)
    requirement = document.requirement
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    # Delete file from filesystem
    try:
        os.remove(document.file_path)
    except OSError:
        pass
    
    requirement_id = document.requirement_id
    db.session.delete(document)
    
    # Auto-update status after deletion
    update_requirement_status(requirement)
    
    db.session.commit()
    
    flash('Document deleted successfully', 'success')
    return redirect(url_for('compliance.view_requirement', requirement_id=requirement_id))

@comp_bp.route('/export/pdf', methods=['GET'])
@login_required
def export_all_pdf():
    """Export all requirements as PDF"""
    if not current_user.organization:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    # Update statuses before export
    update_all_statuses(current_user.organization_id)
    
    requirements = ComplianceRequirement.query.filter_by(
        organization_id=current_user.organization_id
    ).order_by(ComplianceRequirement.expiration_date).all()
    
    pdf_buffer = generate_compliance_pdf(current_user.organization, requirements)
    
    filename = f"{current_user.organization.name}_compliance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@comp_bp.route('/export/csv', methods=['GET'])
@login_required
def export_all_csv():
    """Export all requirements as CSV"""
    if not current_user.organization:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    # Update statuses before export
    update_all_statuses(current_user.organization_id)
    
    requirements = ComplianceRequirement.query.filter_by(
        organization_id=current_user.organization_id
    ).order_by(ComplianceRequirement.expiration_date).all()
    
    csv_buffer = generate_compliance_csv(current_user.organization, requirements)
    
    filename = f"{current_user.organization.name}_compliance_report_{datetime.now().strftime('%Y%m%d')}.csv"
    
    # Convert StringIO to BytesIO for send_file
    import io
    bytes_buffer = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
    bytes_buffer.seek(0)
    
    return send_file(
        bytes_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='text/csv'
    )

@comp_bp.route('/<int:requirement_id>/export/pdf', methods=['GET'])
@login_required
def export_requirement_pdf(requirement_id):
    """Export single requirement detail as PDF"""
    requirement = ComplianceRequirement.query.get_or_404(requirement_id)
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    # Update status before export
    update_requirement_status(requirement)
    db.session.commit()
    
    pdf_buffer = generate_requirement_detail_pdf(requirement)
    
    filename = f"{requirement.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )