from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category_type = db.Column(db.String(20), default='expense')  # 'income' or 'expense'
    
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    transactions = db.relationship('Transaction', backref='category', cascade='all, delete-orphan')
    budgets = db.relationship('Budget', backref='category', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'category_type': self.category_type,
            'subcategories': [sub.to_dict() for sub in self.subcategories]
        }

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'date': self.date.isoformat(),
            'transaction_type': self.transaction_type,
            'category_id': self.category_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

class Budget(db.Model):
    __tablename__ = 'budgets'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('category_id', 'month', 'year', name='unique_category_month_year'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'amount': self.amount,
            'month': self.month,
            'year': self.year,
            'created_at': self.created_at.isoformat()
        }