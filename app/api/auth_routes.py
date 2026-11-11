from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.models.user import User
from app.schemas.user_schema import RegisterSchema, LoginSchema, UserResponseSchema
from app.services.auth_service import AuthService
from app.services.email_service import EmailService

auth_ns = Namespace('auth', description='User authentication and registration')

# Swagger models
register_model = auth_ns.model('Register', {
    'email': fields.String(required=True, description='User email address', example='you@email.com'),
    'password': fields.String(required=True, description='Password (min 6 chars)', example='password123'),
    'name': fields.String(required=True, description='Full name', example='Aswin Kumar'),
})

login_model = auth_ns.model('Login', {
    'email': fields.String(required=True, description='User email address', example='you@email.com'),
    'password': fields.String(required=True, description='Password', example='password123'),
})

@auth_ns.route('/register')
class RegisterResource(Resource):
    @auth_ns.expect(register_model, validate=False)
    @auth_ns.doc(responses={201: 'User created', 400: 'Validation error', 409: 'Email already exists'})
    def post(self):
        schema = RegisterSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 400

        # Check existing user
        if User.objects(email=data["email"].lower()).first():
            return {"error": "Email is already registered."}, 409

        password_hash = AuthService.hash_password(data["password"])
        user = User(
            email=data["email"].lower().strip(),
            name=data["name"].strip(),
            password_hash=password_hash
        )
        user.save()

        # Send welcome email asynchronously
        EmailService.send_welcome_email(user.email, user.name)

        # Generate JWT
        token = AuthService.generate_token(user)

        return {
            "message": "User registered successfully! Welcome email sent.",
            "token": token,
            "user": user.to_dict()
        }, 201

@auth_ns.route('/login')
class LoginResource(Resource):
    @auth_ns.expect(login_model, validate=False)
    @auth_ns.doc(responses={200: 'Login successful', 400: 'Validation error', 401: 'Invalid credentials'})
    def post(self):
        schema = LoginSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 400

        user = User.objects(email=data["email"].lower().strip()).first()
        if not user or not AuthService.verify_password(data["password"], user.password_hash):
            return {"error": "Invalid email or password."}, 401

        token = AuthService.generate_token(user)
        return {
            "message": "Login successful",
            "token": token,
            "user": user.to_dict()
        }, 200

@auth_ns.route('/me')
class MeResource(Resource):
    @jwt_required()
    @auth_ns.doc(security='Bearer Auth')
    def get(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {"error": "User not found."}, 404
        return {"user": user.to_dict()}, 200

