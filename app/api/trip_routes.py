from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from bson import ObjectId

from app.models.user import User
from app.models.trip import Trip
from app.models.expense import Expense
from app.schemas.trip_schema import CreateTripSchema
from app.services.split_service import SplitService

trips_ns = Namespace('trips', description='Trips management and tracking')

create_trip_model = trips_ns.model('CreateTrip', {
    'name': fields.String(required=True, description='Trip Name', example='Courtallam Trip'),
    'trip_type': fields.String(required=True, description='packaged or unpackaged', example='packaged'),
    'members': fields.Raw(required=True, description='Array of member names or count', example=['Arun', 'Divya', 'Kumar', 'Meena']),
    'total_budget': fields.Float(required=False, description='Total budget for packaged trip', example=12000.0),
    'start_date': fields.String(required=False, description='Start date YYYY-MM-DD', example='2026-11-14'),
    'end_date': fields.String(required=False, description='End date YYYY-MM-DD', example='2026-11-15'),
})

@trips_ns.route('')
class TripListResource(Resource):
    @jwt_required()
    @trips_ns.doc(security='Bearer Auth')
    def get(self):
        user_id = get_jwt_identity()
        trips = Trip.objects(user_id=user_id).order_by('-created_at')
        
        result = []
        for trip in trips:
            trip_data = trip.to_dict()
            # Calculate total spent for this trip
            expenses = Expense.objects(trip_id=trip.id)
            total_spent = sum(e.amount for e in expenses)
            trip_data["total_spent"] = round(total_spent, 2)
            trip_data["members_count"] = len(trip.members)
            result.append(trip_data)

        return {"trips": result}, 200

    @jwt_required()
    @trips_ns.doc(security='Bearer Auth')
    @trips_ns.expect(create_trip_model, validate=False)
    def post(self):
        user_id = get_jwt_identity()
        user = User.objects(id=user_id).first()
        if not user:
            return {"error": "User not found."}, 404

        schema = CreateTripSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 400

        trip = Trip(
            user_id=user,
            name=data["name"].strip(),
            trip_type=data["trip_type"],
            members=data["members"],
            total_budget=data.get("total_budget", 0.0),
            start_date=data.get("start_date", "").strip(),
            end_date=data.get("end_date", "").strip()
        )
        trip.save()

        trip_data = trip.to_dict()
        trip_data["total_spent"] = 0.0
        trip_data["members_count"] = len(trip.members)

        return {
            "message": "Trip created successfully",
            "trip": trip_data
        }, 201

@trips_ns.route('/<string:trip_id>')
class TripDetailResource(Resource):
    @jwt_required()
    @trips_ns.doc(security='Bearer Auth')
    def get(self, trip_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        expenses = Expense.objects(trip_id=trip.id).order_by('-created_at')
        settlement = SplitService.calculate_settlement(trip, list(expenses))

        return {
            "trip": trip.to_dict(),
            "expenses": [e.to_dict() for e in expenses],
            "settlement": settlement
        }, 200

    @jwt_required()
    @trips_ns.doc(security='Bearer Auth')
    def delete(self, trip_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        # Delete trip and cascaded expenses
        trip.delete()
        return {"message": "Trip deleted successfully"}, 200

@trips_ns.route('/<string:trip_id>/complete')
class TripCompleteResource(Resource):
    @jwt_required()
    @trips_ns.doc(security='Bearer Auth')
    def patch(self, trip_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        trip.is_completed = not bool(trip.is_completed)
        trip.save()

        return {
            "message": "Trip completion status updated",
            "is_completed": trip.is_completed,
            "trip": trip.to_dict()
        }, 200

