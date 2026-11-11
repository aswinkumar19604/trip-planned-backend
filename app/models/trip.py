from datetime import datetime, timezone
from mongoengine import Document, StringField, FloatField, ListField, ReferenceField, DateTimeField, BooleanField, CASCADE
from app.models.user import User

def utc_now():
    return datetime.now(timezone.utc)

class Trip(Document):
    meta = {
        'collection': 'trips',
        'indexes': ['user_id', 'created_at']
    }
    
    user_id = ReferenceField(User, required=True, reverse_delete_rule=CASCADE)
    name = StringField(required=True, max_length=150)
    trip_type = StringField(required=True, choices=["packaged", "unpackaged"], default="packaged")
    members = ListField(StringField(max_length=100), required=True)
    total_budget = FloatField(default=0.0)
    is_completed = BooleanField(default=False)
    created_at = DateTimeField(default=utc_now)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id.id if self.user_id else ""),
            "name": self.name,
            "trip_type": self.trip_type,
            "members": self.members,
            "total_budget": self.total_budget,
            "is_completed": bool(self.is_completed),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
