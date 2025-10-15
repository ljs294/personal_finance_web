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

@app.route('/api/transactions/<int:id>', methods=['PUT'])
def update_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    data = request.json

    transaction.description = data['description']
    transaction.amount = data['amount']
    transaction.date = datetime.fromisoformat(data['date'])
    transaction.transaction_type = data['transaction_type']
    transaction.category_id = data.get('category_id')
    transaction.notes = data.get('notes')

    db.session.commit()
    return jsonify(transaction.to_dict())

@app.route('/api/transactions/<int:id>', methods=['DELETE'])
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    return '', 204

@app.route('/api/category-details/<int:category_id>', methods=['GET'])
def get_category_details(category_id):
    from sqlalchemy import extract

    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if not month or not year:
        now = datetime.now()
        month = now.month
        year = now.year

    # Get the category
    category = Category.query.get_or_404(category_id)

    # Get budget for parent category
    parent_budget = Budget.query.filter_by(
        category_id=category_id,
        month=month,
        year=year
    ).first()

    # Get spending for parent category in the current month (not including subcategories)
    parent_spent = db.session.query(db.func.sum(Transaction.amount)).filter(
        Transaction.category_id == category_id,
        Transaction.transaction_type == 'expense',
        extract('month', Transaction.date) == month,
        extract('year', Transaction.date) == year
    ).scalar() or 0

    # Get subcategories with their budgets and spending
    subcategories_data = []
    total_sub_budget = 0
    total_sub_spent = 0

    for sub in category.subcategories:
        sub_budget = Budget.query.filter_by(
            category_id=sub.id,
            month=month,
            year=year
        ).first()

        sub_spent = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.category_id == sub.id,
            Transaction.transaction_type == 'expense',
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).scalar() or 0

        sub_budget_amount = sub_budget.amount if sub_budget else 0
        total_sub_budget += sub_budget_amount
        total_sub_spent += sub_spent

        subcategories_data.append({
            'id': sub.id,
            'name': sub.name,
            'budget': sub_budget_amount,
            'spent': sub_spent
        })

    # Total budget and spent includes parent + all subcategories
    parent_budget_amount = parent_budget.amount if parent_budget else 0
    total_budget = parent_budget_amount + total_sub_budget
    total_spent = parent_spent + total_sub_spent

    return jsonify({
        'category_id': category.id,
        'category_name': category.name,
        'budget': total_budget,
        'spent': total_spent,
        'parent_budget': parent_budget_amount,
        'parent_spent': parent_spent,
        'subcategories': subcategories_data
    })

@app.route('/api/spending-comparison', methods=['GET'])
def get_spending_comparison():
    from sqlalchemy import extract, func
    from collections import defaultdict

    # Get current date
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    # Calculate previous month
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    # Get current month's daily spending
    current_spending = db.session.query(
        extract('day', Transaction.date).label('day'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.transaction_type == 'expense',
        extract('month', Transaction.date) == current_month,
        extract('year', Transaction.date) == current_year
    ).group_by(extract('day', Transaction.date)).all()

    # Get previous month's daily spending
    prev_spending = db.session.query(
        extract('day', Transaction.date).label('day'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.transaction_type == 'expense',
        extract('month', Transaction.date) == prev_month,
        extract('year', Transaction.date) == prev_year
    ).group_by(extract('day', Transaction.date)).all()

    # Convert to dictionaries for easier lookup
    current_by_day = {int(day): float(total) for day, total in current_spending}
    prev_by_day = {int(day): float(total) for day, total in prev_spending}

    # Get the current day of month to limit comparison
    current_day = now.day

    # Build arrays for all days up to current day with cumulative totals
    days = list(range(1, current_day + 1))

    # Calculate cumulative spending
    current_data = []
    prev_data = []
    current_cumulative = 0
    prev_cumulative = 0

    for day in days:
        current_cumulative += current_by_day.get(day, 0)
        prev_cumulative += prev_by_day.get(day, 0)
        current_data.append(round(current_cumulative, 2))
        prev_data.append(round(prev_cumulative, 2))

    # Get total budgeted amounts for both months
    current_budget_total = db.session.query(func.sum(Budget.amount)).filter(
        Budget.month == current_month,
        Budget.year == current_year
    ).join(Category).filter(
        Category.category_type == 'expense'
    ).scalar() or 0

    prev_budget_total = db.session.query(func.sum(Budget.amount)).filter(
        Budget.month == prev_month,
        Budget.year == prev_year
    ).join(Category).filter(
        Category.category_type == 'expense'
    ).scalar() or 0

    return jsonify({
        'days': days,
        'current_month': {
            'month': current_month,
            'year': current_year,
            'data': current_data,
            'budget': round(float(current_budget_total), 2)
        },
        'previous_month': {
            'month': prev_month,
            'year': prev_year,
            'data': prev_data,
            'budget': round(float(prev_budget_total), 2)
        }
    })

@app.route('/api/category-spending', methods=['GET'])
def get_category_spending():
    from sqlalchemy import extract

    # Get current month and year or from query params
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)

    if not month or not year:
        now = datetime.now()
        month = now.month
        year = now.year

    categories = Category.query.filter_by(parent_id=None, category_type='expense').all()
    spending = []

    for cat in categories:
        # Get spending for current month
        total = db.session.query(db.func.sum(Transaction.amount)).filter(
            Transaction.category_id == cat.id,
            Transaction.transaction_type == 'expense',
            extract('month', Transaction.date) == month,
            extract('year', Transaction.date) == year
        ).scalar() or 0

        # Get subcategory spending for current month
        sub_total = 0
        for sub in cat.subcategories:
            sub_amount = db.session.query(db.func.sum(Transaction.amount)).filter(
                Transaction.category_id == sub.id,
                Transaction.transaction_type == 'expense',
                extract('month', Transaction.date) == month,
                extract('year', Transaction.date) == year
            ).scalar() or 0
            sub_total += sub_amount

        combined_total = total + sub_total

        # Get budget for current month (parent + subcategories)
        budget = Budget.query.filter_by(
            category_id=cat.id,
            month=month,
            year=year
        ).first()

        parent_budget = budget.amount if budget else 0
        sub_budget_total = 0

        for sub in cat.subcategories:
            sub_budget = Budget.query.filter_by(
                category_id=sub.id,
                month=month,
                year=year
            ).first()
            if sub_budget:
                sub_budget_total += sub_budget.amount

        combined_budget = parent_budget + sub_budget_total

        # Calculate percentage
        percentage = 0
        if combined_budget > 0:
            percentage = (combined_total / combined_budget) * 100

        spending.append({
            'category_id': cat.id,
            'category_name': cat.name,
            'amount': combined_total,
            'budget': combined_budget,
            'percentage': percentage,
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