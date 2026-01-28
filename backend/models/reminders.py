from backend.database.database import db
from datetime import datetime

class ReminderLog(db.Model):
    __tablename__ = 'reminder_log'
    
    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('compliance_requirement.id'), nullable=False)
    reminder_type = db.Column(db.String(20), nullable=False)  # '30_day', '7_day', 'day_of'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    email_to = db.Column(db.String(120), nullable=False)
    
    # Relationships
    requirement = db.relationship('ComplianceRequirement', backref='reminder_logs')