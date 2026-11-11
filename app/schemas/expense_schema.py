from marshmallow import Schema, fields, validate

class CreateExpenseSchema(Schema):
    title = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Expense title cannot be empty.")
    )
    amount = fields.Float(
        required=True,
        validate=validate.Range(min=0.01, error="Amount must be greater than 0.")
    )
    paid_by = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Payer name cannot be empty.")
    )

class ExpenseResponseSchema(Schema):
    id = fields.String()
    trip_id = fields.String()
    title = fields.String()
    amount = fields.Float()
    paid_by = fields.String()
    created_at = fields.String()

