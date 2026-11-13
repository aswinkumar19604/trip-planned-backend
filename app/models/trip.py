import uuid
from datetime import datetime, timezone
from mongoengine import (
    Document, EmbeddedDocument, StringField, FloatField, ListField,
    ReferenceField, DateTimeField, BooleanField, EmbeddedDocumentField,
    IntField, CASCADE
)
from app.models.user import User

def utc_now():
    return datetime.now(timezone.utc)

class ItineraryItem(EmbeddedDocument):
    id = StringField(default=lambda: str(uuid.uuid4()))
    day = IntField(required=True, choices=[1, 2])
    time = StringField(required=True, max_length=30)
    title = StringField(required=True, max_length=150)
    location = StringField(default="", max_length=150)
    notes = StringField(default="", max_length=300)
    is_completed = BooleanField(default=False)

    def to_dict(self):
        return {
            "id": str(self.id),
            "day": self.day,
            "time": self.time,
            "title": self.title,
            "location": self.location or "",
            "notes": self.notes or "",
            "is_completed": bool(self.is_completed)
        }

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
    start_date = StringField(max_length=20, default="")
    end_date = StringField(max_length=20, default="")
    is_completed = BooleanField(default=False)
    itinerary = ListField(EmbeddedDocumentField(ItineraryItem), default=list)
    created_at = DateTimeField(default=utc_now)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id.id if self.user_id else ""),
            "name": self.name,
            "trip_type": self.trip_type,
            "members": self.members,
            "total_budget": self.total_budget,
            "start_date": self.start_date or "",
            "end_date": self.end_date or "",
            "is_completed": bool(self.is_completed),
            "itinerary": [item.to_dict() for item in self.itinerary] if self.itinerary else [],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
