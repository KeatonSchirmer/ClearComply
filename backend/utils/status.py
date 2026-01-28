from backend.models.compliance import ComplianceRequirement
from backend.database.database import db
from datetime import datetime, timedelta

def update_requirement_status(requirement):
    """
    Update a single requirement's status based on:
    - Document presence
    - Expiration date
    """
    today = datetime.now().date()
    thirty_days_from_now = today + timedelta(days=30)
    
    # If expired
    if requirement.expiration_date < today:
        if requirement.documents:
            # Has documents but expired - needs renewal
            requirement.status = 'expired'
        else:
            # No documents and expired
            requirement.status = 'expired'
    
    # If expiring soon (within 30 days)
    elif requirement.expiration_date <= thirty_days_from_now:
        if requirement.documents:
            # Has documents but expiring soon
            requirement.status = 'expiring_soon'
        else:
            # No documents and expiring soon
            requirement.status = 'expiring_soon'
    
    # Future expiration
    else:
        if requirement.documents:
            # Has documents and not expiring soon
            requirement.status = 'compliant'
        else:
            # No documents yet
            requirement.status = 'missing'
    
    return requirement

def update_all_statuses(organization_id=None):
    """
    Update statuses for all requirements, optionally filtered by organization
    """
    if organization_id:
        requirements = ComplianceRequirement.query.filter_by(
            organization_id=organization_id
        ).all()
    else:
        requirements = ComplianceRequirement.query.all()
    
    for req in requirements:
        update_requirement_status(req)
    
    db.session.commit()
    
    return len(requirements)

def get_status_counts(organization_id):
    """
    Get count of requirements by status for an organization
    """
    update_all_statuses(organization_id)
    
    requirements = ComplianceRequirement.query.filter_by(
        organization_id=organization_id
    ).all()
    
    counts = {
        'total': len(requirements),
        'compliant': 0,
        'expiring_soon': 0,
        'expired': 0,
        'missing': 0
    }
    
    for req in requirements:
        if req.status in counts:
            counts[req.status] += 1
    
    # Calculate compliance percentage
    if counts['total'] > 0:
        counts['compliance_percentage'] = round(
            (counts['compliant'] / counts['total']) * 100, 1
        )
    else:
        counts['compliance_percentage'] = 0
    
    return counts

def get_expiring_soon_requirements(organization_id, days=30):
    """
    Get requirements expiring within specified days
    """
    update_all_statuses(organization_id)
    
    cutoff_date = datetime.now().date() + timedelta(days=days)
    
    return ComplianceRequirement.query.filter(
        ComplianceRequirement.organization_id == organization_id,
        ComplianceRequirement.expiration_date <= cutoff_date,
        ComplianceRequirement.expiration_date >= datetime.now().date()
    ).order_by(ComplianceRequirement.expiration_date).all()