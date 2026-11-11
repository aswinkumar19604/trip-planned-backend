from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from bson import ObjectId

from app.models.trip import Trip
from app.models.expense import Expense
from app.schemas.expense_schema import CreateExpenseSchema
from app.services.split_service import SplitService

expenses_ns = Namespace('expenses', path='/trips', description='Trip expense logging and settlement calculations')

create_expense_model = expenses_ns.model('CreateExpense', {
    'title': fields.String(required=True, description='Expense title', example='Hotel'),
    'amount': fields.Float(required=True, description='Amount in INR', example=3200.0),
    'paid_by': fields.String(required=True, description='Member who paid', example='Arun'),
})

@expenses_ns.route('/<string:trip_id>/expenses')
class TripExpensesResource(Resource):
    @jwt_required()
    @expenses_ns.doc(security='Bearer Auth')
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
            "expenses": [e.to_dict() for e in expenses],
            "settlement": settlement
        }, 200

    @jwt_required()
    @expenses_ns.doc(security='Bearer Auth')
    @expenses_ns.expect(create_expense_model, validate=False)
    def post(self, trip_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id):
            return {"error": "Invalid trip ID"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        schema = CreateExpenseSchema()
        try:
            data = schema.load(request.get_json() or {})
        except ValidationError as err:
            return {"error": "Validation failed", "details": err.messages}, 400

        payer = data["paid_by"].strip()
        # If payer is not yet recorded in members list, add them
        if payer not in trip.members:
            trip.members.append(payer)
            trip.save()

        expense = Expense(
            trip_id=trip,
            title=data["title"].strip(),
            amount=round(data["amount"], 2),
            paid_by=payer
        )
        expense.save()

        # Recalculate settlement with newly added expense
        all_expenses = Expense.objects(trip_id=trip.id).order_by('-created_at')
        settlement = SplitService.calculate_settlement(trip, list(all_expenses))

        return {
            "message": "Expense added successfully",
            "expense": expense.to_dict(),
            "settlement": settlement
        }, 201

@expenses_ns.route('/<string:trip_id>/expenses/<string:expense_id>')
class SingleExpenseResource(Resource):
    @jwt_required()
    @expenses_ns.doc(security='Bearer Auth')
    def delete(self, trip_id, expense_id):
        user_id = get_jwt_identity()
        if not ObjectId.is_valid(trip_id) or not ObjectId.is_valid(expense_id):
            return {"error": "Invalid IDs"}, 400

        trip = Trip.objects(id=trip_id, user_id=user_id).first()
        if not trip:
            return {"error": "Trip not found"}, 404

        expense = Expense.objects(id=expense_id, trip_id=trip.id).first()
        if not expense:
            return {"error": "Expense not found"}, 404

        expense.delete()
        
        all_expenses = Expense.objects(trip_id=trip.id).order_by('-created_at')
        settlement = SplitService.calculate_settlement(trip, list(all_expenses))

        return {
            "message": "Expense deleted successfully",
            "settlement": settlement
        }, 200
