from flask import Flask, request, render_template, make_response
from flask_restx import Api, Resource, reqparse
from dotenv import load_dotenv
import os
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from celery import Celery
from celery.result import AsyncResult
from textmsg import SendOtp
import random

from error_codes import error

from mailer import SendMail
load_dotenv()

DB_PATH = os.getenv('SQL_ALCHEMY_URI')
CELERY_BROKER_URLL= os.getenv('CELERY_BROKER_URL')
CELERY_RESULT_BACKENDD= os.getenv('CELERY_RESULT_BACKEND')


app = Flask(__name__)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = "{}".format(DB_PATH)
app.config['CELERY_BROKER_URL']='{}'.format(CELERY_BROKER_URLL)
app.config['CELERY_RESULT_BACKEND']='{}'.format(CELERY_RESULT_BACKENDD)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


################ Models ##################
db = SQLAlchemy(app)
marsh = Marshmallow(app)

class Users(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(50),nullable=False)
    email = db.Column(db.String(50),nullable=False,unique=True)
    password = db.Column(db.String,nullable=False)

    def __init__(self,username,password,email):
        self.username = username
        self.password = password
        self.email = email
    
class UserSchema(marsh.Schema):
    class Meta:
        fields = ('username','email')
    
singleUser = UserSchema()
multiUser = UserSchema(many=True)


api = Api(app)

@api.route('/home')
class Home(Resource):
    def get(self):
        return 'Helloo!'

# parsers
signup_parser = reqparse.RequestParser()
signup_parser.add_argument('username',type=str,required=True)
signup_parser.add_argument('password',type=str,required=True)
signup_parser.add_argument('email',type=str,required=True)

@api.route('/signup')
class Signup(Resource):
    @api.expect(signup_parser)
    def post(self):
        args = signup_parser.parse_args()
        username = args['username']
        password = generate_password_hash(args['password'])
        email = args['email']

        newUser = Users(username=username, password=password,email=email)
        
        db.session.add(newUser)
        db.session.commit()

        return singleUser.jsonify(newUser)



@api.route('/send/<username>')
class SendEmailRoute(Resource):
    def get(self, username):
        if Users.query.filter_by(username=username).count():
            user = Users.query.filter_by(username=username).first()
            doc = (render_template('email.html', user=user))
            x = sendemail.delay(username,doc)
            res = celery.AsyncResult(x.task_id).state
            # print(res)
            return {
                "task_id":x.task_id,
                "description":"msg sent",
                "result":res
            }

        else:
            return ({"Error":error['404'],"Description": "User not found"}), 404


@celery.task(name="flask_app.sendemail",bind=True)
def sendemail(self,username,doc):
    try:
        user = Users.query.filter_by(username=username).first()
        SendMail.delay(user.email, doc)
    except Exception as exc:
        self.retry(exc,countdown=10)

@api.route('/<task_id>')
class result(Resource):
    def get(self,task_id):
        return celery.AsyncResult(task_id).state

@api.route('/sendOtp/<int:number>')
class SendOTP(Resource):
    def get(self,number):
        otp = random.randint(1000,9999)
        x=sendOTP.delay(otp,number)
        res = celery.AsyncResult(x.task_id).state
            # print(res)
        return {
            "task_id":x.task_id,
            "description":"msg sent",
            "result":res
        }

@celery.task(name='flask_app.sendtp',bind=True)
def sendOTP(self,otp,number):
    try:
        SendOtp(otp,number)
    except Exception as exc:
        self.retry(exc,countdown=10)

if __name__ == '__main__':
    app.run(debug=True)