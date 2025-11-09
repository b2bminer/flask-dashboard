from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import requests
import os
import xmlrpc.client

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow frontend to communicate with backend

#ODOO Configuration
ODOO_URL = "http://localhost:8069"  # Replace with your Odoo service name
ODOO_DB = "odoo"
ODOO_USERNAME = "phichetnoraset@gmail.com"
ODOO_PASSWORD = "Asdf1234"

common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Asdf1234@localhost:5432/odoo")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL

app.config["SQLALCHEMY_BINDS"] = {
    "supabase": "postgresql://postgres.fkjsplyswcxdwlepogrp:phichet1234@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"  # Supabase DB
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ✅ Create Model
class FormData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class Rating(db.Model):
    __tablename__ = 'ratings'
    customer_id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)

class Users(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=True)
    work_history = db.relationship("WorkHistory", backref="employee", cascade="all, delete")

class WorkHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

# Define User model for Supabase (use the bind key)
class SupabaseUser(db.Model):
    __tablename__ = "users"
    __bind_key__ = "supabase"  # This tells SQLAlchemy to use the Supabase DB
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)

class SupabaseWatchlist(db.Model):
    __tablename__ = "watchlist"
    __bind_key__ = "supabase"  # This tells SQLAlchemy to use the Supabase DB
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    created_at = db.Column(db.DateTime)

# ✅ Create Tables
with app.app_context():
    db.create_all()

def get_odoo_info():
    """Fetch Odoo system information using XML-RPC."""
    try:
        # Connect to Odoo's XML-RPC API
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        version_info = common.version()
        list_1d = ["one","two","three","four",'five']
        list_2d = [
            [1, 2, 3], 
            [4, 5, 6], 
            [7, 8, 9]
        ]
        list_2d_00 = list_2d[0][0]
        list_3d = [
            [  # First layer (depth = 0)
                [1, 2, 3], 
                [4, 5, 6]
            ],
            [  # Second layer (depth = 1)
                [7, 8, 9], 
                [10, 11, 12]
            ]
        ]
        list_3d_001 = list_3d[0][0][1]

        return {
            "Odoo Version": version_info.get("server_version"),
            "Database Name": ODOO_DB,
            "Array 1d": list_1d,
            "Array 2d": list_2d,
            "Array 2d_00": list_2d_00,
            "Array 3d": list_3d,
            "Array 3d [0,0,1]": list_3d_001
        }
    except Exception as e:
        return {"error": str(e)}

def get_odoo_session():
    session = requests.Session()

    # Step 1: Login
    login_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USERNAME,
            "password": ODOO_PASSWORD
        }
    }

    login_response = session.post(f"{ODOO_URL}/web/session/authenticate", json=login_payload)
    print("Login Response Status:", login_response.status_code)
    print("Login Response Text:", login_response.text)  # Debug

    if login_response.status_code != 200:
        return {"error": "Login request failed"}

    try:
        login_data = login_response.json()
        if "result" not in login_data:
            return {"error": "Login failed", "details": login_data}
    except requests.exceptions.JSONDecodeError:
        return {"error": "Login response was not JSON", "response": login_response.text}

    # ✅ Step 2: Use POST instead of GET for session info
    session_payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": {}
    }

    response = session.post(f"{ODOO_URL}/web/session/get_session_info", json=session_payload)
    
    print("Session Info Response Status:", response.status_code)
    print("Session Info Response Text:", response.text)  # Debug

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return {"error": "Session response was not JSON", "response": response.text}

