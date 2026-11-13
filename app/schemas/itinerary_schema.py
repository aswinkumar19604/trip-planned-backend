from marshmallow import Schema, fields, validate, EXCLUDE

class CreateItineraryItemSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    day = fields.Integer(
        required=True,
        validate=validate.OneOf([1, 2], error="Day must be 1 or 2.")
    )
    time = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Time slot cannot be empty.")
    )
    title = fields.String(
        required=True,
        validate=validate.Length(min=1, max=150, error="Activity title cannot be empty.")
    )
    location = fields.String(load_default="")
    notes = fields.String(load_default="")
    is_completed = fields.Boolean(load_default=False)

class UpdateItineraryItemSchema(Schema):
    day = fields.Integer(validate=validate.OneOf([1, 2], error="Day must be 1 or 2."))
    time = fields.String(validate=validate.Length(min=1))
    title = fields.String(validate=validate.Length(min=1, max=150))
    location = fields.String()
    notes = fields.String()
    is_completed = fields.Boolean()

