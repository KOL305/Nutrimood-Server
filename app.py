from functools import wraps
import math
from bson.objectid import ObjectId
from flask import Flask, render_template, jsonify, request, redirect, session, abort, flash
from flask_pymongo import PyMongo
from flask_session import Session
from passlib.hash import pbkdf2_sha256
import pymongo
import jwt
from config import Config, db
import datetime

app = Flask("Congressional App Challenge")
app.config.from_object(Config)
Session(app)

# Returns a token string that contains user_id and expiration time
def create_token(id):
    time_limit = datetime.datetime.utcnow() + datetime.timedelta(days=0, seconds=900)
    payload = {"user_id": id, "exp": time_limit}
    print(payload)
    token = jwt.encode(
        payload,
        app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )
    return token

# If error returns a message, if correct returns user_id taken from token
def verify_token(token):
    print(token)
    try:
        payload = jwt.decode(token, app.config.get('SECRET_KEY'), algorithms=['HS256'])
        return {"error": "0", "token": str(payload['user_id'])}
    except jwt.ExpiredSignatureError:
        return {"error": "1", "message": "Signature expired. Please log in again."}
    except jwt.InvalidTokenError:
        return {"error": "2", "message": "Invalid token. Please log in again."}

@app.route('/', methods=['GET'])
def testing():
    today = datetime.date.today().strftime("%m-%d-%Y") # May need to change based format from /getjournal date request
    print(today)
    return ""

@app.route('/auth/token', methods=['POST'])
def auth_verify_token():
    token = request.args.get('token')
    session_token = verify_token(str(session["logged_in_token"]))
    result = verify_token(token)
    if result["error"] == "0":
        if session_token == result["token"]:
            return {"error": "0", "message": "Correct Token"}
        else:
            return {"error": "3", "message": "Incorrect token. Please log in again."}
    else:
        return result

@app.route('/api/login', methods=['POST'])
def api_login():
    users = db['users']

    # Gets data from login form
    username = request.get_json().get('name')
    password = request.get_json().get('password')

    print(username)
    print(password)

    user = users.find_one({'username': username})

    # Checking if successful login
    if user != None and pbkdf2_sha256.verify(password, user['password_hash']):
        # Updating Token and Session
        token = create_token(str(user['_id']))
        session['logged_in'] = True
        session['logged_in_id'] = str(user['_id'])
        session['logged_in_token'] = str(token)

        return jsonify({"error": "0", "message": "Login Successful", "token": token})
    else:
        return jsonify({"error": "1", "message": "Invalid login info"})

@app.route('/api/signup', methods=['POST'])
def api_register():

    users = db['users']

    # Gets data from registration form
    username = request.get_json().get('name')
    email = request.get_json().get('email')
    password = request.get_json().get('password')
    height = int(request.get_json().get('height'))
    weight = int(request.get_json().get('weight'))
    water_goal = int(request.get_json().get('watergoal'))
    gender = request.get_json().get('gender')
    birth_date = request.get_json().get('day')
    birth_month = request.get_json().get('month')
    birth_year = request.get_json().get('year')

    birthday_string = (birth_year+"-"+birth_month+"-"+birth_date).strip()

    # Determining Age
    birthday = datetime.datetime.strptime(birthday_string, "%Y-%m-%d")
    today = datetime.datetime.today()
    age = math.floor(int(str(today-birthday).split(" ")[0])/365)

    # Calculating other metrics
    calorie_goal = 0
    if gender == "male":
        calorie_goal = math.floor((10 * weight) + (6.25 * height) - (5 * age) + 5)
    elif gender == "female":
        calorie_goal = math.floor((10 * weight) + (6.25 * height) - (5 * age) - 161)
    # In grams
    protein_goal = math.floor(weight * 0.36)
    lipid_goal = math.floor((calorie_goal * 0.30)/9)
    carbohydrate_goal = math.floor(calorie_goal/8)

    # Creating a user to add to database
    metrics = {
        "height": height,
        "weight": weight,
        "gender": gender,
        "birthday": birthday_string,
    }
    goals = {
        "water": water_goal,
        "calorie": calorie_goal,
        "protein": protein_goal,
        "lipid": lipid_goal,
        "carbohydrate": carbohydrate_goal,
    }
    newUser = {
        "username": username,
        "email": email,
        "password_hash": pbkdf2_sha256.hash(password),
        "metrics": metrics,
        "goals": goals,
        "journal": {},
        "pet": "",
    }

    if users.find_one({'username': username, 'email': email}) is None:
        users.insert_one(newUser)
        
        # Updating session and creating token
        user = users.find_one({'username': username})
        
        token = create_token(str(user['_id']))

        session['logged_in'] = True
        session['logged_in_id'] = str(user['_id'])
        session['logged_in_token'] = str(token)

        return jsonify({"error": "0", "message": "Account Successfully Created", "token": token})
    else:
        return jsonify({"error": "1", "message": "This username and email combination has already been taken"})

@app.route('/api/addfood', methods=['POST'])
def api_add_to_journal():
    users = db['users']
    user = users.find_one({'_id': ObjectId(session['logged_in_id'])})
    journal = user["journal"]

    today = datetime.date.today().strftime("%Y-%m-%d").split("-") # May need to change based format from /getjournal date request
    food = request.args.get('food')
    servings = request.args.get('servings')
    meal = request.args.get('meal')

    ## HOW DO I SORT AND STORE THE JOURNAL ##

    users.update_one({'_id': ObjectId(session['logged_in_id'])},{
        '$set': {'journal': journal}
    })

@app.route('/api/getjournal', methods=['GET'])
def api_get_journal():    
    users = db['users']
    date = request.args.get('date')
    user = users.find_one({'_id': ObjectId(session['logged_in_id'])})
    try:
        journal = user["journal"][str(date)]
        return jsonify({"error": "0", "journal": journal})
    except:
        return jsonify({"error": "1", "message": "No journal for this date"})

@app.route('/api/getdashboard', methods=['GET'])
def api_get_dashboard_info():
    users = db['users']
    user = users.find_one({'_id': ObjectId(session['logged_in_id'])})
    today = datetime.date.today().strftime("%m-%d-%Y") # May need to change based format from /getjournal date request
    today = datetime.date.today().strftime("%Y-%m-%d").split("-") # May need to change based format from /getjournal date request

    journal = user["journal"][str(today)]

    ## HOW DO I SORT AND STORE THE JOURNAL ##

    return jsonify({"goals": user["goals"], "journal": journal})

if __name__ == "__main__":
    app.config['SECRET_KEY'] = '123qwi34iWge9era89F1393h3gwJ0q3'
    app.run(debug=True, host="127.0.0.1", port=8000,)