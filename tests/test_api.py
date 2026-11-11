import unittest
import json
import mongomock
from mongoengine import connect, disconnect
from app import create_app
from app.config import Config

class TestConfig(Config):
    TESTING = True
    DEBUG = False
    JWT_SECRET_KEY = 'test-secret-key-12345-very-long-secret-key-for-sha256'
    MONGODB_SETTINGS = {
        'host': 'mongodb://localhost:27017/test_trip_db',
        'mongo_client_class': mongomock.MongoClient,
    }

class TripPlannerApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        disconnect()
        # Connect using mongomock MongoClient
        connect('test_trip_db', host='mongodb://localhost:27017/test_trip_db', mongo_client_class=mongomock.MongoClient)
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        disconnect()

    def setUp(self):
        # Clear collections between tests
        from app.models.user import User
        from app.models.trip import Trip
        from app.models.expense import Expense
        User.drop_collection()
        Trip.drop_collection()
        Expense.drop_collection()

    def test_01_register_and_login(self):
        # 1. Register
        reg_payload = {
            "email": "aswin@example.com",
            "password": "password123",
            "name": "Aswin Kumar"
        }
        res = self.client.post('/api/v1/auth/register', json=reg_payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertIn("token", data)
        self.assertEqual(data["user"]["email"], "aswin@example.com")

        # 2. Duplicate registration should fail with 409
        dup_res = self.client.post('/api/v1/auth/register', json=reg_payload)
        self.assertEqual(dup_res.status_code, 409)

        # 3. Login
        login_res = self.client.post('/api/v1/auth/login', json={
            "email": "aswin@example.com",
            "password": "password123"
        })
        self.assertEqual(login_res.status_code, 200)
        token = login_res.get_json()["token"]
        self.assertTrue(len(token) > 10)

        # 4. Check profile with token
        headers = {"Authorization": f"Bearer {token}"}
        me_res = self.client.get('/api/v1/auth/me', headers=headers)
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.get_json()["user"]["name"], "Aswin Kumar")

    def test_02_packaged_and_unpackaged_trips_with_splitting(self):
        # Register user
        reg_res = self.client.post('/api/v1/auth/register', json={
            "email": "traveler@example.com",
            "password": "securepassword",
            "name": "Traveler"
        })
        token = reg_res.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create Packaged Trip: Courtallam Trip (4 members, 12,000 budget)
        trip_payload = {
            "name": "Courtallam Trip",
            "trip_type": "packaged",
            "members": ["Arun", "Divya", "Kumar", "Meena"],
            "total_budget": 12000.0
        }
        create_res = self.client.post('/api/v1/trips', json=trip_payload, headers=headers)
        self.assertEqual(create_res.status_code, 201)
        trip = create_res.get_json()["trip"]
        trip_id = trip["id"]
        self.assertEqual(trip["name"], "Courtallam Trip")
        self.assertEqual(trip["total_budget"], 12000.0)

        # Add expenses exactly matching PDF Page 3:
        # 1) Hotel · Arun ₹3,200
        self.client.post(f'/api/v1/trips/{trip_id}/expenses', json={
            "title": "Hotel",
            "amount": 3200.0,
            "paid_by": "Arun"
        }, headers=headers)

        # 2) Food · Divya ₹1,800
        self.client.post(f'/api/v1/trips/{trip_id}/expenses', json={
            "title": "Food",
            "amount": 1800.0,
            "paid_by": "Divya"
        }, headers=headers)

        # 3) Cab · Kumar ₹2,400
        res3 = self.client.post(f'/api/v1/trips/{trip_id}/expenses', json={
            "title": "Cab",
            "amount": 2400.0,
            "paid_by": "Kumar"
        }, headers=headers)
        self.assertEqual(res3.status_code, 201)

        # Fetch trip details and verify exact calculations
        trip_detail_res = self.client.get(f'/api/v1/trips/{trip_id}', headers=headers)
        self.assertEqual(trip_detail_res.status_code, 200)
        data = trip_detail_res.get_json()
        settlement = data["settlement"]

        # Verification of calculations from UI screenshot:
        # Spent: 3200 + 1800 + 2400 = 7400
        self.assertEqual(settlement["total_spent"], 7400.0)
        # Remaining: 12000 - 7400 = 4600
        self.assertEqual(settlement["remaining_budget"], 4600.0)
        # Per person: 7400 / 4 = 1850
        self.assertEqual(settlement["per_person"], 1850.0)

        # Who owes whom:
        # Meena paid 0, owes 1850
        # Divya paid 1800, owes 50
        owes_map = {item["member"]: item["owes"] for item in settlement["owes_summary"]}
        self.assertEqual(owes_map.get("Meena"), 1850.0)
        self.assertEqual(owes_map.get("Divya"), 50.0)

        # Create Unpackaged Trip (Kodaikanal Trip, 5 members)
        unpackaged_res = self.client.post('/api/v1/trips', json={
            "name": "Kodaikanal Trip",
            "trip_type": "unpackaged",
            "members": ["Member 1", "Member 2", "Member 3", "Member 4", "Member 5"]
        }, headers=headers)
        self.assertEqual(unpackaged_res.status_code, 201)

        # Check list of trips (My trips screen - PDF Page 4)
        list_res = self.client.get('/api/v1/trips', headers=headers)
        self.assertEqual(list_res.status_code, 200)
        trips_list = list_res.get_json()["trips"]
        self.assertEqual(len(trips_list), 2)

if __name__ == '__main__':
    unittest.main()
