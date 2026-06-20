from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

db = SQLAlchemy()

class Admin(UserMixin, db.Model):
    """Admin user model"""
    __tablename__ = 'admins'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    repairs = db.relationship('Repair', backref='admin', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

class Customer(db.Model):
    """Customer model"""
    __tablename__ = 'customers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    repairs = db.relationship('Repair', backref='customer', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Repair(db.Model):
    """Repair tracking model"""
    __tablename__ = 'repairs'
    
    # Status options: received, in_progress, completed, ready_pickup, picked_up
    STATUS_CHOICES = {
        'received': 'Diterima',
        'in_progress': 'Dalam Proses',
        'completed': 'Selesai',
        'ready_pickup': 'Siap Diambil',
        'picked_up': 'Diambil'
    }
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tracking_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.String(36), db.ForeignKey('customers.id'), nullable=False)
    admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True)
    
    shoe_type = db.Column(db.String(100), nullable=False)  # e.g., "Nike Air Jordan 1"
    shoe_color = db.Column(db.String(50), nullable=False)
    problem_description = db.Column(db.Text, nullable=False)
    repair_notes = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(20), default='received', nullable=False)
    cost = db.Column(db.Float, nullable=True)
    
    date_in = db.Column(db.DateTime, default=datetime.utcnow)
    date_completed = db.Column(db.DateTime, nullable=True)
    date_pickup = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    status_history = db.relationship('StatusHistory', backref='repair', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Repair {self.tracking_number}>'
    
    def get_status_display(self):
        return self.STATUS_CHOICES.get(self.status, self.status)
    
    def get_days_in_repair(self):
        """Hitung berapa hari sepatu di workshop"""
        end_date = self.date_pickup or datetime.utcnow()
        delta = end_date - self.date_in
        return delta.days

class StatusHistory(db.Model):
    """Track status changes"""
    __tablename__ = 'status_history'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repair_id = db.Column(db.String(36), db.ForeignKey('repairs.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StatusHistory {self.repair_id} - {self.status}>'
