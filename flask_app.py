from flask import Flask, request, render_template, make_response
from flask_restx import Api, Resource, reqparse, Namespace
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
from time import time, sleep

from error_codes import error

#for caching 
from caching import cached

#for parsers
from parsers import signup_parser, login_parser, OtpLogin

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
    contact_number = db.Column(db.String,nullable=False)
    otp = db.Column(db.String,nullable=True)
    otp_released_time = db.Column(db.FLOAT(precision=15), nullable=True)

    def __init__(self,username,password,email,contact_number):
        self.username = username
        self.password = password
        self.email = email
        self.contact_number = contact_number

class UserSchema(marsh.Schema):
    class Meta:
        fields = ('username','email','contact_number')
    
singleUser = UserSchema()
multiUser = UserSchema(many=True)

class UsersV2(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    firstname = db.Column(db.String(50),nullable=False)
    lastname = db.Column(db.String(50),nullable=False)
    email = db.Column(db.String(50),nullable=False,unique=True)
    password = db.Column(db.String,nullable=False)
    contact_number = db.Column(db.String,nullable=False)
    otp = db.Column(db.String,nullable=True)
    otp_released_time = db.Column(db.FLOAT(precision=15), nullable=True)

    def __init__(self,firstname,lastname,password,email,contact_number):
        self.firstname = firstname
        self.lastname = lastname
        self.password = password
        self.email = email
        self.contact_number = contact_number

class UserSchema(marsh.Schema):
    class Meta:
        fields = ('firstname','lastname','email','contact_number')
    
singleUserv2 = UserSchema()

# api = Api(app)
mainapi = Api(app)
api= Namespace('version1',description='v1')
apiv2= Namespace('version2',description='v2')

mainapi.add_namespace(api,path='/v1')
mainapi.add_namespace(apiv2,path='/v2')

@apiv2.route('/home')
@api.route('/home')
class Home(Resource):
    def get(self):
        return 'Helloo! This is a common route for all versions'

'''' version 1 '''
@api.route('/signup')
class Signup(Resource):
    @api.expect(signup_parser)
    def post(self):
        args = signup_parser.parse_args()
        username = args['username']
        password = generate_password_hash(args['password'])
        email = args['email']
        contact_number = args['contact_number']

        newUser = Users(username=username, password=password,email=email,contact_number=contact_number)
        
        db.session.add(newUser)
        db.session.commit()

        return singleUser.jsonify(newUser)

'''' version 1 '''
@api.route("/login")
class Login(Resource):
    def get(self):
        args = login_parser.parse_args()
        email = args["email"]
        password = args["password"]
        if Users.query.filter_by(email=email).count()==0:
            return {
                'msg':'No User found'
            },404
        targetUser = Users.query.filter_by(email=email).first()
        if check_password_hash(password,targetUser.password):
            return {
                "msg":'Invalid password'
            },404
        genrated_otp = random.randint(1000,9999)
        targetUser.otp = genrated_otp
        targetUser.otp_released_time = time()
        db.session.commit()
        x=sendOTP.delay(genrated_otp,targetUser.contact_number)
        res = celery.AsyncResult(x.task_id).state
        return {
            "task_id":x.task_id,
            "description":"otp Sent successfully on your registered contact number",
            "result":res
        },200
'''' version 1 '''
@api.route('/loginOtp')
class LoginOtp(Resource):
    def get(self):
        args = OtpLogin.parse_args()
        email = args["email"]
        entered_otp = args["otp"]
        targetUser = Users.query.filter_by(email)
        if targetUser.otp == entered_otp:
            return {
                "Description":"Logged in successfully"
            },200
        else:
            return {
                "Description":"otp invalid"
            },400

'''' version 1 '''
@celery.task(name='flask_app.sendotp',bind=True)
def sendOTP(self,otp,number):
    try:
        SendOtp(otp,number)
    except Exception as exc:
        self.retry(exc,countdown=10)

'''' version 1 '''
@celery.task(name="flask_app.sendemail",bind=True)
def sendemail(self,username,doc):
    try:
        user = Users.query.filter_by(username=username).first()
        SendMail(user.email, doc)
    except Exception as exc:
        self.retry(exc,countdown=10)

'''' version 1 '''
@api.route('/<task_id>')
class result(Resource):
    def get(self,task_id):
        return celery.AsyncResult(task_id).state

'''' version 2 '''
@apiv2.route('/signup')
class Signup(Resource):
    @api.expect(signup_parser)
    def post(self):
        args = signup_parser.parse_args()
        username = list(args['username'].split(" "))
        firstname = username[0]
        lastname = username[1]
        password = generate_password_hash(args['password'])
        email = args['email']
        contact_number = args['contact_number']

        newUser_V2 = UsersV2(firstname=firstname, lastname=lastname, password=password,email=email,contact_number=contact_number)
        newUser_V1 = Users(username = "".join(username), email = email, contact_number = contact_number,password = password)

        db.session.add(newUser_V2)
        db.session.add(newUser_V1)
        db.session.commit()

        return singleUserv2.jsonify(newUser_V2)


'''' Common routes for both versions of api'''

@api.route('/sendMail/<username>')
class SendEmailRoute(Resource):
    def get(self, username):
        if Users.query.filter_by(username=username).count():
            user = Users.query.filter_by(username=username).first()
            doc = (render_template('email.html', user=user))
            x = sendemail.delay(username,doc)
            res = celery.AsyncResult(x.task_id).state
            return {
                "task_id":x.task_id,
                "description":"msg sent",
                "result":res
            }

        else:
            return ({"Error":error['404'],"Description": "User not found"}), 404



@api.route('/sendOtp/<username>')
class SendOTP(Resource):
    def get(self,username):
        if Users.query.filter_by(username=username).count():
            user = Users.query.filter_by(username=username).first()
            number = user.contact_number
            generated_otp = random.randint(1000,9999)
            user.otp = generated_otp
            x=sendOTP.delay(generated_otp,number)
            res = celery.AsyncResult(x.task_id).state
            return {
                "task_id":x.task_id,
                "description":"Otp sent",
                "result":res
            }
        return {
            'ERROR':"FORBIDDEN",
            'DESCRIPTION':'NO USER FOUND WITH ENTERED CRED'
        },404

@api.route('/get/<username>')
class TestingCache(Resource):
    @cached
    def get(self,username):
        sleep(5)
        if Users.query.filter_by(username=username).count==0:
            targetUser= Users.query.filter_by(username=username).first()
            return {
                'username':username,
                'email':targetUser.email,

            }
        return {
            "msg":"No user with username"
        }

if __name__ == '__main__':
    app.run(debug=True)