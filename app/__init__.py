import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from mongoengine import connect, disconnect
from app.config import Config
from app.api import api_bp

jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for React Native / mobile clients
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize JWT
    jwt.init_app(app)

    # JWT Error handlers for clean JSON responses
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({"error": "Missing or invalid authorization header.", "status": 401}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired. Please log in again.", "status": 401}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({"error": "Token is invalid.", "status": 401}), 401

    # Connect to MongoDB via MongoEngine
    mongo_host = app.config['MONGODB_SETTINGS']['host']
    try:
        connect(host=mongo_host)
        print(f"Connected to MongoDB at {mongo_host}")
    except Exception as e:
        print(f"Warning: MongoDB connection could not be established at startup: {e}")

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.route('/')
    def root():
        return jsonify({
            "name": "Trip Planner API",
            "version": "1.0.0",
            "status": "online",
            "docs": "/api/v1/docs"
        })

    @app.route('/health')
    def health():
        return jsonify({"status": "healthy"})

    return app

