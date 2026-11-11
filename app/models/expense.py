from datetime import datetime, timezone
from mongoengine import Document, StringField, FloatField, ReferenceField, DateTimeField, CASCADE
from app.models.trip import Trip

def utc_now():
    return datetime.now(timezone.utc)

class Expense(Document):
    meta = {
        'collection': 'expenses',
        'indexes': ['trip_id', 'created_at']
    }
    
    trip_id = ReferenceField(Trip, required=True, reverse_delete_rule=CASCADE)
    title = StringField(required=True, max_length=150)
    amount = FloatField(required=True, min_value=0.01)
    paid_by = StringField(required=True, max_length=100)
    created_at = DateTimeField(default=utc_now)

    def to_dict(self):
        return {
            "id": str(self.id),
            "trip_id": str(self.trip_id.id if self.trip_id else ""),
            "title": self.title,
            "amount": self.amount,
            "paid_by": self.paid_by,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
