from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from app.models.user import User

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password)

    @staticmethod
    def generate_token(user: User) -> str:
        # Identity can be user id string
        return create_access_token(identity=str(user.id))

