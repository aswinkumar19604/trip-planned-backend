from flask import request
from flask_restx import Namespace, Resource, fields
from app.services.places_service import PlacesService

places_ns = Namespace('places', path='/places', description='Tourist Attractions & Sightseeing recommendations')

place_model = places_ns.model('TouristPlace', {
    'id': fields.String(description='Unique place identifier', example='kodai_1'),
    'name': fields.String(description='Place name', example='Kodaikanal Lake'),
    'category': fields.String(description='Category (Lake, Viewpoint, Waterfall, etc.)', example='Lake'),
    'category_icon': fields.String(description='Emoji icon', example='🚣'),
    'rating': fields.Float(description='User rating (1-5)', example=4.7),
    'reviews_count': fields.String(description='Review count', example='15.2k'),
    'photo': fields.String(description='Photo image URL', example='https://images.unsplash.com/...'),
    'description': fields.String(description='Brief description', example='Star-shaped lake in the heart of the hills.'),
    'best_time': fields.String(description='Recommended visiting hours', example='09:00 AM – 05:30 PM'),
    'suggested_duration': fields.String(description='Suggested visit duration', example='2 hours'),
    'entry_fee': fields.String(description='Estimated entry fee', example='Free'),
    'latitude': fields.Float(description='Latitude coordinate', example=10.2381),
    'longitude': fields.Float(description='Longitude coordinate', example=77.4892),
})

places_response_model = places_ns.model('PlacesResponse', {
    'success': fields.Boolean(example=True),
    'destination': fields.String(example='Kodai'),
    'clean_name': fields.String(example='Kodaikanal'),
    'count': fields.Integer(example=6),
    'places': fields.List(fields.Nested(place_model)),
})

@places_ns.route('')
class PlacesListResource(Resource):
    @places_ns.doc(
        description='Get curated and OpenStreetMap tourist attractions for a destination',
        params={
            'destination': 'Destination or trip name (e.g. Kodai, Ooty, Goa, Chennai)',
            'category': 'Category filter (all, viewpoint, waterfall, lake, park, beach, temple, heritage)'
        }
    )
    @places_ns.response(200, 'Success', places_response_model)
    def get(self):
        destination = request.args.get('destination', '').strip()
        category = request.args.get('category', 'all').strip()

        if not destination:
            return {
                'success': False,
                'error': 'Query parameter "destination" is required',
                'places': []
            }, 400

        result = PlacesService.get_places(raw_destination=destination, category_filter=category)
        return {
            'success': True,
            **result
        }, 200
