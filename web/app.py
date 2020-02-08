from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.ImageRecognition
users = db["Users"]

def userExist(username):
    if users.find({'Username': username}).count() == 0:
        return False
    else:
        return True

class Register(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']

        if userExist(username):
            retJson = {
                'status': 301,
                'message': 'Invalid Username'
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 4
        })

        retJson = {
            'status': 200,
            'message': "You've registered successfully"
        }
        return jsonify(retJson)

def verify_pw(username, password):
    if not userExist(username):
        return False
    hashed_pw = users.find({
        'Username': username
    })[0]['Password']

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def generateReturnDictionary(status, message):
    retJson = {
        "status": status,
        "message": message
    }
    return retJson

def verifyCredentials(username, password):
    if not userExist(username):
        return generateReturnDictionary(301, 'Invalid Username'), True

    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return generateReturnDictionary(302, 'Invalid Password'), True

    return None, False
class classify(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['password']
        url = postedData['url']

        retJson, error = verifyCredentials(username, password)

        if error:
            return jsonify(retJson)

        tokens = users.find({
            "Username": username
        })[0]["Tokens"]

        if tokens <= 0:
            return jsonify( generateReturnDictionary(303, 'Not Enough Tokens!') )

        r = requests.get(url)
        retJson = {}

        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            proc = subprocess.Popen('python classify_image.py --model_dir=. --image_file=./temp.jpg')
            proc.communicate()[0]
            proc.wait()
            with open("text.txt") as g:
                retJson = json.load(g)

        users.update({
            "Username": username
        }, {
            "$set":{
                "Tokens": tokens - 1
            }
        })
        return jsonify(retJson)

class Refill(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData['username']
        password = postedData['admin_pw']
        amount = postedData['amount']

        if not userExist(username):
            return jsonify(generateReturnDictionary(301, 'Invalid Username'))
        correct_pw = '123abc'

        if not password == correct_pw:
            return jsonify(generateReturnDictionary(302, 'invalid Password'))

        users.update({
            'Username': username,
        }, {
            "$set" :{
                "Tokens": amount
            }
        })
        return jsonify(generateReturnDictionary(200, 'Token Refilled successfully'))


api.add_resource(Register, '/register')
api.add_resource(classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__ == "__main__":
    app.run(host='0.0.0.0')
