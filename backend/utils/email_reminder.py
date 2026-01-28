from flask_mail import Message, Mail
from flask import render_template_string
from backend.models.compliance import ComplianceRequirement
from backend.models.reminders import ReminderLog
from backend.models.auth import User
from backend.database.database import db
from datetime import datetime, timedelta

def send_reminder_email(mail: Mail, requirement: ComplianceRequirement, user_email: str, reminder_type: str):
    """
    Send reminder email for a compliance requirement
    """
    days_until = (requirement.expiration_date - datetime.now().date()).days
    
    # Email subject based on urgency
    if reminder_type == 'day_of':
        subject = f"🚨 URGENT: {requirement.name} expires TODAY"
    elif reminder_type == '7_day':
        subject = f"⚠️ {requirement.name} expires in 7 days"
    else:  # 30_day
        subject = f"📅 {requirement.name} expires in 30 days"
    
    # Email body
    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #d9534f;">Compliance Reminder</h2>
            
            <p>Hello,</p>
            
            <p>This is a reminder that the following compliance requirement is expiring soon:</p>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #d9534f; margin: 20px 0;">
                <h3 style="margin-top: 0;">{requirement.name}</h3>
                <p><strong>Expiration Date:</strong> {requirement.expiration_date.strftime('%B %d, %Y')}</p>
                <p><strong>Days Until Expiration:</strong> {days_until} day(s)</p>
                <p><strong>Status:</strong> {requirement.status.replace('_', ' ').title()}</p>
                {f'<p><strong>Description:</strong> {requirement.description}</p>' if requirement.description else ''}
            </div>
            
            <p><strong>Action Required:</strong></p>
            <ul>
                <li>Review the requirement details</li>
                <li>Upload updated compliance documents</li>
                <li>Update the expiration date if renewed</li>
            </ul>
            
            <p>
                <a href="http://localhost:5000/compliance/{requirement.id}" 
                   style="background-color: #007bff; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Requirement
                </a>
            </p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <p style="font-size: 12px; color: #666;">
                This is an automated reminder from ClearComply. 
                <br>To manage your notification settings, log in to your account.
            </p>
        </body>
    </html>
    """
    
    try:
        msg = Message(
            subject=subject,
            recipients=[user_email],
            html=body
        )
        mail.send(msg)
        
        # Log the reminder
        reminder_log = ReminderLog(
            requirement_id=requirement.id,
            reminder_type=reminder_type,
            email_to=user_email
        )
        db.session.add(reminder_log)
        db.session.commit()
        
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False

def check_and_send_reminders(app, mail: Mail):
    """
    Check all requirements and send reminders where needed
    """
    with app.app_context():
        today = datetime.now().date()
        
        # Get all requirements
        requirements = ComplianceRequirement.query.all()
        
        reminders_sent = 0
        
        for req in requirements:
            days_until_expiry = (req.expiration_date - today).days
            
            # Get organization owner email
            owner = User.query.filter_by(
                organization_id=req.organization_id
            ).first()
            
            if not owner:
                continue
            
            # Check if reminder already sent for this period
            existing_log = None
            reminder_type = None
            
            # Day of expiration
            if days_until_expiry == 0:
                reminder_type = 'day_of'
                existing_log = ReminderLog.query.filter_by(
                    requirement_id=req.id,
                    reminder_type='day_of'
                ).filter(
                    ReminderLog.sent_at >= datetime.now() - timedelta(hours=12)
                ).first()
            
            # 7 days before
            elif days_until_expiry == 7:
                reminder_type = '7_day'
                existing_log = ReminderLog.query.filter_by(
                    requirement_id=req.id,
                    reminder_type='7_day'
                ).filter(
                    ReminderLog.sent_at >= datetime.now() - timedelta(days=1)
                ).first()
            
            # 30 days before
            elif days_until_expiry == 30:
                reminder_type = '30_day'
                existing_log = ReminderLog.query.filter_by(
                    requirement_id=req.id,
                    reminder_type='30_day'
                ).filter(
                    ReminderLog.sent_at >= datetime.now() - timedelta(days=1)
                ).first()
            
            # Send reminder if needed and not already sent
            if reminder_type and not existing_log:
                if send_reminder_email(mail, req, owner.email, reminder_type):
                    reminders_sent += 1
                    print(f"Sent {reminder_type} reminder for: {req.name}")
        
        print(f"Total reminders sent: {reminders_sent}")
        return reminders_sent