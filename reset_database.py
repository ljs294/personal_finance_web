"""
Script to reset the database with the new schema including user authentication.
This will delete all existing data and create new tables.
"""
import os
import sys
from flask import Flask
from models import db, User, Category, Transaction, Budget
from config import Config

# Create a new Flask app instance for migration
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

def reset_database():
    with app.app_context():
        # Get the database file path
        db_path = os.path.join(app.instance_path, 'budget.db')

        # Drop all tables and recreate
        print("Dropping all existing tables...")
        db.drop_all()

        # Create new database with updated schema
        print("Creating new database with user authentication...")
        db.create_all()
        print("Database created successfully!")
        print("\nYou can now start the app and register a new user.")

if __name__ == '__main__':
    reset_database()
