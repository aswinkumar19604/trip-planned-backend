from flask import Blueprint
from flask_restx import Api

from app.api.auth_routes import auth_ns
from app.api.trip_routes import trips_ns
from app.api.expense_routes import expenses_ns
from app.api.itinerary_routes import itinerary_ns

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

authorizations = {
    'Bearer Auth': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Type in the *'Value'* input box: **Bearer &lt;JWT&gt;**"
    }
}

api = Api(
    api_bp,
    version='1.0.0',
    title='Trip Planner API',
    description='Trip Planner REST API with Packaged/Unpackaged Budgets & Expense Splitting',
    doc='/docs',
    authorizations=authorizations,
    security='Bearer Auth'
)

api.add_namespace(auth_ns)
api.add_namespace(trips_ns)
api.add_namespace(expenses_ns)
api.add_namespace(itinerary_ns)

