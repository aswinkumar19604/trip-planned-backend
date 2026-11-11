from datetime import datetime, timezone
from mongoengine import Document, StringField, EmailField, DateTimeField

def utc_now():
    return datetime.now(timezone.utc)

class User(Document):
    meta = {
        'collection': 'users',
        'indexes': ['email']
    }
    
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    name = StringField(required=True, max_length=120)
    created_at = DateTimeField(default=utc_now)

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
