# User Login System Guide

## Overview
The Budget Tracker app now includes a complete user authentication system. Each user has their own private data (transactions, categories, and budgets) that is isolated from other users.

## Features Implemented

### 1. User Authentication
- **Registration**: New users can create an account with username, email, and password
- **Login**: Existing users can log in with username and password
- **Logout**: Users can securely log out from the application
- **Session Management**: User sessions are maintained with Flask-Login

### 2. Data Isolation
All data is now user-specific:
- **Categories**: Each user has their own expense and income categories
- **Transactions**: Transactions are private to each user
- **Budgets**: Budget allocations are user-specific
- **Security**: Users cannot access other users' data

### 3. Database Schema Updates
New tables and relationships:
- **User table**: Stores user credentials (username, email, password hash)
- **Foreign keys**: All data tables (Category, Transaction, Budget) now have user_id foreign keys
- **Relationships**: Proper cascading deletes to maintain data integrity

## How to Use

### First Time Setup
1. **Reset the database** (if you had data before):
   ```bash
   python reset_database.py
   ```

2. **Start the application**:
   ```bash
   python app.py
   ```

3. **Access the app**: Open your browser and navigate to `http://127.0.0.1:5000`

### Creating an Account
1. Navigate to `http://127.0.0.1:5000/register`
2. Fill in:
   - Username (unique)
   - Email (unique)
   - Password (minimum 6 characters)
3. Click "Create Account"
4. You'll be automatically logged in and redirected to the dashboard

### Logging In
1. Navigate to `http://127.0.0.1:5000/login`
2. Enter your username and password
3. Click "Log In"
4. You'll be redirected to your personal dashboard

### Logging Out
- Click the "Logout" link in the top navigation bar
- You'll be logged out and redirected to the login page

## API Changes

All API endpoints now require authentication:
- `/api/categories` - Get/Create categories (user-specific)
- `/api/transactions` - Get/Create transactions (user-specific)
- `/api/budgets` - Get/Create budgets (user-specific)
- `/api/category-spending` - Get spending by category (user-specific)
- `/api/spending-comparison` - Get spending comparison (user-specific)
- `/api/budget-overview` - Get budget overview (user-specific)

## Security Features

1. **Password Hashing**: Passwords are hashed using Werkzeug's security functions
2. **Session Security**: Flask-Login manages secure sessions
3. **CSRF Protection**: Forms are protected against cross-site request forgery
4. **Data Isolation**: Database queries filter by user_id to prevent data leakage
5. **Authentication Required**: All routes except login/register require authentication

## File Structure

### New Files
- `templates/login.html` - Login page
- `templates/register.html` - Registration page
- `reset_database.py` - Database migration script

### Modified Files
- `models.py` - Added User model and user_id foreign keys
- `app.py` - Added authentication routes and @login_required decorators
- `templates/index.html` - Added logout button
- `requirements.txt` - Added Flask-Login dependency

## Technical Details

### User Model
```python
class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Relationships
    categories = relationship('Category')
    transactions = relationship('Transaction')
    budgets = relationship('Budget')
```

### Authentication Flow
1. User registers → Password is hashed → User created in database
2. User logs in → Password verified → Session created
3. User accesses protected route → @login_required decorator checks session
4. API queries → Automatically filtered by current_user.id
5. User logs out → Session destroyed

## Next Steps

You can now:
1. Create multiple user accounts to test data isolation
2. Add additional security features (email verification, password reset)
3. Implement role-based access control if needed
4. Add profile management features

## Troubleshooting

**Issue**: Can't access the dashboard
- **Solution**: Make sure you're logged in. Navigate to `/login`

**Issue**: Database errors
- **Solution**: Run `python reset_database.py` to recreate the database

**Issue**: Flask-Login not installed
- **Solution**: Run `pip install -r requirements.txt`

## Support

For questions or issues, check:
- Flask-Login documentation: https://flask-login.readthedocs.io/
- Flask documentation: https://flask.palletsprojects.com/
