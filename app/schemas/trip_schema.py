from marshmallow import Schema, fields, validate, pre_load, ValidationError, EXCLUDE

class CreateTripSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        required=True,
        validate=validate.Length(min=1, error="Trip name cannot be empty.")
    )
    trip_type = fields.String(
        required=True,
        validate=validate.OneOf(["packaged", "unpackaged"], error="Trip type must be packaged or unpackaged.")
    )
    members = fields.List(
        fields.String(),
        required=True,
        validate=validate.Length(min=1, error="At least one member is required.")
    )
    total_budget = fields.Float(
        load_default=0.0,
        validate=validate.Range(min=0.0, error="Total budget cannot be negative.")
    )
    start_date = fields.String(load_default="")
    end_date = fields.String(load_default="")

    @pre_load
    def process_members(self, data, **kwargs):
        # Support either a number of members (e.g. 4 -> ['Member 1', 'Member 2', 'Member 3', 'Member 4'])
        # or a list of names, or comma-separated names
        if not data or not isinstance(data, dict):
            return data
            
        raw_members = data.get("members")
        if isinstance(raw_members, int):
            data["members"] = [f"Member {i+1}" for i in range(max(1, raw_members))]
        elif isinstance(raw_members, str):
            if raw_members.strip().isdigit():
                count = int(raw_members.strip())
                data["members"] = [f"Member {i+1}" for i in range(max(1, count))]
            else:
                data["members"] = [m.strip() for m in raw_members.split(",") if m.strip()]
        return data

class TripResponseSchema(Schema):
    id = fields.String()
    user_id = fields.String()
    name = fields.String()
    trip_type = fields.String()
    members = fields.List(fields.String())
    total_budget = fields.Float()
    start_date = fields.String()
    end_date = fields.String()
    is_completed = fields.Boolean()
    created_at = fields.String()

