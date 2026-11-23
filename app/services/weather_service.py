import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

# 30-minute in-memory cache: { cache_key: { "timestamp": float, "data": dict } }
_WEATHER_CACHE = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes

# Common alias mapping for popular destinations
DESTINATION_ALIASES = {
    "kodai": "Kodaikanal",
    "kodaikanal": "Kodaikanal",
    "ooty": "Ooty",
    "udhagamandalam": "Ooty",
    "courtallam": "Courtallam",
    "kutralam": "Courtallam",
    "coorg": "Madikeri",
    "pondi": "Puducherry",
    "pondicherry": "Puducherry",
    "munnar": "Munnar",
    "wayanad": "Wayanad",
    "manali": "Manali",
    "shimla": "Shimla",
    "goa": "Goa",
    "darjeeling": "Darjeeling",
    "vagamon": "Vagamon",
    "chikmagalur": "Chikmagalur",
    "alleppey": "Alappuzha",
    "alappuzha": "Alappuzha",
    "chennai": "Chennai",
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "mumbai": "Mumbai",
    "delhi": "New Delhi",
    "hyderabad": "Hyderabad",
    "jaipur": "Jaipur",
}

WMO_CODE_MAP = {
    0: ("Clear Sky", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Depositing Rime Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Moderate Drizzle", "🌦️"),
    55: ("Dense Drizzle", "🌧️"),
    61: ("Slight Rain", "🌦️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    71: ("Slight Snow", "❄️"),
    73: ("Moderate Snow", "❄️"),
    75: ("Heavy Snow", "❄️"),
    77: ("Snow Grains", "❄️"),
    80: ("Light Rain Showers", "🌦️"),
    81: ("Moderate Rain Showers", "🌧️"),
    82: ("Violent Rain Showers", "⛈️"),
    85: ("Slight Snow Showers", "🌨️"),
    86: ("Heavy Snow Showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with Slight Hail", "⛈️"),
    99: ("Thunderstorm with Heavy Hail", "⛈️"),
}

class WeatherService:
    @staticmethod
    def clean_destination_name(raw_name: str) -> str:
        """
        Cleans trip names like 'Kodai Trip 2026' or 'Weekend to Ooty' into 'Kodaikanal' or 'Ooty'
        """
        if not raw_name:
            return ""

        text = raw_name.lower().strip()

        # Remove noise words
        noise_words = [
            r"\btrip\b", r"\btour\b", r"\bvisit\b", r"\bweekend\b",
            r"\bvacation\b", r"\bholiday\b", r"\bjourney\b", r"\bto\b",
            r"\bthe\b", r"\bwith\b", r"\bfriends\b", r"\bfamily\b",
            r"\b202\d\b", r"\bday\s*\d+\b"
        ]
        for pattern in noise_words:
            text = re.sub(pattern, " ", text)

        cleaned = re.sub(r"[^\w\s]", " ", text).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        # Check aliases first
        for key, val in DESTINATION_ALIASES.items():
            if key in cleaned:
                return val

        # Capitalize first letter of each remaining word if found
        if cleaned:
            return cleaned.title()

        return raw_name.strip()

    @staticmethod
    def geocode_place(place_name: str):
        """
        Finds latitude and longitude using Open-Meteo Geocoding API (free, no key needed)
        with local fallback for top Indian travel spots.
        """
        # Top travel destinations fallback coordinates
        FALLBACK_COORDS = {
            "kodaikanal": {"name": "Kodaikanal", "latitude": 10.2381, "longitude": 77.4892, "admin1": "Tamil Nadu", "country": "India"},
            "ooty": {"name": "Ooty", "latitude": 11.4102, "longitude": 76.6950, "admin1": "Tamil Nadu", "country": "India"},
            "munnar": {"name": "Munnar", "latitude": 10.0889, "longitude": 77.0595, "admin1": "Kerala", "country": "India"},
            "courtallam": {"name": "Courtallam", "latitude": 8.9298, "longitude": 77.2690, "admin1": "Tamil Nadu", "country": "India"},
            "coorg": {"name": "Coorg", "latitude": 12.4244, "longitude": 75.7382, "admin1": "Karnataka", "country": "India"},
            "goa": {"name": "Goa", "latitude": 15.2993, "longitude": 74.1240, "admin1": "Goa", "country": "India"},
            "wayanad": {"name": "Wayanad", "latitude": 11.6854, "longitude": 76.1320, "admin1": "Kerala", "country": "India"},
            "manali": {"name": "Manali", "latitude": 32.2432, "longitude": 77.1892, "admin1": "Himachal Pradesh", "country": "India"},
            "puducherry": {"name": "Puducherry", "latitude": 11.9416, "longitude": 79.8083, "admin1": "Puducherry", "country": "India"},
            "chennai": {"name": "Chennai", "latitude": 13.0827, "longitude": 80.2707, "admin1": "Tamil Nadu", "country": "India"},
            "bangalore": {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "admin1": "Karnataka", "country": "India"},
            "bengaluru": {"name": "Bengaluru", "latitude": 12.9716, "longitude": 77.5946, "admin1": "Karnataka", "country": "India"},
            "mumbai": {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777, "admin1": "Maharashtra", "country": "India"},
            "delhi": {"name": "New Delhi", "latitude": 28.6139, "longitude": 77.2090, "admin1": "Delhi", "country": "India"},
        }

        place_key = place_name.lower().strip()

        try:
            query = urllib.parse.quote(place_name)
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=1&language=en&format=json"

            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TripPlannerApp/1.0 (travel-weather-service)"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                results = data.get("results")
                if results and len(results) > 0:
                    first = results[0]
                    return {
                        "name": first.get("name", place_name),
                        "latitude": first.get("latitude"),
                        "longitude": first.get("longitude"),
                        "country": first.get("country", ""),
                        "admin1": first.get("admin1", ""),
                    }
        except Exception as e:
            # Check local fallback
            if place_key in FALLBACK_COORDS:
                return FALLBACK_COORDS[place_key]

        if place_key in FALLBACK_COORDS:
            return FALLBACK_COORDS[place_key]

        return None

    @staticmethod
    def get_weather(destination: str) -> dict:
        """
        Fetches current weather and daily forecast with packing tips.
        Uses in-memory cache for 30 minutes.
        """
        cleaned_place = WeatherService.clean_destination_name(destination)
        if not cleaned_place:
            return {"error": "Invalid destination name."}

        cache_key = cleaned_place.lower()
        now_ts = datetime.now(timezone.utc).timestamp()

        # Check cache
        if cache_key in _WEATHER_CACHE:
            cached = _WEATHER_CACHE[cache_key]
            if now_ts - cached["timestamp"] < CACHE_TTL_SECONDS:
                return cached["data"]

        # 1. Geocode destination
        geo = WeatherService.geocode_place(cleaned_place)
        if not geo:
            # Fallback try original destination
            geo = WeatherService.geocode_place(destination.strip())
            if not geo:
                return {
                    "error": f"Could not find coordinates for '{destination}'. Please check destination name."
                }

        lat = geo["latitude"]
        lon = geo["longitude"]

        # 2. Fetch Open-Meteo forecast
        forecast_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m"
            f"&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&timezone=auto"
        )

        try:
            req = urllib.request.Request(
                forecast_url,
                headers={"User-Agent": "TripPlannerApp/1.0 (travel-weather-service)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                weather_data = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {
                "error": f"Failed to connect to weather provider: {str(e)}"
            }

        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})

        current_code = current.get("weather_code", 0)
        condition_text, icon = WMO_CODE_MAP.get(current_code, ("Clear", "☀️"))

        current_temp = round(current.get("temperature_2m", 20.0), 1)
        feels_like = round(current.get("apparent_temperature", current_temp), 1)
        humidity = current.get("relative_humidity_2m", 50)
        wind_speed = round(current.get("wind_speed_10m", 0.0), 1)
        precipitation = current.get("precipitation", 0.0)

        # Parse daily forecast (next 3-5 days)
        daily_times = daily.get("time", [])
        daily_codes = daily.get("weather_code", [])
        daily_maxs = daily.get("temperature_2m_max", [])
        daily_mins = daily.get("temperature_2m_min", [])
        daily_rain_probs = daily.get("precipitation_probability_max", [])

        forecast_list = []
        for i in range(min(5, len(daily_times))):
            d_code = daily_codes[i] if i < len(daily_codes) else 0
            d_cond, d_icon = WMO_CODE_MAP.get(d_code, ("Clear", "☀️"))
            forecast_list.append({
                "date": daily_times[i],
                "day_label": f"Day {i + 1}" if i < 2 else datetime.strptime(daily_times[i], "%Y-%m-%d").strftime("%a"),
                "max_temp": round(daily_maxs[i]) if i < len(daily_maxs) and daily_maxs[i] is not None else current_temp,
                "min_temp": round(daily_mins[i]) if i < len(daily_mins) and daily_mins[i] is not None else current_temp,
                "condition": d_cond,
                "icon": d_icon,
                "rain_prob": daily_rain_probs[i] if i < len(daily_rain_probs) else 0,
            })

        # Today's high and low
        high_temp = forecast_list[0]["max_temp"] if forecast_list else current_temp
        low_temp = forecast_list[0]["min_temp"] if forecast_list else current_temp
        max_rain_today = forecast_list[0]["rain_prob"] if forecast_list else 0

        # Smart packing and travel advice
        packing_tips = []
        if current_temp < 16 or low_temp < 16:
            packing_tips.append("Cool hill climate. Pack sweaters, shawls, and warm jackets! 🧥")
        elif current_temp > 30 or high_temp > 30:
            packing_tips.append("Warm and sunny. Carry sunglasses, sunscreen, and light cottons! 🕶️")
        else:
            packing_tips.append("Pleasant weather. Carry a light cardigan or comfortable layer! 🧣")

        if max_rain_today > 30 or precipitation > 0.5 or "Rain" in condition_text or "Drizzle" in condition_text:
            packing_tips.append("Rain or showers expected. Make sure to carry an umbrella or raincoat! ☔")

        result = {
            "destination": geo["name"],
            "region": geo.get("admin1", ""),
            "country": geo.get("country", ""),
            "latitude": lat,
            "longitude": lon,
            "current": {
                "temperature": current_temp,
                "feels_like": feels_like,
                "condition": condition_text,
                "icon": icon,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "precipitation": precipitation,
                "high": high_temp,
                "low": low_temp,
                "rain_probability": max_rain_today,
            },
            "packing_tips": packing_tips,
            "forecast": forecast_list,
        }

        # Store in cache
        _WEATHER_CACHE[cache_key] = {
            "timestamp": now_ts,
            "data": result,
        }

        return result
