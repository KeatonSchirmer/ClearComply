from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required, current_user
from backend.utils.email_reminder import send_reminder_email
from backend.models.compliance import ComplianceRequirement
from flask import current_app

remind_bp = Blueprint('reminder', __name__)

@remind_bp.route('/test/<int:requirement_id>')
@login_required
def test_reminder(requirement_id):
    """
    Manually send a test reminder for a requirement
    """
    requirement = ComplianceRequirement.query.get_or_404(requirement_id)
    
    if requirement.organization_id != current_user.organization_id:
        flash('Access denied', 'error')
        return redirect(url_for('compliance.compliance'))
    
    from backend.database.database import db
    mail = current_app.extensions['mail']
    
    success = send_reminder_email(mail, requirement, current_user.email, '7_day')
    
    if success:
        flash('Test reminder sent to your email!', 'success')
    else:
        flash('Failed to send reminder', 'error')
    
    return redirect(url_for('compliance.view_requirement', requirement_id=requirement_id))