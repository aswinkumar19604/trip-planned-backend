from flask import request
from flask_restx import Namespace, Resource
from app.services.weather_service import WeatherService

weather_ns = Namespace('weather', description='Live destination weather forecast and packing recommendations')

@weather_ns.route('')
class WeatherResource(Resource):
    @weather_ns.doc(
        params={'destination': 'Destination city or hill station (e.g. Kodai, Ooty, Goa, Munnar)'}
    )
    def get(self):
        """
        Get live weather and travel packing advisory for a destination.
        """
        destination = request.args.get('destination', '').strip()
        if not destination:
            return {"error": "destination parameter is required (e.g. ?destination=Kodai)"}, 400

        try:
            weather = WeatherService.get_weather(destination)
            if "error" in weather:
                return weather, 404
            return weather, 200
        except Exception as e:
            return {
                "error": f"Failed to retrieve weather for {destination}: {str(e)}"
            }, 500
