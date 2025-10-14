from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from models import db, Category, Transaction, Budget
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
    category_type = request.args.get('type', 'expense')
    categories = Category.query.filter_by(parent_id=None, category_type=category_type).all()
    return jsonify([cat.to_dict() for cat in categories])

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.json
    category = Category(
        name=data['name'],
        parent_id=data.get('parent_id'),
        category_type=data.get('category_type', 'expense')
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
    categories = Category.query.filter_by(parent_id=None, category_type='expense').all()
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

# Budget routes
@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    if not month or not year:
        now = datetime.now()
        month = now.month
        year = now.year
    
    budgets = Budget.query.filter_by(month=month, year=year).all()
    return jsonify([b.to_dict() for b in budgets])

@app.route('/api/budgets', methods=['POST'])
def create_or_update_budget():
    data = request.json
    
    existing_budget = Budget.query.filter_by(
        category_id=data['category_id'],
        month=data['month'],
        year=data['year']
    ).first()
    
    if existing_budget:
        existing_budget.amount = data['amount']
        db.session.commit()
        return jsonify(existing_budget.to_dict())
    else:
        budget = Budget(
            category_id=data['category_id'],
            amount=data['amount'],
            month=data['month'],
            year=data['year']
        )
        db.session.add(budget)
        db.session.commit()
        return jsonify(budget.to_dict()), 201

@app.route('/api/budgets/<int:id>', methods=['DELETE'])
def delete_budget(id):
    budget = Budget.query.get_or_404(id)
    db.session.delete(budget)
    db.session.commit()
    return '', 204

@app.route('/api/budget-overview', methods=['GET'])
def get_budget_overview():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    category_type = request.args.get('type', 'expense')

    if not month or not year:
        now = datetime.now()
        month = now.month
        year = now.year

    from sqlalchemy import extract

    categories = Category.query.filter_by(parent_id=None, category_type=category_type).all()
    overview = []

    for cat in categories:
        budget = Budget.query.filter_by(
            category_id=cat.id,
            month=month,
            year=year
        ).first()

        if category_type == 'income':
            actual = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.category_id == cat.id,
                Transaction.transaction_type == 'income',
                extract('month', Transaction.date) == month,
                extract('year', Transaction.date) == year
            ).scalar() or 0
        else:
            actual = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.category_id == cat.id,
                Transaction.transaction_type == 'expense',
                extract('month', Transaction.date) == month,
                extract('year', Transaction.date) == year
            ).scalar() or 0

        # Process subcategories
        subcategories_data = []
        total_sub_budgeted = 0
        total_sub_actual = 0

        for sub in cat.subcategories:
            sub_budget = Budget.query.filter_by(
                category_id=sub.id,
                month=month,
                year=year
            ).first()

            if category_type == 'income':
                sub_actual = db.session.query(db.func.sum(Transaction.amount)).filter(
                    Transaction.category_id == sub.id,
                    Transaction.transaction_type == 'income',
                    extract('month', Transaction.date) == month,
                    extract('year', Transaction.date) == year
                ).scalar() or 0
            else:
                sub_actual = db.session.query(db.func.sum(Transaction.amount)).filter(
                    Transaction.category_id == sub.id,
                    Transaction.transaction_type == 'expense',
                    extract('month', Transaction.date) == month,
                    extract('year', Transaction.date) == year
                ).scalar() or 0

            sub_budgeted = sub_budget.amount if sub_budget else 0
            total_sub_budgeted += sub_budgeted
            total_sub_actual += sub_actual

            subcategories_data.append({
                'category_id': sub.id,
                'category_name': sub.name,
                'budgeted': sub_budgeted,
                'actual': sub_actual,
                'difference': sub_actual - sub_budgeted,
                'is_subcategory': True
            })

        # Parent category budgeted is sum of subcategories, actual includes parent + subs
        parent_budgeted = budget.amount if budget else 0
        combined_budgeted = parent_budgeted + total_sub_budgeted
        combined_actual = actual + total_sub_actual

        overview.append({
            'category_id': cat.id,
            'category_name': cat.name,
            'budgeted': combined_budgeted,
            'actual': combined_actual,
            'difference': combined_actual - combined_budgeted,
            'subcategory_count': len(cat.subcategories),
            'subcategories': subcategories_data,
            'is_subcategory': False
        })

    return jsonify(overview)

if __name__ == '__main__':
    app.run(debug=True)