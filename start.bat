@echo off
cd /d C:\Users\ljsma\Documents\Projects\budget-tracker
call venv\Scripts\activate
start http://localhost:5000
python app.py
pause