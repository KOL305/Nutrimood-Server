from functools import wraps
import math
from operator import itemgetter
from bson.objectid import ObjectId
from flask import Flask, render_template, jsonify, request, redirect, session, abort, flash
from flask_pymongo import PyMongo
from flask_session import Session
from passlib.hash import pbkdf2_sha256
import pymongo
import jwt
from config import Config, db
import datetime
import uuid

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
        "last_miss": today.strftime("%m-%d-%Y"),
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
    value = request.headers.get('authorization')
    verify = verify_token(value)
    if verify["error"] != "0":
        return jsonify({"error": verify["error"], "message": verify["message"]})
    user_id = verify["token"]

    users = db['users']
    user = users.find_one({'_id': ObjectId(user_id)})
    journal = user["journal"]

    print("Journal")
    print(journal)

    today = datetime.date.today().strftime("%m-%d-%Y") # May need to change based format from /getjournal date request
    food = request.get_json().get('food')
    servings = request.get_json().get('servings')
    meal = request.get_json().get('meal')

    if meal == "Breakfast":
        meal_index = 0
    elif meal == "Lunch":
        meal_index = 1
    elif meal == "Dinner":
        meal_index = 2
    elif meal == "Snack":
        meal_index = 3
    elif meal == "Water":
        meal_index = 4

    if today not in journal:
        journal[today] = []

    # Saves each food in a journal with keys: description<str>, brand<str>, ingredients<str>, nutrients<dict>, servings<int>, meal<str>
    nutrients = {}
    nutrients["energy"] = {"amount": 0, "unit": "KCAL"}
    nutrients["protein"] = {"amount": 0, "unit": "G"}
    nutrients["total lipid (fat)"] = {"amount": 0, "unit": "G"}
    nutrients["carbohydrate, by difference"] = {"amount": 0, "unit": "G"}
    for nutrient in food['foodNutrients']:
        nutrients[str(nutrient['nutrientName'].lower())] = {"amount": nutrient['value'], "unit": nutrient['unitName']}
    food_data = {
        "description": food['lowercaseDescription'],
        "brand": food['brandOwner'],
        "ingredients": food['ingredients'],
        "nutrients": nutrients,
        "servings": servings,
        "serving_size": food['servingSize'],
        "serving_units": food['servingSizeUnit'],
        "meal": meal,
        "meal_index": meal_index,
        }
    journal[today].append(food_data)

    users.update_one({'_id': ObjectId(user_id)},{
        '$set': {'journal': journal}
    })
    return jsonify({"error": "0", "message": "Food Successfully Added"})

@app.route('/api/getjournal', methods=['GET'])
def api_get_journal():
    users = db['users']
    value = request.headers.get('authorization')
    verify = verify_token(value)
    if verify["error"] != "0":
        return jsonify({"error": verify["error"], "message": verify["message"]})
    user_id = verify_token(value)["token"]
    user = users.find_one({'_id': ObjectId(user_id)})

    date = request.args.get('date')

    print(date)

    foods = []
    try:
        journal = user["journal"][str(date)]
        print(journal)
        for food in journal:
            name = food["description"]
            servings = food["servings"]
            calories = round(food["nutrients"]["energy"]["amount"]*servings)
            meal = food["meal"]
            meal_index = food["meal_index"]
            foods.append({"name": name, "calories": calories, "servings": servings, "meal": meal, "meal_index": meal_index})
        print(foods)
        try:
            foods_sorted = sorted(foods, key=itemgetter('meal_index'), reverse=True)
            return jsonify({"error": "0", "journal": foods_sorted})
        except:
            return jsonify({"error": "0", "journal": foods})
        print(foods) 
        
    except:
        print("hello")
        return jsonify({"error": "-1", "message": "No journal for this date"})

@app.route('/api/getdashboard', methods=['GET'])
def api_get_dashboard_info():
    today = datetime.datetime.today().strftime("%m-%d-%Y")
    users = db['users']
    value = request.headers.get('authorization')

    verify = verify_token(value)
    if verify["error"] != "0":
        return jsonify({"error": verify["error"], "message": verify["message"]})
    user_id = verify_token(value)["token"]
    user = users.find_one({'_id': ObjectId(user_id)})

    protein = 0
    lipid = 0
    carbohydrate = 0
    energy = 0
    water = 0

    goals = user["goals"]

    journal = {}
    try:
        journal = user["journal"][str(today)]
        for food in journal:
            nutrient_list = food["nutrients"]
            servings = food["servings"]
            protein += nutrient_list["protein"]["amount"]*servings
            lipid += nutrient_list["total lipid (fat)"]["amount"]*servings
            carbohydrate += nutrient_list["carbohydrate, by difference"]["amount"]*servings
            energy += nutrient_list["energy"]["amount"]*servings
            if food["meal"] == "Water":
                water += food["serving_size"]*servings
            print(nutrient_list)
            print(servings)
    except:
        pass

    entries = {"Calories": round(energy/goals["calorie"],2), "Proteins": round(protein/goals["protein"],2), "Fat": round(lipid/goals["lipid"],2), "Carbs": round(carbohydrate/goals["carbohydrate"],2), "Water": round(water/goals["water"],2)}

    # Determining Day
    last_miss = datetime.datetime.strptime(user["last_miss"], "%m-%d-%Y")
    
    today = datetime.datetime.today().strftime("%m-%d-%Y")
    today = datetime.datetime.strptime(today, "%m-%d-%Y")
    yesterday = (datetime.datetime.today() - datetime.timedelta(days = 1)).strftime("%m-%d-%Y").split(" ")[0]

    day = str(today-last_miss)
    if "day" in day:
        day = str(int(day.split(" ")[0])+1)
    else:
        day = "1"

    print(yesterday)

    last_journal = {}
    last_protein = 0
    last_lipid = 0
    last_carbohydrate = 0
    last_energy = 0
    last_water = 0
    try:
        last_journal = user["journal"][str(yesterday)]
        print(last_journal)
        for food in last_journal:
            nutrient_list = food["nutrients"]
            servings = food["servings"]
            last_protein += nutrient_list["protein"]["amount"]*servings
            last_lipid += nutrient_list["total lipid (fat)"]["amount"]*servings
            last_carbohydrate += nutrient_list["carbohydrate, by difference"]["amount"]*servings
            last_energy += nutrient_list["energy"]["amount"]*servings
            if food["meal"] == "Water":
                last_water += food["serving_size"]*servings
            print(nutrient_list)
            print(servings)

        last_entries = {"Calories": round(last_energy/goals["calorie"],2), "Proteins": round(last_protein/goals["protein"],2), "Fat": round(last_lipid/goals["lipid"],2), "Carbs": round(last_carbohydrate/goals["carbohydrate"],2), "Water": round(last_water/goals["water"],2)}

        average = (last_entries['Calories']+ last_entries['Proteins']+last_entries['Carbs']+last_entries['Fat'])/4
        if average <= .3 or average >= 1.7:
            print(last_miss)
            users.update_one({'_id': ObjectId(user_id)},{
                '$set': {'last_miss': today.strftime("%m-%d-%Y")}
            })
            day = "1"
    except:
        pass

    return jsonify({"error": "0", "entries": entries, "day": day})

@app.route('/api/logout', methods=["GET"])
def api_logout():
    session['logged_in'] = False
    session['logged_in_id'] = ''
    session['logged_in_token'] = ''

if __name__ == "__main__":
    app.config['SECRET_KEY'] = '123qwi34iWge9era89F1393h3gwJ0q3'
    app.run(debug=True, host="127.0.0.1", port=8000,)