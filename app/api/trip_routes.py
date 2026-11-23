from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from bson import ObjectId
from datetime import datetime, timezone
import math

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

@trips_ns.route('/explore')
class TripExploreResource(Resource):
    @jwt_required()
    @trips_ns.doc(
        security='Bearer Auth',
        params={
            'destination': 'Filter by destination name (e.g. Kodai)',
            'filter': 'Date filter: this_month, prev_month, all',
            'page': 'Page number (default 1)',
            'limit': 'Items per page (default 10)'
        }
    )
    def get(self):
        """
        Explore trip itineraries and expenses for a destination.
        Returns sanitized history (itinerary + expenses) without personal user information.
        """
        destination = request.args.get('destination', '').strip()
        time_filter = request.args.get('filter', 'all').strip().lower()

        try:
            page = max(1, int(request.args.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            limit = min(50, max(1, int(request.args.get('limit', 10))))
        except (ValueError, TypeError):
            limit = 10

        query_params = {}

        # Search by destination/trip name (case-insensitive partial match)
        if destination:
            query_params['name__icontains'] = destination

        # Filter by time period
        now = datetime.now(timezone.utc)
        if time_filter == 'this_month':
            start_of_this_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            query_params['created_at__gte'] = start_of_this_month
        elif time_filter == 'prev_month':
            if now.month == 1:
                prev_year = now.year - 1
                prev_month = 12
            else:
                prev_year = now.year
                prev_month = now.month - 1
            start_of_prev_month = datetime(prev_year, prev_month, 1, 0, 0, 0, tzinfo=timezone.utc)
            start_of_this_month = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
            query_params['created_at__gte'] = start_of_prev_month
            query_params['created_at__lt'] = start_of_this_month

        query_set = Trip.objects(**query_params).order_by('-created_at')
        total_count = query_set.count()

        # Pagination
        skip = (page - 1) * limit
        trips = query_set.skip(skip).limit(limit)

        result = []
        for trip in trips:
            # Fetch all expenses for this trip
            expenses = Expense.objects(trip_id=trip.id).order_by('created_at')
            total_spent = sum(e.amount for e in expenses)

            # Publicly sanitized expense breakdown (no personal user names)
            expenses_list = [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "amount": round(e.amount, 2),
                    "date": e.created_at.strftime("%b %d") if e.created_at else ""
                }
                for e in expenses
            ]

            # Publicly sanitized itinerary breakdown
            itinerary_list = [
                {
                    "id": str(item.id),
                    "day": item.day,
                    "time": item.time,
                    "title": item.title,
                    "location": item.location or "",
                    "notes": item.notes or ""
                }
                for item in (trip.itinerary or [])
            ]

            result.append({
                "id": str(trip.id),
                "name": trip.name,
                "trip_type": trip.trip_type,
                "total_budget": trip.total_budget,
                "total_spent": round(total_spent, 2),
                "start_date": trip.start_date or "",
                "end_date": trip.end_date or "",
                "created_at": trip.created_at.isoformat() if trip.created_at else None,
                "expenses_count": len(expenses_list),
                "itinerary_count": len(itinerary_list),
                "expenses": expenses_list,
                "itinerary": itinerary_list
            })

        total_pages = max(1, math.ceil(total_count / limit))
        has_next = page < total_pages

        return {
            "trips": result,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": total_pages,
                "has_next": has_next
            }
        }, 200

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

