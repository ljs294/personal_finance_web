from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from models import db, Category, Transaction
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# Category routes
@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.filter_by(parent_id=None).all()
    return jsonify([cat.to_dict() for cat in categories])

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.json
    category = Category(
        name=data['name'],
        parent_id=data.get('parent_id')
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    category = Category.query.get_or_404(id)
    data = request.json
    category.name = data['name']
    db.session.commit()
    return jsonify(category.to_dict())

@app.route('/api/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    return '', 204

# Transaction routes
@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    return jsonify([t.to_dict() for t in transactions])

@app.route('/api/transactions', methods=['POST'])
def create_transaction():
    data = request.json
    transaction = Transaction(
        description=data['description'],
        amount=data['amount'],
        date=datetime.fromisoformat(data['date']),
        transaction_type=data['transaction_type'],
        category_id=data.get('category_id'),
        notes=data.get('notes')
    )
    db.session.add(transaction)
    db.session.commit()
    return jsonify(transaction.to_dict()), 201

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    return '', 204

@app.route('/api/category-spending', methods=['GET'])
def get_category_spending():
    categories = Category.query.filter_by(parent_id=None).all()
    spending = []
    
    for cat in categories:
        total = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.category_id == cat.id,
            Transaction.transaction_type == 'expense'
        ).scalar() or 0
        
        spending.append({
            'category_id': cat.id,
            'category_name': cat.name,
            'amount': total,
            'subcategory_count': len(cat.subcategories)
        })
    
    return jsonify(spending)

if __name__ == '__main__':
    app.run(debug=True)