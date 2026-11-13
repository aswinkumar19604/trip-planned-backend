from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from bson import ObjectId

from app.models.trip import Trip, ItineraryItem
from app.schemas.itinerary_schema import CreateItineraryItemSchema, UpdateItineraryItemSchema

itinerary_ns = Namespace('itinerary', path='/trips', description='2-Day Itinerary time slots and activity tracking')

itinerary_model = itinerary_ns.model('ItineraryItem', {
    'day': fields.Integer(required=True, description='Day 1 or Day 2', example=1),
    'time': fields.String(required=True, description='Time slot', example='09:00 AM'),
    'title': fields.String(required=True, description='Activity title', example='Breakfast & Team Briefing'),
    'location': fields.String(required=False, description='Location', example='Café Green'),
    'notes': fields.String(required=False, description='Notes', example='Pack cameras and water bottles'),
    'is_completed': fields.Boolean(required=False, description='Completion status', example=False),
})

@itinerary_ns.route('/<string:trip_id>/itinerary')
class TripItineraryResource(Resource):
    @jwt_required()
    @itinerary_ns.doc(security='Bearer Auth')
    def get(self, trip_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        itinerary_list = [item.to_dict() for item in (trip.itinerary or [])]
        return {
            "trip_id": trip_id,
            "itinerary": itinerary_list
        }, 200

    @jwt_required()
    @itinerary_ns.doc(security='Bearer Auth')
    @itinerary_ns.expect(itinerary_model, validate=False)
    def post(self, trip_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        schema = CreateItineraryItemSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 400

        item = ItineraryItem(
            day=data["day"],
            time=data["time"].strip(),
            title=data["title"].strip(),
            location=data.get("location", "").strip(),
            notes=data.get("notes", "").strip(),
            is_completed=data.get("is_completed", False)
        )

        trip.itinerary.append(item)
        trip.save()

        return {
            "message": "Itinerary slot added successfully",
            "item": item.to_dict(),
            "itinerary": [i.to_dict() for i in trip.itinerary]
        }, 201

@itinerary_ns.route('/<string:trip_id>/itinerary/<string:item_id>')
class SingleItineraryItemResource(Resource):
    @jwt_required()
    @itinerary_ns.doc(security='Bearer Auth')
    def put(self, trip_id, item_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        # Find target item
        target = None
        for item in trip.itinerary:
            if str(item.id) == item_id:
                target = item
                break

        if not target:
            return {"error": "Itinerary item not found"}, 404

        schema = UpdateItineraryItemSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 400

        if "day" in data:
            target.day = data["day"]
        if "time" in data:
            target.time = data["time"].strip()
        if "title" in data:
            target.title = data["title"].strip()
        if "location" in data:
            target.location = data["location"].strip()
        if "notes" in data:
            target.notes = data["notes"].strip()
        if "is_completed" in data:
            target.is_completed = bool(data["is_completed"])

        trip.save()

        return {
            "message": "Itinerary item updated successfully",
            "item": target.to_dict(),
            "itinerary": [i.to_dict() for i in trip.itinerary]
        }, 200

    @jwt_required()
    @itinerary_ns.doc(security='Bearer Auth')
    def delete(self, trip_id, item_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        original_count = len(trip.itinerary)
        trip.itinerary = [item for item in trip.itinerary if str(item.id) != item_id]

        if len(trip.itinerary) == original_count:
            return {"error": "Itinerary item not found"}, 404

        trip.save()

        return {
            "message": "Itinerary item deleted successfully",
            "itinerary": [i.to_dict() for i in trip.itinerary]
        }, 200
