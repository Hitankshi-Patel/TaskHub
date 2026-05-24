import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    # Store ID as String/UUID to support Firebase / OAuth UID formats
    id = db.Column(db.String(128), primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    full_name = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(50), default='user', nullable=False) # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tasks_created = db.relationship('Task', backref='creator', lazy=True, foreign_keys='Task.created_by')
    tasks_assigned = db.relationship('Task', backref='assignee', lazy=True, foreign_keys='Task.assigned_to')

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    product_image_url = db.Column(db.Text, nullable=False)
    
    # Task Status Flow: pending → assigned → in_progress → submitted → accepted → revision_requested
    status = db.Column(db.String(50), default='pending', nullable=False)
    
    assigned_to = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    generations = db.relationship('GeneratedImage', backref='task', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "product_image_url": self.product_image_url,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

class GeneratedImage(db.Model):
    __tablename__ = 'generated_images'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = db.Column(db.String(36), db.ForeignKey('tasks.id', ondelete='CASCADE'), nullable=False)
    
    # image_type: 'white_background', 'theme_1', 'theme_2', 'creative_1', 'creative_2', 'model_front', 'model_side', 'model_close'
    image_type = db.Column(db.String(50), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    prompt_used = db.Column(db.Text, nullable=True)
    
    # store metadata as JSON (JSONB on PostgreSQL, falling back to standard JSON/Text elsewhere)
    meta_data = db.Column(db.JSON, nullable=True)
    angle = db.Column(db.String(50), nullable=True) # 'front', 'side', 'close-up'
    is_final = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "image_type": self.image_type,
            "image_url": self.image_url,
            "prompt_used": self.prompt_used,
            "metadata": self.meta_data,
            "angle": self.angle,
            "is_final": self.is_final,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(128), db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(255), nullable=False) # e.g. 'task_created', 'task_assigned', etc.
    table_name = db.Column(db.String(100), nullable=False)
    record_id = db.Column(db.String(36), nullable=False)
    
    old_values = db.Column(db.JSON, nullable=True)
    new_values = db.Column(db.JSON, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "table_name": self.table_name,
            "record_id": self.record_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