@app.route('/get_customers', methods=['GET'])
def get_customers():
    try:
        #common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        #id = common.authenticate(db, username, password, {})
        #models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
        customers = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, 'res.partner', 'search_read', [[('customer_rank', '>=', 0)]], {'fields': ['id', 'name', 'email', 'phone']})
        return jsonify(customers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_custom_model():
    url = "http://localhost:8069"
    db = "odoo"
    username = "phichetnoraset@gmail.com"
    password = "Asdf1234"

    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    ids = models.execute_kw(db, uid, password, 'res.partner', 'search_read', [[['is_company', '=', True]]], {'fields': ['name', 'country_id', 'comment'], 'limit': 5})
    return ids

@app.route('/')
def home():
    data = FormData.query.all()
    #system_info = get_odoo_info()
    #system_info2 = get_odoo_session()
    #return render_template('index.html', data=data, system_info=system_info, system_info2=system_info2)
    return render_template('index.html', data=data )

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/customers')
def customers():
    #data = get_customers()
    custom_data = get_custom_model()
    return render_template('customers.html', custom_datas=custom_data)

@app.route('/vendor')
def vendor():
    return render_template('vendor_entry.html')

@app.route('/employee')
def employee_entry():
    return render_template('employee_entry.html')

@app.route('/supabase')
def supabase():
    return render_template('supabase.html')

@app.route("/submit", methods=["POST"])
def submit():
    name = request.form["name"]
    email = request.form["email"]
    message = request.form["message"]

    new_entry = FormData(name=name, email=email, message=message)
    db.session.add(new_entry)
    db.session.commit()

    # TODO: Process data (save to database, send email, etc.)
    print(f"Received Data - Name: {name}, Email: {email}, Message: {message}")

    #return redirect(url_for("home"))
    return jsonify({"success": True})

@app.route("/odoo_status")
def odoo_status():
    session_info = get_odoo_session()
    print(session_info)
    return jsonify(session_info)

@app.route('/create_customer', methods=['POST'])
def create_customer():
    try:
        data = request.json
        customer_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'create', [{
                'name': data['name'],
                'email': data.get('email', ''),
                'phone': data.get('phone', ''),
                'customer_rank': 1
            }]
        )
        return jsonify({"message": "Customer Created", "customer_id": customer_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/add_supabase_user', methods=['POST'])
def add_supabase_user():
    try:
        data = request.json
        if not data or "email" not in data or "name" not in data:
            return jsonify({"error": "Missing required fields (email, name)"}), 400
        new_user = SupabaseUser(email=data["email"], name=data["name"])
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User added to Supabase DB successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500  # Return the exact error message

@app.route('/edit_supabase_user', methods=['POST'])
def edit_supabase_user():
    try:
        data = request.json
        user_id = data.get("id")
        new_name = data.get("name")
        new_email = data.get("email")

        if not user_id or not new_name or not new_email:
            return jsonify({"error": "Missing required fields (id, name, email)"}), 400

        user = SupabaseUser.query.get(user_id)
        if user:
            user.name = new_name
            user.email = new_email
            db.session.commit()
            return jsonify({"message": "User updated in Supabase DB successfully"}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/delete_supabase_user', methods=['POST'])
def delete_supabase_user():
    try:
        data = request.json
        user_id = data.get("id")

        if not user_id:
            return jsonify({"error": "Missing required field (id)"}), 400

        user = SupabaseUser.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            return jsonify({"message": "User deleted from Supabase DB successfully"}), 200
        else:
            return jsonify({"error": "User not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route('/get_supabase_users', methods=['GET'])
def get_supabase_users():
    users = SupabaseUser.query.all()
    return jsonify([{"id": user.id, "email": user.email, "name": user.name} for user in users])

@app.route('/ratings', methods=['GET'])
def get_ratings():
    ratings = Rating.query.all()
    return jsonify([{
        'customer_id': r.customer_id,
        'product_id': r.product_id,
        'rating': r.rating
    } for r in ratings])

@app.route("/add_employee", methods=["POST"])
def add_employee():
    data = request.json
    try:
        new_employee = Employee(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            address=data.get("address")
        )
        db.session.add(new_employee)
        db.session.commit()
        return jsonify({"message": "Employee Added!" + str(new_employee.id), "employee_id": new_employee.id})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/edit_employee', methods=['PUT'])
def edit_employee():
    data = request.json
    employee_id = data.get("id")
    print("Received JSON:", data)

    if not employee_id:
        return jsonify({"error": "Employee ID is required"}), 400

    employee = Employee.query.get(employee_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    try:
        # อัปเดตฟิลด์ต่างๆ
        employee.name = data.get("name", employee.name)
        employee.email = data.get("email", employee.email)
        employee.phone = data.get("phone", employee.phone)
        employee.address = data.get("address", employee.address)

        db.session.commit()
        return jsonify({"message": f"Employee {employee_id} updated successfully"})
    
    except Exception as e:
        db.session.rollback()  # Rollback ถ้ามีข้อผิดพลาด
        return jsonify({"error": str(e)}), 400

@app.route("/add_work_history", methods=["POST"])
def add_work_history():
    try:
        # ✅ Extract JSON data from request
        data = request.json

        # ✅ Retrieve values safely
        employee_id = data.get("employee_id")
        company = data.get("company")
        position = data.get("position")
        start_date = data.get("startDate")
        end_date = data.get("endDate", None)  # Optional

        # ✅ Validate required fields
        if not employee_id or not company or not position or not start_date:
            return jsonify({"error": "Missing required fields"}), 400

        # ✅ Insert into WorkHistory table
        new_work = WorkHistory(
            employee_id=employee_id,
            company=company,
            position=position,
            start_date=start_date,
            end_date=end_date
        )

        db.session.add(new_work)
        db.session.commit()
        return jsonify({"message": "Work History Added!"}), 201

    except Exception as e:
        print("Error:", str(e))  # Debugging in terminal
        return jsonify({"error": str(e)}), 500

@app.route("/get_employees", methods=["GET"])
def get_employees():
    employees = Employee.query.order_by(Employee.name).all()
    return jsonify([{
        "id": emp.id,
        "name": emp.name,
        "email": emp.email,
        "phone": emp.phone,
        "address": emp.address
    } for emp in employees])

# 🚀 Get Work History for Employee
@app.route("/get_work_history/<int:employee_id>", methods=["GET"])
def get_work_history(employee_id):
    work_entries = WorkHistory.query.filter_by(employee_id=employee_id).all()
    return jsonify([{
        "id": work.id,
        "company": work.company,
        "position": work.position,
        "start_date": work.start_date.strftime("%Y-%m-%d"),
        "end_date": work.end_date.strftime("%Y-%m-%d") if work.end_date else "Present"
    } for work in work_entries])

@app.route("/save_work_history", methods=["POST"])
def save_work_history():
    try:
        data = request.json
        work_history_list = data.get("workHistory", [])

        # Process each work history record
        for work_history in work_history_list:
            if work_history.get("id"):  # แก้ไข
                history = WorkHistory.query.get(work_history["id"])
                if history:
                    history.company = work_history["company"]
                    history.position = work_history["position"]
                    history.start_date = work_history["startDate"]
                    history.end_date = work_history["endDate"]
            else:  # เพิ่มใหม่
                # Ensure employee_id is set (this should come from the frontend)
                employee_id = work_history.get("employee_id")
                if not employee_id:
                    return jsonify({"error": "Employee ID is required"}), 400  # Return error if employee_id is missing

                # Handle empty end_date (set to None if empty string)
                end_date = work_history.get("endDate")
                if end_date == "":
                    end_date = None

                new_work = WorkHistory(
                    employee_id=employee_id,
                    company=work_history["company"],
                    position=work_history["position"],
                    start_date=work_history["startDate"],
                    end_date=end_date
                )

                db.session.add(new_work)

        db.session.commit()
        return jsonify({"message": "Work History Saved Successfully!"}), 201
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/delete_work_history/<int:work_history_id>", methods=["DELETE"])
def delete_work_history(work_history_id):
    # ลบข้อมูลจาก database โดยใช้ ID
    result = delete_from_database_by_id(work_history_id)  # เขียนฟังก์ชันลบเอง
    if result:
        return jsonify({"message": "Deleted successfully."}), 200
    else:
        return jsonify({"message": "Failed to delete."}), 400

def delete_from_database_by_id(work_history_id):
    try:
        record = WorkHistory.query.get(work_history_id)
        if record:
            db.session.delete(record)
            db.session.commit()
            return True
        else:
            return False  # ไม่พบ record
    except Exception as e:
        print(f"Error deleting work history: {e}")
        db.session.rollback()
        return False
    
@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/css')
def css():
    return render_template('css.html')

from settrade_v2 import Investor
from settrade_v2.errors import SettradeError
import pandas as pd
import numpy as np
from scipy import stats  # สำหรับคำนวณ percentile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta, timezone
import yfinance as yf
from sklearn.linear_model import LinearRegression
import os
import base64
from io import BytesIO
import csv
import pytz
import talib
import io
from datetime import timedelta

from fetch_stock_data import get_stock_data, fetch_stock_data

from DropboxServices import upload_base64_image, upload_combined_base64_images, clear_dropbox_folder, build_gallery_page
from GithubServices import combined_base64_images, upload_file_to_github, upload_multiple_files_to_github, delete_all_files_in_github

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
HF_API_URL = "https://api-inference.huggingface.co/models/csebuetnlp/mT5_multilingual_XLSum"
HF_TOKEN = os.getenv("HF_TOKEN")
HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

set100 = [
    "AAV", "AMATA", "AOT", "AP", "AWC", "BA", "BAM", "BANPU",
    "BBL", "BCH", "BCP", "BCPG", "BDMS", "BEM", "BGRIM", "BH", "BJC", "BLA",
    "BSRC", "BTG", "BTS", "CBG", "CCET", "CENTEL", "CHG", "CK", "CKP", "COCOCO",
    "COM7", "CPALL", "CPF", "CPN", "CRC", "DELTA", "DOHOME", "EA", "EGCO",
    "GLOBAL", "GPSC", "GULF", "GUNKUL", "HANA", "HMPRO", "ICHI", "IRPC", "ITC",
    "IVL", "JAS", "JMT", "KBANK", "KCE", "KKP", "KTB", "KTC",
    "MEGA", "MINT", "MTC", "OR", "OSP", "PLANB",
    "PTT", "PTTEP", "PTTGC", "RATCH", "RCL", "SAPPE", "SAWAD", "SCB",
    "SCGP", "SISB", "SJWD", "SKY", "SPRC", "STA", "STGT", "TASCO",
    "TIDLOR", "TISCO", "TLI", "TOP", "TRUE", "TTB", "TU", "VGI", "WHA", "UVAN", "TACC"
]
set100A = [
    "AAV", "AMATA", "AOT", "AP", "AWC", "BA", "BAM", "BANPU",
    "BBL", "BCH", "BCP", "BCPG", "BDMS", "BEM", "BGRIM", "BH", "BJC", "BLA",
    "BSRC", "BTG", "BTS", "CBG", "CCET", "CENTEL", "CHG", "CK", "CKP", "COCOCO",
    "COM7", "CPALL", "CPF", "CPN", "CRC", "DELTA", "DOHOME", "EA", "EGCO",
]
set100B = [
    "GLOBAL", "GPSC", "GULF", "GUNKUL", "HANA", "HMPRO", "ICHI", "IRPC", "ITC",
    "IVL", "JAS", "JMT", "KBANK", "KCE", "KKP", "KTB", "KTC",
    "MEGA", "MINT", "MTC", "OR", "OSP", "PLANB",
]
set100C = [
    "PTT", "PTTEP", "PTTGC", "RATCH", "RCL", "SAPPE", "SAWAD", "SCB",
    "SCGP", "SISB", "SJWD", "SKY", "SPRC", "STA", "STGT", "TASCO",
    "TIDLOR", "TISCO", "TLI", "TOP", "TRUE", "TTB", "TU", "VGI", "WHA", "UVAN", "TACC", "THCOM"
]

set100x = ["UVAN", "TACC"]

@app.route('/get_set100')
def get_set100():
    return jsonify(set100)

import os
import time
from pathlib import Path
DATA_DIR = "data"
Path(DATA_DIR).mkdir(exist_ok=True)
os.makedirs('images', exist_ok=True)

from CNN_prepare_stock_image import generate_candlestick_image, prepare_stock_image
from CNN_predict_my_model import predict_patternAPI

@app.route("/downloadStockdata")
def downloadStockdata():
    ticker = request.args.get('ticker', '')
    #set100x = [ticker] if ticker else get_user_watchlist()
    load_flag = request.args.get('load_flag', 'WL')  # เพิ่มการรับค่า load_flag
    if ticker:
        set100x = ticker
    elif load_flag == 'WL':
        set100x = get_user_watchlist()
    elif load_flag == 'SET100A':
        set100x = set100A
    elif load_flag == 'SET100B':
        set100x = set100B
    elif load_flag == 'SET100C':
        set100x = set100C
    else:
        return jsonify({"error": "Invalid load_flag value"}), 400
    investor = Investor(
        app_id="gnPhUtkuauTPjrqK",
        app_secret="RW53D4/kib04nDaWLn5qi1DtA3sO/zdXzQSaxGWctbs=",
        broker_id="023",
        app_code="ALGO_EQ",
        is_auto_queue=False
    )

    mkt_data = investor.MarketData()
    current_date = datetime.now()
    start_date = (current_date - timedelta(days=365)).strftime("%Y-%m-%dT00:00")
    end_date = current_date.strftime("%Y-%m-%dT23:59")

    print(f"Downloading data from {start_date} to {end_date}")
    timeframes = [
        {'interval': '15m', 'days_limit': 30},  # 15 นาที เก็บได้ 7 วัน
        {'interval': '60m', 'days_limit': 60},    # 1 ชั่วโมง เก็บได้ 30 วัน
        {'interval': '1d', 'days_limit': 365*2},   # 1 วัน เก็บได้ 1 ปี
        {'interval': '1w', 'days_limit': 365*2}, # 1 สัปดาห์ เก็บได้ 2 ปี
        {'interval': '1M', 'days_limit': 365*5}  # 1 เดือน เก็บได้ 5 ปี
    ]

    results = {}

    for symbol in set100x:
        print(f"\n=== Downloading for {symbol} ===")
        results[symbol] = {}

        for tf in timeframes:
            try:
                print(f"  Processing {tf['interval']} timeframe...")
                res = mkt_data.get_candlestick(
                    symbol=symbol,
                    interval=tf['interval'],
                    limit=1000,
                    normalized=True,
                    start=start_date,
                    end=end_date
                )

                df = pd.DataFrame({
                    'time': pd.to_datetime(res['time'], unit='s'),
                    'open': res['open'],
                    'high': res['high'],
                    'low': res['low'],
                    'close': res['close'],
                    'volume': res['volume'],
                    'value': res['value']
                })

                df = df.sort_values('time')
                df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')

                if tf['interval'] in ['1d', '1w', '1M']:
                    df['date'] = df['time'].dt.date

                filename = f"{DATA_DIR}/{symbol}_{tf['interval']}.csv"
                df.to_csv(filename, index=False)
                print(f"  Saved {len(df)} rows to {filename}")

                results[symbol][tf['interval']] = {
                    'status': 'success',
                    'records': len(df),
                    'filename': filename
                }
                time.sleep(1)  # 1 วินาที หรือเปลี่ยนตามที่เหมาะสม

            except Exception as e:
                print(f"  Error: {str(e)}")
                results[symbol][tf['interval']] = {
                    'status': 'error',
                    'message': str(e)
                }
            time.sleep(0.25)  # 1/4 วินาที หรือเปลี่ยนตามที่เหมาะสม
        prepare_stock_image(symbol, folder_name='images', file_name=f"{symbol}.png", single_image='Y')

    return jsonify({
        'overall_status': 'completed',
        'symbols': results
    })

@app.route("/tradingviewdata")
def tradingviewdata():
    symbol = request.args.get("symbol", "PTT")
    tf = request.args.get("timeframe", "D")
    from_ts = request.args.get("from", type=float)
    to_ts = request.args.get("to", type=float)

    df = get_stock_data(symbol, tf, from_ts, to_ts)
    if df is None:
        return jsonify({"error": "Data not found"}), 404
    
    return jsonify(df[['time', 'open', 'high', 'low', 'close', 'ema5', 'ema20','volume']].to_dict(orient='records'))

def is_system_available():
    try:
        response = requests.get("https://api.settrade.com/api")
        #https://openapi.settrade.com/api/service-status
        if response.status_code == 200:
            data = response.json()
            return data.get("status") == "available"  # หรือ "OK" ขึ้นอยู่กับ API
        return False
    except requests.RequestException:
        return False

@app.route('/tradingview', methods=['GET', 'POST'])
def tradingview():
    return render_template("tradingview.html")

@app.route('/get_quote')
def get_quote():
    try:
        ticker = request.args.get('ticker', '')
        investor = Investor(
            app_id="gnPhUtkuauTPjrqK",
            app_secret="RW53D4/kib04nDaWLn5qi1DtA3sO/zdXzQSaxGWctbs=",
            broker_id="023",
            app_code="ALGO_EQ",
            is_auto_queue=False
        )
        mkt_data = investor.MarketData()
        quote_data = mkt_data.get_quote_symbol(ticker)
        
        # จัดรูปแบบข้อมูลให้เหมาะสม
        return jsonify({
            'last': quote_data.get('last'),
            'change': quote_data.get('change'),
            'percentChange': quote_data.get('percentChange'),
            'high': quote_data.get('high'),
            'low': quote_data.get('low'),
            'volume': quote_data.get('totalVolume'),
            'open': quote_data.get('open'),
            'time': quote_data.get('lastTradingDate')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/portfolio', methods=['GET', 'POST'])
def portfolio():
    try:
        try:
            # ✅ ห่อการสร้าง Investor ด้วย try แยก
            investor = Investor(
                app_id="gnPhUtkuauTPjrqK",
                app_secret="RW53D4/kib04nDaWLn5qi1DtA3sO/zdXzQSaxGWctbs=",
                broker_id="023",
                app_code="ALGO_EQ",
                is_auto_queue=False
            )
        except SettradeError as e:
            # ✅ ตรวจจับ error จาก SETTRADE โดยตรง
            err_msg = str(e)
            if "U-591" in err_msg or "System Unavailable" in err_msg:
                print("⚠️ SETTRADE API ไม่พร้อมใช้งาน (System Unavailable) — ข้ามการเชื่อมต่อ")
                return render_template(
                    'portfolio.html',
                    account_info=None,
                    portfolio_data=None,
                    set100=set100
                )
            else:
                raise  # ถ้าเป็น error อื่น ให้โยนต่อ
        
        # ✅ ถ้าเชื่อมต่อสำเร็จค่อยเรียกข้อมูลต่อ
        equity = investor.Equity(account_no="602068305")
        account_info = equity.get_account_info()
        portfolio_data = equity.get_portfolios()
        print('portfolio_data')
        print(portfolio_data)
        return render_template(
            'portfolio.html',
            account_info=account_info,
            portfolio_data=portfolio_data,
            set100=set100
        )

    except Exception as e:
        print(f"\nเกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")
        return render_template(
            'portfolio.html',
            account_info=None,
            portfolio_data=None,
            set100=set100
        )

@app.route('/portfolioOLD', methods=['GET', 'POST'])
def portfolioOLD():
    try:
        investor = Investor(
                        app_id="gnPhUtkuauTPjrqK",
                        app_secret="RW53D4/kib04nDaWLn5qi1DtA3sO/zdXzQSaxGWctbs=",
                        broker_id="023",
                        app_code="ALGO_EQ",
                        is_auto_queue = False)
        equity = investor.Equity(account_no="602068305")
        account_info = equity.get_account_info()
        print("Account Info:", account_info)
        portfolio_data   = equity.get_portfolios()
        return render_template('portfolio.html', account_info=account_info, portfolio_data=portfolio_data, set100=set100)
    except Exception as e:
        print(f"\nเกิดข้อผิดพลาดในการเชื่อมต่อ: {str(e)}")
        return render_template('portfolio.html', set100=set100)

def analyze_stock_trend(ticker, isupload=True ):
    try:
        #if enable_date_range == 'Y':
        #    stock_data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
        #else:
        #    stock_data = yf.download(ticker, interval=interval, period=period, auto_adjust=False)
        #stock_data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
        stock_data = get_stock_data(ticker, 'D' )
        if stock_data is None:
            print("ไม่สามารถโหลดข้อมูลหุ้นได้ ", ticker)
            return None, "ไม่สามารถโหลดข้อมูลหุ้นได้"

        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = stock_data.columns.get_level_values(0)
        
        if len(stock_data) == 0:
            return None, "ไม่พบข้อมูลสำหรับหุ้นนี้ในช่วงวันที่กำหนด"
        
        if 'close' not in stock_data.columns:
            return None, "รูปแบบข้อมูลไม่ถูกต้อง - ไม่พบคอลัมน์ราคาปิด"
        if 'volume' not in stock_data.columns:
            return None, "ข้อมูลไม่มีคอลัมน์ Volume"
        # Ensure we have open, high, low, close columns for candlestick analysis
        required_columns = ['open', 'high', 'low', 'close']
        if not all(col in stock_data.columns for col in required_columns):
            return None, "ข้อมูลไม่ครบถ้วนสำหรับการวิเคราะห์แท่งเทียน (ต้องการ open, high, low, close)"
        
        # คำนวณค่าเฉลี่ยเคลื่อนที่
        stock_data['MA_5'] = stock_data['close'].rolling(window=5).mean().fillna(method='bfill')
        stock_data['MA_20'] = stock_data['close'].rolling(window=20).mean()
        stock_data = stock_data.dropna(subset=['MA_20'])
        stock_data['MA_200'] = stock_data['close'].rolling(window=200).mean().fillna(method='bfill')

        stock_data['RSI'] = talib.RSI(stock_data['close'])
        rsi_forecast = predict_rsi_trend(stock_data)
        stock_data['MACD'], stock_data['MACD_signal'], _ = talib.MACD(stock_data['close'])

        # คำนวณ Momentum
        stock_data['Momentum'] = (stock_data['close'] / stock_data['close'].shift(5) - 1) * 100

        # คำนวณ Bollinger Bands
        stock_data['Upper_Band'] = stock_data['MA_20'] + (2 * stock_data['close'].rolling(window=20).std())
        stock_data['Lower_Band'] = stock_data['MA_20'] - (2 * stock_data['close'].rolling(window=20).std())
        # คำนวณ Percentile (เปรียบเทียบกับ 1 ปีย้อนหลัง)
        latest_close = stock_data['close'].iloc[-1]
        one_year_data = stock_data['close'].tail(252)  # 252 วันทำการใน 1 ปี
        percentile = stats.percentileofscore(one_year_data, latest_close)
        # วิเคราะห์ระดับราคา
        price_zone = clean_nan_values({
            'latest_price': latest_close,
            'ma200': stock_data['MA_200'].iloc[-1],
            'percentile': percentile,
            'bollinger_position': None,
            'zone_analysis': None
        })

        # คำนวณค่าเฉลี่ยเคลื่อนที่ของ Volume
        stock_data['Volume_MA_20'] = stock_data['volume'].rolling(window=20).mean()
        # คำนวณปริมาณซื้อขายผิดปกติ (Abnormal Volume)
        stock_data['Volume_Ratio'] = stock_data['volume'] / stock_data['Volume_MA_20']

        stock_data['price_change'] = stock_data['close'].diff()
        stock_data['pct_change'] = stock_data['close'].pct_change() * 100

        # Initialize pattern detection columns
        stock_data['Bullish_Reversal'] = False
        stock_data['Bearish_Reversal'] = False
        stock_data['Candle_Pattern'] = ''
        
        # Detect patterns for last 5 days (most recent patterns are more relevant)
        for i in range(len(stock_data)-3, len(stock_data)):
            current = stock_data.iloc[i]
            prev1 = stock_data.iloc[i-1] if i > 0 else None
            prev2 = stock_data.iloc[i-2] if i > 1 else None
            
            # คำนวณองค์ประกอบพื้นฐาน
            body_size = abs(current['close'] - current['open'])
            total_range = current['high'] - current['low']
            upper_shadow = current['high'] - max(current['open'], current['close'])
            lower_shadow = min(current['open'], current['close']) - current['low']
            
            # Hammer (Bullish reversal)
            if (lower_shadow > 2 * body_size and 
                upper_shadow < body_size * 0.5 and
                current['close'] > current['open']):
                stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True
                stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Hammer'
            
            # Engulfing patterns
            if prev1 is not None:
                # Bullish Engulfing
                if (prev1['close'] < prev1['open'] and 
                    current['open'] < prev1['close'] and 
                    current['close'] > prev1['open']):
                    stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True
                    stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Bullish Engulfing'
                            
            # Morning Star (3-candle pattern)
            if prev2 is not None and prev1 is not None:
                # Morning Star
                if (prev2['close'] < prev2['open'] and 
                    prev1['open'] < prev2['close'] and 
                    prev1['high'] - prev1['low'] > prev2['high'] - prev2['low'] and
                    current['close'] > prev2['open']):
                    stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True
                    stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Morning Star'

            # เงื่อนไข Pin Bar (Bullish)
            if (lower_shadow >= 2 * body_size and 
                upper_shadow <= body_size * 0.3 and
                total_range > 3 * stock_data['close'].rolling(20).std().iloc[-1]):
                stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True
                stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Bullish Pin Bar'
            
            # เงื่อนไข Doji
            elif (body_size <= total_range * 0.05 and  # ตัวแท่งเล็กมาก
                total_range > stock_data['close'].rolling(20).std().iloc[-1] * 0.5):
                stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True  # Doji อาจเป็นสัญญาณกลับตัว
                stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Doji'
                
                # Doji Star Pattern (ต้องการแท่งก่อนหน้าเป็นขาลง)
                if prev1 is not None and prev1['close'] < prev1['open']:
                    stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Bullish Doji Star'

        for i in range(1, len(stock_data)):  # เริ่มจาก index 1 เพราะต้องใช้ข้อมูลวันก่อนหน้า
            current = stock_data.iloc[i]
            prev = stock_data.iloc[i-1]
            
            # คำนวณองค์ประกอบพื้นฐาน
            current_body = current['close'] - current['open']
            prev_body = prev['close'] - prev['open']
            
            # เงื่อนไข Piercing Line (Bullish Reversal)
            piercing_line_conditions = [
                prev['close'] < prev['open'],  # แท่งก่อนหน้าเป็นเทียนแดง (ขาลง)
                current['open'] < prev['close'],  # เปิดต่ำกว่าปิดของวันก่อนหน้า
                current['close'] > (prev['open'] + prev['close']) / 2,  # ปิดเข้าไปมากกว่าครึ่งหนึ่งของเทียนก่อนหน้า
                current['close'] < prev['open'],  # แต่ยังไม่เกินเปิดของวันก่อนหน้า
                current_body > 0,  # แท่งปัจจุบันเป็นเทียนเขียว
                abs(prev_body) > 0.5 * (prev['high'] - prev['low'])  # แท่งก่อนหน้ามีตัวแท่งชัดเจน
            ]
            
            if all(piercing_line_conditions):
                stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True
                stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Piercing Line'

        for i in range(2, len(stock_data)):  # ต้องการอย่างน้อย 2 แท่งก่อนหน้า
            current = stock_data.iloc[i]
            prev1 = stock_data.iloc[i-1]
            
            # เงื่อนไขหลักของ Tweezer Bottom
            tweezer_conditions = [
                # แท่งแรกเป็นขาลง (Red Candle)
                prev1['close'] < prev1['open'],
                # แท่งปัจจุบันเป็นขาขึ้น (Green Candle)
                current['close'] > current['open'],
                # ราคาต่ำสุดเท่ากันหรือใกล้เคียงมาก (ภายใน 0.1%)
                abs(current['low'] - prev1['low']) <= (0.001 * prev1['low']),
                # แท่งปัจจุบันปิดเข้าไปในตัวแท่งก่อนหน้า
                current['close'] > (prev1['open'] + prev1['close']) / 2,
                # ยืนยันปริมาณซื้อขาย
                current['volume'] > prev1['volume'] * 0.8
            ]
            
            if all(tweezer_conditions):
                stock_data.at[stock_data.index[i], 'Bullish_Reversal'] = True
                stock_data.at[stock_data.index[i], 'Candle_Pattern'] = 'Tweezer Bottom'

        ma200_value = stock_data['MA_200'].iloc[-1]
        # Get latest candle pattern
        latest_pattern = stock_data['Candle_Pattern'].iloc[-1]
        latest_bullish_signal = stock_data['Bullish_Reversal'].iloc[-1]
        latest_bearish_signal = stock_data['Bearish_Reversal'].iloc[-1]
        latest = {
            'price': stock_data['close'].iloc[-1],
            'volume': stock_data['volume'].iloc[-1],
            'volume_ma20': stock_data['Volume_MA_20'].iloc[-1],
            'volume_ratio': stock_data['Volume_Ratio'].iloc[-1],
            'ma5': stock_data['MA_5'].iloc[-1],
            'ma20': stock_data['MA_20'].iloc[-1],
            'ma200': round(ma200_value, 2) if not np.isnan(ma200_value) else None,
            'candle_pattern': latest_pattern,
            'bullish_signal': bool(latest_bullish_signal),
            'bearish_signal': bool(latest_bearish_signal)
        }
        #print("latest ", latest)
        # วิเคราะห์ปริมาณซื้อขาย
        volume_analysis = {
            'normal_range': (0.8, 1.2),  # ปริมาณปกติอยู่ระหว่าง 80%-120% ของค่าเฉลี่ย
            'abnormal_volume': latest['volume_ratio'] > 1.5 or latest['volume_ratio'] < 0.5,
            'volume_signal': None,
            'trend_confirmation': None
        }

        # วิเคราะห์ตำแหน่งเทียบ Bollinger Bands
        if latest_close > stock_data['Upper_Band'].iloc[-1]:
            price_zone['bollinger_position'] = 'above_upper'
        elif latest_close < stock_data['Lower_Band'].iloc[-1]:
            price_zone['bollinger_position'] = 'below_lower'
        else:
            price_zone['bollinger_position'] = 'within_bands'
        
        # วิเคราะห์โซนราคา (ใช้ทั้ง MA200 และ Percentile)
        if (latest_close < stock_data['MA_200'].iloc[-1]) and (percentile < 30):
            price_zone['zone_analysis'] = 'ราคาอยู่ในโซนถูก (Undervalued)'
        elif (latest_close > stock_data['MA_200'].iloc[-1]) and (percentile > 70):
            price_zone['zone_analysis'] = 'ราคาอยู่ในโซนแพง (Overvalued)'
        else:
            price_zone['zone_analysis'] = 'ราคาอยู่ในระดับเหมาะสม (Fair Value)'
        
        # วิเคราะห์แนวโน้มราคาปิดด้วยการถดถอยเชิงเส้น
        X = np.array(range(len(stock_data))).reshape(-1, 1)
        y = stock_data['close'].values
        model = LinearRegression().fit(X, y)
        trend_slope = float(model.coef_[0])

        # วิเคราะห์แนวโน้มราคาสูงสุดด้วยการถดถอยเชิงเส้น
        lookback_days = 10
        recent_data = stock_data.tail(lookback_days)
        x = np.arange(len(recent_data)).reshape(-1, 1)  # index 0 ถึง 19
        y = recent_data['high'].values.reshape(-1, 1)   # ใช้คอลัมน์ High
        model = LinearRegression().fit(x, y)
        trendHighPrice_slope = model.coef_[0][0]  # ค่าความชัน
        intercept = model.intercept_[0]

        if (trendHighPrice_slope > 0.05):
            trendHighPrice_analysis =  'สูงขึ้น'
        elif (trendHighPrice_slope < -0.05):
            trendHighPrice_analysis =  'ต่ำลง'
        else:
            trendHighPrice_analysis =  'คงที่'

        if len(stock_data) < 20:
            return None, "ข้อมูลไม่เพียงพอสำหรับการวิเคราะห์ (ต้องการอย่างน้อย 20 วัน)"
        
        # วิเคราะห์สัญญาณ
        latest_close = float(stock_data['close'].iloc[-1])
        latest_ma5 = float(stock_data['MA_5'].iloc[-1])
        latest_ma20 = float(stock_data['MA_20'].iloc[-1])
        latest_momentum = float(stock_data['Momentum'].iloc[-1])

        # กำหนดสัญญาณปริมาณซื้อขาย
        if latest['volume_ratio'] > 1.5:
            volume_analysis['volume_signal'] = 'ปริมาณเพิ่มขึ้น'
        elif latest['volume_ratio'] < 0.5:
            volume_analysis['volume_signal'] = 'ปริมาณลดลง'
        else:
            volume_analysis['volume_signal'] = 'ปริมาณปกติ'

        # ยืนยันแนวโน้มด้วยปริมาณซื้อขาย
        if (trend_slope > 0) and (latest['volume_ratio'] > 1):
            volume_analysis['trend_confirmation'] = 'แนวโน้มขึ้น'
        elif (trend_slope < 0) and (latest['volume_ratio'] > 1):
            volume_analysis['trend_confirmation'] = 'แนวโน้มลง'
        else:
            volume_analysis['trend_confirmation'] = 'แนวโน้มไม่ชัดเจน'

        # เงื่อนไขการปรับตัวขึ้น
        bullish_conditions = [
            latest_close > latest['ma20'],
            latest['ma5'] > latest['ma20'],
            trend_slope > 0,
            latest_momentum > 0,
            latest['bullish_signal']  # ใช้เฉพาะสัญญาณ Bullish
        ]
        bearish_conditions = [
            latest_close < latest['ma20'],
            latest['ma5'] < latest['ma20'],
            trend_slope < 0,
            latest['bearish_signal'] and latest['candle_pattern'] in ['Bearish Engulfing', 'Evening Star']
        ]
        
        #bullish_score = sum(bullish_conditions)
        bullish_score = calculate_bullish_score(bullish_conditions, latest)
        bearish_score = sum(bearish_conditions)

        # แปลงค่า numpy ใน volume_analysis ก่อนส่งกลับ
        if isinstance(volume_analysis.get('volume_signal'), np.bool_):
            volume_analysis['volume_signal'] = bool(volume_analysis['volume_signal'])
        
        # แปลงค่าใน trend_confirmation
        if isinstance(volume_analysis.get('trend_confirmation'), np.bool_):
            volume_analysis['trend_confirmation'] = bool(volume_analysis['trend_confirmation'])
        
        # แปลงค่าใน abnormal_volume
        if isinstance(volume_analysis.get('abnormal_volume'), np.bool_):
            volume_analysis['abnormal_volume'] = bool(volume_analysis['abnormal_volume'])

        # แปลงค่า numpy ใน price_zone
        for key in price_zone:
            if isinstance(price_zone[key], np.bool_):
                price_zone[key] = bool(price_zone[key])

        # แปลงค่า numpy ใน latest
        for key in latest:
            if isinstance(latest[key], np.bool_):
                latest[key] = bool(latest[key])
        
        #print( 'latest_pattern', latest_pattern)
        candle_analysis = {
            'pattern': latest_pattern,
            'reliability': get_pattern_reliability(latest_pattern),
            'confirmation': ''
        }
        if latest_pattern == 'Piercing Line':
            print( 'Piercing')
            candle_analysis = confirm_piercing_line(stock_data, -1)
            print( candle_analysis)
        elif latest_pattern == 'Tweezer Bottom':
            print( 'Tweezer')
            candle_analysis = confirm_tweezer_bottom(stock_data, -1)
            print( candle_analysis)

        macd_value = stock_data['MACD'].iloc[-1]
        try:
            #chart77 = main(date_col="Date", SYMBOL=ticker) # Predict with ARIMA Model
            #chart77 = plot_chart(date_col="Date", SYMBOL=ticker, tf="W", max_bars=100)
            chart77, summary = detect_combined_signals(SYMBOL=ticker,tf="D",confirm=False)
            #chart78 = plot_chart(date_col="Date", SYMBOL=ticker, tf="1h", max_bars=150)
            chart78, summary1h = detect_combined_signals(SYMBOL=ticker,tf="1h",confirm=False)
            #chart79 = plot_chart(date_col="Date", SYMBOL=ticker, tf="15m", max_bars=150)
            chart79, summary15m = detect_combined_signals(SYMBOL=ticker,tf="15m",confirm=False)
            rsi_status = "-"
            signal = "-"
            if summary1h["RSI"]["signal"] == "Buy":
                rsi_status = summary1h["RSI"]["status"]
                signal = summary1h["RSI"]["signal"]
            elif summary1h["Divergence"]["signal"] == "Buy":
                rsi_status = summary1h["Divergence"]["status"]
                signal = summary1h["Divergence"]["signal"]
            #elif summary["RSI"]["signal"] == "Buy":
            #    rsi_status = summary["RSI"]["status"]
            #    signal = summary["RSI"]["signal"]
            #elif summary["Divergence"]["signal"] == "Buy":
            #    rsi_status = summary["Divergence"]["status"]
            #    signal = summary["Divergence"]["signal"]

            print(f"signal: {ticker} {signal}")
            if signal=="Buy" and isupload == True:
                dropbox_path = f"/chart/{ticker}_chart.png"
                output_path = f"chart/{ticker}_chart.png"
                #upload_base64_image(chart79, dropbox_path)
                upload_combined_base64_images([chart77,chart78,chart79], dropbox_path)
                combined_base64_images([chart77,chart78,chart79], "vertical", output_path)
                print(f"uploaded {ticker}")
        except Exception as e:
            print(f"Error uploading: {e}")

        is_in_watchlist = check_watchlist(ticker)

        # เตรียมผลลัพธ์
        result = {
            #'stock_data': stock_data,  # เพิ่มข้อมูลดิบสำหรับใช้ใน Plotly
            'ticker': ticker,
            'latest_close': round(latest_close, 2) if round(latest_close, 2) else None,
            'previous_close': round(stock_data['close'].iloc[-2], 2),
            'open': round(stock_data['open'].iloc[-1], 2),
            'ma5': round(latest_ma5, 2),
            'ma20': float(round(latest_ma20, 2)),
            'momentum': round(latest_momentum, 2),
            'macd': round(macd_value, 2) if not np.isnan(macd_value) else None,
            'rsi': round(rsi_forecast['current_rsi'], 2),
            'signal': signal,
            'rsi_status': rsi_status,
            'rsi_signal': rsi_forecast['signal'],
            'trend_slope': round(trend_slope, 4),
            'trendHighPrice_analysis': trendHighPrice_analysis,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'trend': 'ขาขึ้น' if trend_slope > 0 else 'ขาลง',
            'price_zone': price_zone,
            'latest': latest,
            'price_change': {
                'absolute': round(stock_data['price_change'].iloc[-1], 2),  # การเปลี่ยนแปลงราคา (บาท)
                'percent': round(stock_data['pct_change'].iloc[-1], 2),     # การเปลี่ยนแปลงราคา (%)
                'direction': 'up' if stock_data['price_change'].iloc[-1] > 0 else 'down',  # ทิศทาง
                'previous_close': round(stock_data['close'].iloc[-2], 2) if round(stock_data['close'].iloc[-2], 2) else None
            },
            'volume_analysis': volume_analysis if volume_analysis else None,
            'candle_pattern': latest_pattern,
            'candle_analysis': candle_analysis if candle_analysis else None,
            'analysis': '',
            'chart77': chart77,
            'chart78': chart78,
            'chart79': chart79,
            'is_in_watchlist': is_in_watchlist,
            'success': True
        }
        
        if bullish_score >= 3:
            result['analysis'] = 'ปรับตัวขึ้น (Bullish)'
        elif bullish_score >= 2:
            result['analysis'] = 'มีโอกาสปรับตัวขึ้น'
        else:
            result['analysis'] = 'ยังไม่มีการปรับตัวขึ้นชัดเจน'

        #print(result)
        return result, None
        
    except Exception as e:
        return None, f"เกิดข้อผิดพลาด: {str(e)}"

def predict_rsi_trend(df, window=5):
    recent_rsi = df['RSI'].tail(window)
    x = np.arange(len(recent_rsi))
    y = recent_rsi.values

    # ใช้ Linear Regression คำนวณแนวโน้ม
    slope, intercept = np.polyfit(x, y, 1)
    direction = "ขาขึ้น ↗" if slope > 0 else "ขาลง ↘"

    # ประเมินความแรงของการเปลี่ยนแปลง
    strength = abs(slope)

    # สร้างข้อความวิเคราะห์
    if slope > 0 and y[-1] < 30:
        signal = "🟢 RSI เริ่มกลับตัวจากเขต Oversold"
    elif slope < 0 and y[-1] > 70:
        signal = "🔴 RSI กำลังอ่อนตัวจาก Overbought"
    else:
        signal = "⚪ RSI เปลี่ยนแปลงปานกลาง"

    return {
        "slope": slope,
        "direction": direction,
        "current_rsi": y[-1],
        "signal": signal
    }

def get_pattern_reliability( pattern):
    reliability_map = {
        'Bullish Pin Bar': 'สูง (High)',
        'Bullish Doji Star': 'ปานกลาง (Medium)',
        'Doji': 'ต่ำ (Low)'
        # ... (รูปแบบอื่นๆ)
    }
    return reliability_map.get(pattern, 'ไม่ทราบ (Unknown)')

def calculate_bullish_score(conditions, latest):
    # เพิ่มพารามิเตอร์เฉพาะสำหรับรูปแบบใหม่
    candle_pattern_weights = {
        'Bullish Pin Bar': 1.2,       # ให้น้ำหนักสูงกว่าเทียนทั่วไป
        'Bullish Doji Star': 1.1,
        'Doji': 0.8,                  # Doji ธรรมดามีน้ำหนักน้อยกว่า
        'Hammer': 1.0,
        'Bullish Engulfing': 1.3,
        'Morning Star': 1.4,
        'Piercing Line': 1.25,  # น้ำหนักสูงกว่า Hammer แต่ต่ำกว่า Engulfing
        'Tweezer Bottom': 1.4  # น้ำหนักสูงเพราะเป็นรูปแบบ 2 แท่ง
    }
    base_score = sum(conditions[:4])  # 4 เงื่อนไขแรก (MA, Momentum, etc.)
    
    # เพิ่มน้ำหนักตามรูปแบบเทียน
    pattern = latest['candle_pattern']
    pattern_weight = candle_pattern_weights.get(pattern, 0.5)
    
    return base_score + pattern_weight * conditions[4]  # conditions[4] คือ bullish_signal

def confirm_piercing_line(stock_data, index):
    current = stock_data.iloc[index]
    prev = stock_data.iloc[index-1]
    confirmations = {
        'volume_increase': bool(current['volume'] > prev['volume'] * 1.2),
        'above_ma20': bool(current['close'] > stock_data['MA_20'].iloc[index]),
        'momentum_positive': bool((current['close'] / stock_data['close'].iloc[index-3] - 1) > 0)
    }
    
    reliability = sum(confirmations.values()) / len(confirmations)  # ค่า 0-1

    return {
        'pattern': 'Piercing Line',
        'reliability': f"{reliability:.0%}",
        'confirmation': confirmations
    }

def confirm_tweezer_bottom(stock_data, index):
    current = stock_data.iloc[index]
    prev1 = stock_data.iloc[index-1]
    
    confirmations = {
        'support_level': bool(current['low'] == prev1['low'])  # ราคาต่ำสุดเท่ากันพอดี
        #'volume_confirmation': current['volume'] > stock_data['Volume_MA_20'].iloc[index],
        #'rsi_oversold': 'rsi' in stock_data.columns and stock_data['RSI'].iloc[index] < 30,
        #'above_ma200': current['close'] > stock_data['MA_200'].iloc[index]
    }
    
    reliability_score = sum(confirmations.values()) / len(confirmations)
    
    return {
        'pattern': 'Tweezer Bottom',
        'reliability': f"{reliability_score:.0%}",
        'confirmation': confirmations
    }

@app.route("/stock_analyze2/", defaults={'ticker': 'PTT'}, methods=['GET', 'POST'])
@app.route('/stock_analyze2/<ticker>', methods=['GET', 'POST'])
def stock_analyze2(ticker=None):

    if is_system_available():
        try:
            investor = Investor(
                            app_id="gnPhUtkuauTPjrqK",
                            app_secret="RW53D4/kib04nDaWLn5qi1DtA3sO/zdXzQSaxGWctbs=",
                            broker_id="023",
                            app_code="ALGO_EQ",
                            is_auto_queue = False)
            equity = investor.Equity(account_no="602068305")
            account_info = equity.get_account_info()
            print("Account Info:", account_info)
            portfolio = equity.get_portfolios()
            mkt_data = investor.MarketData()
            quote_data = mkt_data.get_quote_symbol("AWC")
            return render_template('stock_analyze2.html', account_info=account_info, portfolio=portfolio, quote_data=quote_data)
        except SettradeError as e:
            print("เกิดข้อผิดพลาดจาก Settrade API:", e)
    else:
        print("❌ System Unavailable - กรุณาลองใหม่ภายหลัง")

    return render_template('stock_analyze2.html', ticker=ticker )

from flask import jsonify
import numpy as np
import pandas as pd
import json

@app.route('/analyze_stock_trend2', methods=['POST'])
def analyze_stock_trend2():
    try:
        data = request.get_json()
        
        if not data or 'ticker' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required parameters'
            }), 400
        
        ticker = data.get('ticker')

        # เรียกใช้ฟังก์ชันวิเคราะห์
        result, error = analyze_stock_trend(
            ticker=ticker,
        )
        
        if error:
            return jsonify({
                'success': False,
                'message': error
            }), 400

        # ฟังก์ชันช่วยแปลงค่า numpy/pandas เป็น Python native types
        def convert_to_serializable(obj):
            if isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64)):
                return float(obj)
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, pd.DataFrame):
                return obj.to_dict(orient='records')
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(v) for v in obj]
            else:
                return obj

        # แปลงผลลัพธ์ก่อนส่งกลับ
        serializable_result = convert_to_serializable(result)
        
        Pricepredictor = PricePredictor()
        chart6, error = Pricepredictor.run(symbol=ticker)
        chart7 = main(date_col="Date", SYMBOL=ticker)
        #print('chart6:')
        #print(chart6)

        return jsonify({
            'success': True,
            'data': serializable_result,
            'chart6': chart6,
            'chart7': chart7
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'เกิดข้อผิดพลาด: {str(e)}'
        }), 500

def convert_int64_to_int(data):
    """แปลงค่าทั้งหมดใน dictionary จาก int64 เป็น int"""
    if isinstance(data, dict):
        return {k: int(v) if str(type(v)) == "<class 'numpy.int64'>" else v 
                for k, v in data.items()}
    return data

# ฟังก์ชันช่วยแปลงค่า numpy/pandas เป็น Python native types
def convert_to_serializable2(obj):
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')
    elif isinstance(obj, dict):
        return {k: convert_to_serializable2(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable2(v) for v in obj]
    else:
        return obj

def clean_nan_values(data):
    """
    แปลงค่า NaN/None ในโครงสร้างข้อมูลให้เป็น None พร้อมแปลงประเภทข้อมูล
    """
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(v) for v in data]
    elif pd.isna(data):  # ครอบคลุมทั้ง numpy.nan และ pandas.NA
        return None
    elif isinstance(data, (np.floating, float)):
        return float(data)
    elif isinstance(data, (np.integer, int)):
        return int(data)
    return data

# ฟังก์ชันเรียก API Hugging Face
def summarize_thai(text):
    payload = {"inputs": "th: " + text}
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    
    if response.status_code == 200:
        return response.json()[0]["summary_text"]
    else:
        return f"Error: {response.status_code} - {response.text}"

# Endpoint: POST /summarize
@app.route("/summarize", methods=["POST"])
def summarize_api():
    try:
        data = request.get_json()
        
        # กรณีรับคำขอวิเคราะห์ข้อความทั่วไป
        if "text" in data:
            summary = summarize_thai(data["text"])
            return jsonify({
                "status": "success",
                "summary": summary
            })
        
        # กรณีรับคำขอวิเคราะห์หุ้นทั้งหมด
        elif "analyze_all" in data and data["analyze_all"]:
            all_results = []
            
            set100.sort()
            for ticker in set100:
                result, error = analyze_stock_trend(ticker, isupload=False)
                if not error:
                    result['ticker'] = ticker
                    #all_results.append(result)
                    all_results.append(convert_to_serializable2(result))
            
            return jsonify({
                "status": "success",
                "all_results": all_results
            })
        elif "analyze_watchlist" in data and data["analyze_watchlist"]:
            all_results = []
            
            delete_all_files_in_server("chart")
            clear_dropbox_folder("/chart")
            delete_all_files_in_github("chart")
            watchlist_items = get_user_watchlist()
            for ticker in watchlist_items:
                result, error = analyze_stock_trend(ticker, isupload=True)
                if not error:
                    result['ticker'] = ticker
                    #all_results.append(result)
                    all_results.append(convert_to_serializable2(result))
            build_gallery_page()
            upload_multiple_files_to_github("chart")
            upload_file_to_github("gallery.html", None)

            return jsonify({
                "status": "success",
                "all_results": all_results
            })
        
        else:
            return jsonify({"error": "Invalid request format"}), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/watchlist', methods=['POST'])
def handle_watchlist():
    try:
        data = request.json
        if not data or "ticker" not in data:
            return jsonify({"error": "Missing required fields (ticker)"}), 400
        new_watchlist = SupabaseWatchlist(ticker=data["ticker"])
        db.session.add(new_watchlist)
        db.session.commit()
        return jsonify({"message": "Watchlist added to Supabase DB successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500  # Return the exact error message

@app.route("/render_watchlist")
def render_watchlist():
    try:
        watchlist_items = get_user_watchlist()  # ดึง ticker ทั้งหมด
        all_results = []
        
        for ticker in watchlist_items:
            result, error = analyze_stock_trend(ticker, isupload=False)
            if not error:
                result['ticker'] = ticker
                #predicted_class, confidence = predict_patternAPI(f"images/{ticker}.png")
                #result['predicted_class'] = predicted_class
                all_results.append(convert_to_serializable2(result))
        
        return jsonify({
            "status": "success",
            "all_results": all_results
        })
        #return jsonify(watchlist_items)  # ส่งเป็น JSON array
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/watchlist/<string:ticker>", methods=["DELETE"])
def delete_watchlist_item(ticker):
    try:
        # ถ้า ticker เป็นค่าว่างหรือตัวอักษร "all" -> ลบทั้งหมด
        if not ticker or ticker.strip().lower() == "all":
            deleted = SupabaseWatchlist.query.delete()
            db.session.commit()
            return jsonify({
                "message": f"Deleted all watchlist items ({deleted} records)."
            }), 200

        # กรณีลบเฉพาะ ticker เดียว
        item = SupabaseWatchlist.query.filter_by(ticker=ticker).first()
        if not item:
            return jsonify({"error": "Ticker not found"}), 404

        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": f"Deleted ticker '{ticker}' successfully."}), 200

    except Exception as e:
        db.session.rollback()  # rollback เพื่อความปลอดภัยในกรณี error
        return jsonify({"error": str(e)}), 500

def get_user_watchlist(ticker=None):
    try:
        if ticker:
            item = SupabaseWatchlist.query.filter_by(ticker=ticker).first()
            if item:
                return {
                    "ticker": item.ticker,
                    "created_at": item.created_at.isoformat() if item.created_at else None
                }
            else:
                return None
        else:
            items = SupabaseWatchlist.query.order_by(SupabaseWatchlist.ticker.asc()).all()
            return [item.ticker for item in items] if items else []
    except Exception as e:
        print(f"Error fetching watchlist: {str(e)}")
        return [] if not ticker else None

def check_watchlist(ticker):
    try:
        watchlist = get_user_watchlist(ticker)
        #print('watchlist', watchlist)
        if watchlist is None:  # ไม่เจอ ticker
            return False
        return watchlist.get('ticker') == ticker
    except Exception as e:
        print(f"Error in check_watchlist: {str(e)}")
        return False

def generate_chart(df, symbol):
    plt.figure(figsize=(8, 4))
    plt.plot(df['time'], df['close'], label='Close')
    plt.plot(df['time'], df['RSI'], label='RSI')
    plt.plot(df['time'], df['MACD'], label='MACD')
    plt.title(f'{symbol} Trend')
    plt.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def plot_rsi_with_trend(df, symbol, window=14, trend_window=5):
    # คำนวณ RSI
    df['RSI'] = talib.RSI(df['close'], timeperiod=window)
    
    # ตัดเฉพาะ RSI ล่าสุด (trend window)
    rsi_recent = df['RSI'].tail(trend_window)
    x = np.arange(len(rsi_recent))
    y = rsi_recent.values
    
    # Linear Regression → แนวโน้ม RSI
    slope, intercept = np.polyfit(x, y, 1)
    trend_line = slope * x + intercept

    # Plot RSI + Trend
    plt.figure(figsize=(10, 4))
    plt.plot(df['time'].tail(100), df['RSI'].tail(100), label='RSI', color='blue')
    
    # แนวโน้มวาดทับช่วงท้าย
    recent_time = df['time'].tail(trend_window)
    plt.plot(recent_time, trend_line, label='RSI Trend', linestyle='--', color='red')

    # เส้นแนว Overbought/Oversold
    plt.axhline(70, color='gray', linestyle=':', label='Overbought (70)')
    plt.axhline(30, color='gray', linestyle=':', label='Oversold (30)')

    # แสดงผล
    plt.title(f"RSI & Trend - {symbol}")
    plt.ylabel("RSI Value")
    plt.xlabel("Date")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

def forecast_rsi_current_dates(df, rsi_period=14, forecast_days=3):
    df['RSI'] = talib.RSI(df['close'], timeperiod=rsi_period)
    df = df.dropna()

    # ใช้ RSI ล่าสุด 14 วัน
    recent_df = df.tail(14).reset_index(drop=True)
    recent_dates = recent_df['time']
    recent_rsi = recent_df['RSI']

    # Linear regression
    x = np.arange(len(recent_rsi))
    y = recent_rsi.values
    slope, intercept = np.polyfit(x, y, 1)

    # คาดการณ์วันถัดไป
    future_x = np.arange(len(recent_rsi), len(recent_rsi) + forecast_days)
    future_rsi = slope * future_x + intercept

    # แปลงวันที่สำหรับแกน X
    last_date = recent_dates.iloc[-1]
    future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]

    # รวมวันที่ทั้งหมด
    all_dates = pd.to_datetime(list(recent_dates) + future_dates)

    # รวม RSI ทั้งหมด
    all_rsi = np.concatenate([y, future_rsi])

    # วาดกราฟ
    plt.figure(figsize=(10, 4))
    plt.plot(all_dates[:len(y)], y, label='Actual RSI', marker='o')
    plt.plot(all_dates[len(y):], future_rsi, label='Forecast RSI', linestyle='--', color='red', marker='x')

    # เส้นระดับ RSI
    plt.axhline(70, color='gray', linestyle=':', label='Overbought (70)')
    plt.axhline(30, color='gray', linestyle=':', label='Oversold (30)')

    # ปรับรูปแบบวันที่บนแกน X
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.xticks(rotation=45)

    plt.title("RSI Forecast with Dates")
    plt.xlabel("Date")
    plt.ylabel("RSI")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)
    return future_rsi, base64.b64encode(buf.read()).decode('utf-8')

def forecast_rsi_backward_dates(df, symbol, rsi_period=14, forecast_days=3):
    try:
        # คำนวณ RSI และลบแถวที่มีค่า NaN
        df['RSI'] = talib.RSI(df['close'], timeperiod=rsi_period)
        df = df.dropna()
        
        # แยกข้อมูลจริงล่าสุดไว้สำหรับตรวจสอบ (hold-out)
        actual_holdout = df.tail(forecast_days)
        df_train = df.iloc[:-forecast_days]
        #print("actual_holdout: ", actual_holdout)
        
        # ใช้ RSI ล่าสุด 14 วันจากข้อมูลที่เหลือ (หลังตัด hold-out)
        recent_df = df_train.tail(rsi_period).reset_index(drop=True)
        recent_dates = recent_df['time']
        recent_rsi = recent_df['RSI']
        
        # Linear regression
        x = np.arange(len(recent_rsi))
        y = recent_rsi.values
        slope, intercept = np.polyfit(x, y, 1)
        
        # คาดการณ์ RSI สำหรับวันถัดไป
        future_x = np.arange(len(recent_rsi), len(recent_rsi) + forecast_days)
        future_rsi = slope * future_x + intercept

        trend_direction = "คงที่ ⚪"
        latest_actual_rsi = recent_rsi.iloc[-1]
        if future_rsi[-1] > future_rsi[0] and future_rsi[-1] > latest_actual_rsi:
            trend_direction = "ขาขึ้น ↗"
        elif future_rsi[-1] < future_rsi[0] and future_rsi[-1] < latest_actual_rsi:
            trend_direction = "ขาลง ↘"
        
        # วันที่สำหรับการพยากรณ์
        last_date = recent_dates.iloc[-1]
        future_dates = [last_date + timedelta(days=i) for i in range(1, forecast_days + 1)]
        
        # สร้างกราฟ
        plt.figure(figsize=(12, 6))
        
        # แสดงข้อมูลทั้งหมดเพื่อดูแนวโน้ม
        plt.plot(pd.to_datetime(df['time']), df['RSI'], label='All RSI Data', color='black', alpha=0.3)
        
        # แสดงเฉพาะส่วนที่ใช้คำนวณ RSI (14 วันล่าสุด)
        plt.plot(pd.to_datetime(recent_dates), recent_rsi, 
                label='RSI Calculation Window', color='blue', marker='o')
        
        # แสดงข้อมูล hold-out
        plt.plot(pd.to_datetime(actual_holdout['time']), actual_holdout['RSI'], 
                label='Actual RSI (Hold-out)', color='green', marker='o', linestyle='')
        
        # แสดงการพยากรณ์
        plt.plot(future_dates, future_rsi, label='Forecast RSI', 
                linestyle='--', color='red', marker='x', markersize=8)
        
        # เส้นระดับ RSI
        plt.axhline(70, color='gray', linestyle=':', label='Overbought (70)')
        plt.axhline(30, color='gray', linestyle=':', label='Oversold (30)')
        
        ## ปรับแต่งแกน X ใหม่ ##
        ax = plt.gca()
        
        # กำหนดให้แสดงเฉพาะวันที่ที่เกี่ยวข้อง (14 วันคำนวณ + วันที่พยากรณ์)
        display_dates = list(recent_dates) + future_dates
        ax.set_xlim([pd.to_datetime(recent_dates.iloc[0]) - timedelta(days=1), 
                    pd.to_datetime(future_dates[-1]) + timedelta(days=1)])
        
        # กำหนดรูปแบบวันที่
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))
        
        # กำหนดความถี่ในการแสดงค่าแกน X
        if len(display_dates) > 14:
            interval = max(1, len(display_dates) // 7)  # แสดงประมาณ 7 ค่าในแกน X
        else:
            interval = 1
        
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
        
        # ปรับมุมและตำแหน่งของ label
        plt.xticks(rotation=45, ha='right')
        
        # ปรับแต่งกราฟ
        plt.title(f"{symbol} RSI Forecast ({forecast_days}-day Prediction)", pad=20)
        plt.xlabel("Date", labelpad=10)
        plt.ylabel("RSI", labelpad=10)
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        # บันทึกกราฟ
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        
        # คำนวณความคลาดเคลื่อน
        mae = np.mean(np.abs(future_rsi - actual_holdout['RSI'].values))
        result = {
            'forecast_rsi': future_rsi,
            'actual_rsi': actual_holdout['RSI'].values,
            'mae': mae,
            'chart': base64.b64encode(buf.read()).decode('utf-8'),
            'forecast_dates': actual_holdout['time'].tolist(),
            'rsi_trend': trend_direction
        }

        return result
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def summarize(text):
    payload = {"inputs": "th: " + text}
    r = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    if r.status_code == 200:
        return r.json()[0]["summary_text"]
    return f"เกิดข้อผิดพลาด: {r.status_code}"

def delete_all_files_in_server(folder_name):
    folder_path = os.path.join(os.getcwd(), folder_name)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                # ถ้ามีโฟลเดอร์ย่อย (เช่น chart/subfolder)
                import shutil
                shutil.rmtree(file_path)
                print(f"Deleted folder: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting {file_path}: {e}")

import importlib
import LSTM_rsi_predictor as LSTM_rsi_predictor
importlib.reload(LSTM_rsi_predictor)
import LSTM_price_predictor as LSTM_price_predictor
importlib.reload(LSTM_price_predictor)
from LSTM_rsi_predictor import RSIPredictor
from LSTM_price_predictor import PricePredictor
from ARIMA_price_predictor_with_rsi import main, plot_chart, plot_chart_daily_weekly_side_by_side
from localminima import detect_combined_signals, detect_overbought_oversold, detect_bullish_bearish_divergence, detect_double_bottom

@app.route("/analyze", methods=["POST"])
def analyze():
    symbol = request.json.get("symbol", "").upper()
    try:
        df, err = fetch_stock_data(symbol)
        chart = generate_chart(df, symbol)
        chart2 = plot_rsi_with_trend(df, symbol, window=14, trend_window=5)
        future_rsi, chart3 = forecast_rsi_current_dates(df, rsi_period=14, forecast_days=3)
        chart4 = forecast_rsi_backward_dates(df, symbol, rsi_period=14, forecast_days=3)
        print('symbol: ',symbol)
        RSIpredictor = RSIPredictor(symbol=symbol)
        chart5, error = RSIpredictor.run()
        Pricepredictor = PricePredictor()
        chart6, error = Pricepredictor.run(symbol=symbol)
        chart7 = main(date_col="Date", SYMBOL=symbol)

        rsi = df["RSI"].iloc[-1]
        macd = df["MACD"].iloc[-1]
        summary_text = f"หุ้น {symbol} RSI ล่าสุดคือ {rsi:.2f} และ MACD อยู่ที่ {macd:.2f}"
        summary = summarize(summary_text)

        return jsonify({
            "chart": chart,
            "chart2": chart2,
            "chart3": chart3,
            "chart4": chart4['chart'],
            "chart5": chart5,
            "chart6": chart6,
            "chart7": chart7,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False) #fix error main thread is not in main loop
    #app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=True) #fix class updated not reload
