from functools import wraps
from bson.objectid import ObjectId
from flask import Flask, render_template, jsonify, request, redirect, session, abort, flash
from flask_pymongo import PyMongo
from flask_session import Session
from passlib.hash import pbkdf2_sha256
import pymongo
from config import Config, db

app = Flask("Congressional App Challenge")
app.config.from_object(Config)
Session(app)

# def login_required(something):
#     @wraps(something)
#     def wrap_login(*args, **kwargs):
#         if 'logged_in' in session and session["logged_in"]:
#             return something(session['logged_in_id'], *args, **kwargs)
#         else:
#             flash("Please Sign In First", category="danger")
#             return redirect('/')
#     return wrap_login

@app.route('/api/login', methods=['POST'])
def login():
    username = request.args.get('username')
    password = request.args.get('password')

@app.route('/api/register', methods=['POST'])
def register():  
    username = request.args.get('username')
    password = request.args.get('password')
    confirm_password = request.args.get('confirmpassword')
    height = request.args.get('height')
    weight = request.args.get('weight')
    gender = request.args.get('gender')
    birthday = request.args.get('birthday')

@app.route('/api/addfood', methods=['POST'])
def add_to_journal():
    food = request.args.get('food')
    servings = request.args.get('servings')
    meal = request.args.get('meal')

@app.route('/api/getjournal', methods=['GET'])
def get_journal():    
    pass

@app.route('/api/getdashboard', methods=['GET'])
def get_dashboard_info():
    pass

if __name__ == "__main__":
    app.config['SECRET_KEY'] = '123qwi34iWge9era89F1393h3gwJ0q3'
    app.run(debug=True)