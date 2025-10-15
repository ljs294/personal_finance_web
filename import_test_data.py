from app import app, db
from models import Category, Transaction, Budget
from datetime import datetime
import json

def import_test_data():
    with app.app_context():
        print("Starting test data import...")

        # Load test data files
        with open('test_budget.json', 'r') as f:
            budget_json = json.load(f)

        with open('test_transactions.json', 'r') as f:
            transaction_data = json.load(f)

        month = budget_json['month']
        year = budget_json['year']

        # Create a mapping of category names to IDs
        category_map = {}

        # First, create all parent expense categories
        print("\nCreating parent expense categories...")
        for item in budget_json['budgets']:
            # Check if category already exists
            existing = Category.query.filter_by(
                name=item['category_name'],
                parent_id=None,
                category_type='expense'
            ).first()

            if not existing:
                category = Category(
                    name=item['category_name'],
                    parent_id=None,
                    category_type='expense'
                )
                db.session.add(category)
                db.session.flush()
                category_map[item['category_name']] = category.id
                print(f"  Created: {item['category_name']} (ID: {category.id})")
            else:
                category_map[item['category_name']] = existing.id
                print(f"  Already exists: {item['category_name']} (ID: {existing.id})")

        db.session.commit()

        # Create parent income categories
        print("\nCreating income categories...")
        for item in budget_json['income_budgets']:
            existing = Category.query.filter_by(
                name=item['category_name'],
                parent_id=None,
                category_type='income'
            ).first()

            if not existing:
                category = Category(
                    name=item['category_name'],
                    parent_id=None,
                    category_type='income'
                )
                db.session.add(category)
                db.session.flush()
                category_map[item['category_name']] = category.id
                print(f"  Created: {item['category_name']} (ID: {category.id})")
            else:
                category_map[item['category_name']] = existing.id
                print(f"  Already exists: {item['category_name']} (ID: {existing.id})")

        db.session.commit()

        # Then create all subcategories
        print("\nCreating subcategories...")
        for item in budget_json['budgets']:
            parent_name = item['category_name']
            parent_id = category_map.get(parent_name)

            if parent_id and 'subcategories' in item:
                for subcat in item['subcategories']:
                    # Check if subcategory already exists
                    existing = Category.query.filter_by(
                        name=subcat['category_name'],
                        parent_id=parent_id,
                        category_type='expense'
                    ).first()

                    if not existing:
                        category = Category(
                            name=subcat['category_name'],
                            parent_id=parent_id,
                            category_type='expense'
                        )
                        db.session.add(category)
                        db.session.flush()
                        category_map[f"{parent_name} > {subcat['category_name']}"] = category.id
                        print(f"  Created: {parent_name} > {subcat['category_name']} (ID: {category.id})")
                    else:
                        category_map[f"{parent_name} > {subcat['category_name']}"] = existing.id
                        print(f"  Already exists: {parent_name} > {subcat['category_name']} (ID: {existing.id})")

        db.session.commit()

        # Create budgets for parent categories
        print(f"\nCreating budgets for {month}/{year}...")
        for item in budget_json['budgets']:
            category_id = category_map.get(item['category_name'])

            if category_id:
                # Check if budget already exists
                existing_budget = Budget.query.filter_by(
                    category_id=category_id,
                    month=month,
                    year=year
                ).first()

                if not existing_budget:
                    budget = Budget(
                        category_id=category_id,
                        amount=item['amount'],
                        month=month,
                        year=year
                    )
                    db.session.add(budget)
                    print(f"  Created budget: {item['category_name']} - ${item['amount']}")
                else:
                    existing_budget.amount = item['amount']
                    print(f"  Updated budget: {item['category_name']} - ${item['amount']}")

            # Create budgets for subcategories
            if 'subcategories' in item:
                for subcat in item['subcategories']:
                    subcat_id = category_map.get(f"{item['category_name']} > {subcat['category_name']}")

                    if subcat_id:
                        existing_budget = Budget.query.filter_by(
                            category_id=subcat_id,
                            month=month,
                            year=year
                        ).first()

                        if not existing_budget:
                            budget = Budget(
                                category_id=subcat_id,
                                amount=subcat['amount'],
                                month=month,
                                year=year
                            )
                            db.session.add(budget)
                            print(f"  Created budget: {item['category_name']} > {subcat['category_name']} - ${subcat['amount']}")
                        else:
                            existing_budget.amount = subcat['amount']
                            print(f"  Updated budget: {item['category_name']} > {subcat['category_name']} - ${subcat['amount']}")

        # Create income budgets
        for item in budget_json['income_budgets']:
            category_id = category_map.get(item['category_name'])

            if category_id:
                existing_budget = Budget.query.filter_by(
                    category_id=category_id,
                    month=month,
                    year=year
                ).first()

                if not existing_budget:
                    budget = Budget(
                        category_id=category_id,
                        amount=item['amount'],
                        month=month,
                        year=year
                    )
                    db.session.add(budget)
                    print(f"  Created income budget: {item['category_name']} - ${item['amount']}")
                else:
                    existing_budget.amount = item['amount']
                    print(f"  Updated income budget: {item['category_name']} - ${item['amount']}")

        db.session.commit()

        # Create transactions
        print(f"\nCreating transactions for {month}/{year}...")
        transaction_count = 0
        for item in transaction_data['transactions']:
            # Find category ID by matching category name
            category_id = None

            # Check if it has a parent category (subcategory)
            if 'parent_category' in item and item['parent_category']:
                lookup_key = f"{item['parent_category']} > {item['category_name']}"
                category_id = category_map.get(lookup_key)

            # If not found, try just the category name (parent category)
            if not category_id:
                category_id = category_map.get(item['category_name'])

            # Check if transaction already exists (by description, amount, and date)
            transaction_date = datetime.fromisoformat(item['date']).date()
            existing_transaction = Transaction.query.filter_by(
                description=item['description'],
                amount=item['amount'],
                date=transaction_date
            ).first()

            if not existing_transaction:
                transaction = Transaction(
                    description=item['description'],
                    amount=item['amount'],
                    date=transaction_date,
                    transaction_type=item['transaction_type'],
                    category_id=category_id,
                    notes=item.get('notes')
                )
                db.session.add(transaction)
                transaction_count += 1
                if transaction_count % 10 == 0:
                    print(f"  Created {transaction_count} transactions...")
            else:
                print(f"  Skipped duplicate: {item['description']}")

        db.session.commit()
        print(f"  Total transactions created: {transaction_count}")

        print("\nTest data import complete!")
        print(f"Categories created: {len(category_map)}")
        print(f"Budgets created/updated for {month}/{year}")
        print(f"Transactions created: {transaction_count}")

if __name__ == '__main__':
    import_test_data()
