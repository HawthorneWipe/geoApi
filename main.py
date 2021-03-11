from flask import json
from flask.json import dump
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError, OperationalError
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, jsonify, render_template, request
import requests
from dotenv import load_dotenv
import os
from urllib.parse import urlparse
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
load_dotenv()
app = Flask(__name__)
GEO_API_KEY = os.getenv('SECRET_GEO_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 'sqlite:///Persons.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False
app.secret_key = os.getenv('SECRET_FLASK_KEY')
db = SQLAlchemy(app)
jwt = JWTManager(app)


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(250), nullable=False)
    lat = db.Column(db.String(250), nullable=False)
    lon = db.Column(db.String(250), nullable=False)


class PersonSerializer(SQLAlchemyAutoSchema):
    class Meta:
        model = Person
        load_instance = True


db.create_all()


@app.route("/auth", methods=["POST"])
def login():
    if request.is_json:
        username = request.json.get("username", None)
        password = request.json.get("password", None)
        if username != "Gill Gillenhall" or password != "passwordpassword123passwordpassword":
            return jsonify({"Message": "Bad username or password"}), 401
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)

    else:
        return jsonify({"Message": "Make sure you are using JSON payload"}), 400


@app.route('/geolocateme', methods=['GET'])
@jwt_required()
def geolocateme():
    param = {
        'access_key': GEO_API_KEY,
        'output': 'json'
    }
    try:
        #! The API returns data even if the IP or domain are invalid, just check for field == null for now.
        #! Might use validators.ipv4(request.args.get("url")):
        response = requests.get(
            url='http://api.ipstack.com/check', params=param)
        response.raise_for_status()
        if response.json()['city'] == None:
            raise Exception("Returned Null")
    except:
        return jsonify({'Message': 'Could not connect to the ipstack or data not found'}), 401
    return response.json(), 200


@app.route('/geolocateAdd', methods=['GET'])
@jwt_required()
def geolocate():
    param = {
        'access_key': GEO_API_KEY,
        'output': 'json'
    }
    if request.is_json:
        if "url" not in request.json:
            return jsonify({"Message": "'url' key missing in the request"}), 400
        else:
            try:
                #! The API returns data even if the IP or domain are invalid, just check for field == null for now.
                #! Might use validators.ipv4(request.args.get("url")):
                response = requests.get(
                    url='http://api.ipstack.com/'+str(request.json.get("url")), params=param)
                response.raise_for_status()
                if response.json()['city'] == None:
                    raise Exception("Not a valid url or IP")
                else:
                    try:
                        person_create = Person(url=response.json()['ip'], lat=response.json()[
                            'latitude'], lon=response.json()['longitude'])
                        db.session.add(person_create)
                        db.session.commit()
                    except:
                        return jsonify({'Message': 'Failed to connect to the database'}), 503
                return response.json(), 200
            except Exception as e:
                print(e)
                return jsonify({'Message': f'{e}'}), 400
    else:
        return jsonify({"Message": "Make sure you are using JSON payload"}), 400


@app.route('/geolocateall', methods=['GET'])
@jwt_required()
def all_cafes():
    try:
        Persons = Person.query.all()
        if Persons == []:
            raise Exception
        visits = PersonSerializer()
        return jsonify(Visits=[visits.dump(person) for person in Persons])
    except Exception as e:
        # print(e)
        return jsonify({"Message": "Could not retrieve from database"})

    # # HTTP DELETE - Delete Record


@app.route('/geolocateRemove', methods=['DELETE'])
def delete_cafe():
    if request.is_json:
        if 'visit' not in request.json:
            return jsonify({"Message":
                            "No 'visit' in request keys. Go to /geolocateall and add JSON payload in form of {'visit': 'id number'}"})
        try:
            delete_entry = db.session.query(Person).filter(
                Person.id == request.json.get('visit')).one()
        except Exception as e:
            return jsonify({"Error": "Could not read from database"})
        else:
            try:
                ip = delete_entry.url
                db.session.delete(delete_entry)
                db.session.flush()
                db.session.commit()
                return jsonify({"message": f"Deleted entry {ip}"})
            except Exception as e:
                return jsonify({"Error": "Could not delete from the database"}), 404
    else:
        return jsonify({"Message": "Make sure you are using JSON payload"}), 400


if __name__ == '__main__':
    app.run()
