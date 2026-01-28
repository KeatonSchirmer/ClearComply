from backend.database.database import db
from datetime import datetime

class ComplianceRequirement(db.Model):
    __tablename__ = 'compliance_requirement'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    expiration_date = db.Column(db.Date, nullable=False)
    renewal_frequency = db.Column(db.String(50))
    status = db.Column(db.String(20), default='missing')
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = db.relationship('Organization', backref='requirements')
    documents = db.relationship('ComplianceDocument', back_populates='requirement', cascade='all, delete-orphan')

class ComplianceDocument(db.Model):
    __tablename__ = 'compliance_document'
    
    id = db.Column(db.Integer, primary_key=True)
    requirement_id = db.Column(db.Integer, db.ForeignKey('compliance_requirement.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    version = db.Column(db.Integer, default=1)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    requirement = db.relationship('ComplianceRequirement', back_populates='documents')