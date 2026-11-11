from marshmallow import Schema, fields, validate

class RegisterSchema(Schema):
    email = fields.Email(required=True, error_messages={"required": "Email is required."})
    password = fields.String(
        required=True,
        validate=validate.Length(min=6, error="Password must be at least 6 characters.")
    )
    name = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Name cannot be empty.")
    )

class LoginSchema(Schema):
    email = fields.Email(required=True, error_messages={"required": "Email is required."})
    password = fields.String(required=True, error_messages={"required": "Password is required."})

class UserResponseSchema(Schema):
    id = fields.String()
    email = fields.Email()
    name = fields.String()
    created_at = fields.String()

