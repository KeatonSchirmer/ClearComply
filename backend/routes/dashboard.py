from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from backend.utils.status import get_status_counts, get_expiring_soon_requirements

dash_bp = Blueprint('dashboard', __name__)

@dash_bp.route('/', methods=['GET'])
@login_required
def dashboard():
    if not current_user.organization:
        return redirect(url_for('auth.login'))
    
    org_id = current_user.organization_id
    
    # Get status counts (auto-updates statuses)
    status_data = get_status_counts(org_id)
    
    # Get expiring soon requirements
    expiring_soon = get_expiring_soon_requirements(org_id, days=30)
    
    return render_template(
        'dashboard.html',
        organization_name=current_user.organization.name,
        compliance_percentage=status_data['compliance_percentage'],
        compliant_count=status_data['compliant'],
        expiring_soon_count=status_data['expiring_soon'],
        expiring_soon=expiring_soon,
        missing_count=status_data['missing'] + status_data['expired'],
        total_requirements=status_data['total']
    )