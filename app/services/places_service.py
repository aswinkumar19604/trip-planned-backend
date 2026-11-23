import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 24-hour cache for dynamic places: { cache_key: { "timestamp": float, "places": list } }
_PLACES_CACHE = {}
CACHE_TTL_SECONDS = 86400  # 24 hours

DESTINATION_ALIASES = {
    # Tamil Nadu
    "kodai": "Kodaikanal",
    "kodaikanal": "Kodaikanal",
    "ooty": "Ooty",
    "udhagamandalam": "Ooty",
    "chennai": "Chennai",
    "madurai": "Madurai",
    "courtallam": "Courtallam",
    "kutralam": "Courtallam",
    "kanyakumari": "Kanyakumari",
    "cape comorin": "Kanyakumari",
    "rameswaram": "Rameswaram",
    "rameshwaram": "Rameswaram",
    "mahabalipuram": "Mahabalipuram",
    "mamallapuram": "Mahabalipuram",
    "coimbatore": "Coimbatore",
    "yercaud": "Yercaud",
    "thanjavur": "Thanjavur",

    # Kerala
    "munnar": "Munnar",
    "wayanad": "Wayanad",
    "kochi": "Kochi",
    "cochin": "Kochi",
    "alleppey": "Alappuzha",
    "alappuzha": "Alappuzha",
    "varkala": "Varkala",
    "kovalam": "Kovalam",
    "thekkady": "Thekkady",
    "vagamon": "Vagamon",

    # Karnataka
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "coorg": "Coorg",
    "madikeri": "Coorg",
    "mysore": "Mysuru",
    "mysuru": "Mysuru",
    "hampi": "Hampi",
    "chikmagalur": "Chikmagalur",
    "gokarna": "Gokarna",

    # Goa & West
    "goa": "Goa",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "pune": "Pune",
    "lonavala": "Lonavala",
    "mahabaleshwar": "Mahabaleshwar",

    # North & Golden Triangle
    "agra": "Agra",
    "delhi": "New Delhi",
    "new delhi": "New Delhi",
    "jaipur": "Jaipur",
    "udaipur": "Udaipur",
    "jodhpur": "Jodhpur",
    "varanasi": "Varanasi",
    "kashi": "Varanasi",
    "banaras": "Varanasi",
    "amritsar": "Amritsar",
    "rishikesh": "Rishikesh",
    "haridwar": "Haridwar",
    "manali": "Manali",
    "shimla": "Shimla",
    "leh": "Leh Ladakh",
    "ladakh": "Leh Ladakh",
    "srinagar": "Srinagar",

    # East & Others
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "darjeeling": "Darjeeling",
    "puri": "Puri",
    "gangtok": "Gangtok",
    "shillong": "Shillong",
    "hyderabad": "Hyderabad",
    "pondi": "Puducherry",
    "pondicherry": "Puducherry",
}

# Curated High-Quality Catalog for Top Indian Destinations
TOP_DESTINATIONS_PLACES = {
    "Kodaikanal": [
        {
            "id": "kodai_1",
            "name": "Kodaikanal Lake",
            "category": "Lake",
            "category_icon": "🚣",
            "rating": 4.7,
            "reviews_count": "15.2k",
            "photo": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
            "description": "Star-shaped lake in the heart of the hills. Famous for boating, pedal boats, and cycling along the perimeter.",
            "best_time": "09:00 AM – 05:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free (Boating ₹150+)",
            "latitude": 10.2381,
            "longitude": 77.4892,
        },
        {
            "id": "kodai_2",
            "name": "Coaker's Walk",
            "category": "Viewpoint",
            "category_icon": "🌄",
            "rating": 4.6,
            "reviews_count": "11.8k",
            "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
            "description": "A 1-kilometer pedestrian path along the edge of steep slopes offering breathtaking panoramic valley views.",
            "best_time": "07:00 AM – 10:00 AM",
            "suggested_duration": "1 hour",
            "entry_fee": "₹30",
            "latitude": 10.2315,
            "longitude": 77.4947,
        },
        {
            "id": "kodai_3",
            "name": "Pillar Rocks",
            "category": "Viewpoint",
            "category_icon": "⛰️",
            "rating": 4.6,
            "reviews_count": "9.4k",
            "photo": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&q=80",
            "description": "Three giant granite boulders standing vertically shoulder-to-shoulder, reaching 400 feet into the clouds.",
            "best_time": "09:00 AM – 04:00 PM",
            "suggested_duration": "1 hour",
            "entry_fee": "₹10",
            "latitude": 10.2072,
            "longitude": 77.4667,
        },
        {
            "id": "kodai_4",
            "name": "Bryant Park",
            "category": "Park",
            "category_icon": "🌺",
            "rating": 4.5,
            "reviews_count": "8.1k",
            "photo": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
            "description": "A wonderfully landscaped 20-acre botanical garden housing hundreds of rose varieties, shrubs, and a glasshouse.",
            "best_time": "09:30 AM – 06:00 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹30",
            "latitude": 10.2338,
            "longitude": 77.4938,
        },
        {
            "id": "kodai_5",
            "name": "Silver Cascade Falls",
            "category": "Waterfall",
            "category_icon": "🌊",
            "rating": 4.4,
            "reviews_count": "7.3k",
            "photo": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
            "description": "A glittering 180-foot waterfall cascading right by the Ghat Road, welcoming travelers to Kodaikanal.",
            "best_time": "08:00 AM – 05:00 PM",
            "suggested_duration": "45 mins",
            "entry_fee": "Free",
            "latitude": 10.2505,
            "longitude": 77.5197,
        },
        {
            "id": "kodai_6",
            "name": "Pine Forest",
            "category": "Nature",
            "category_icon": "🌲",
            "rating": 4.6,
            "reviews_count": "10.5k",
            "photo": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
            "description": "Enchanting dense forest of towering pine trees, popular for photography, peaceful strolls, and film shootings.",
            "best_time": "10:00 AM – 04:30 PM",
            "suggested_duration": "1 hour",
            "entry_fee": "Free",
            "latitude": 10.2185,
            "longitude": 77.4623,
        },
    ],
    "Ooty": [
        {
            "id": "ooty_1",
            "name": "Ooty Botanical Gardens",
            "category": "Park",
            "category_icon": "🌺",
            "rating": 4.7,
            "reviews_count": "18.3k",
            "photo": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
            "description": "Historic 55-acre garden laid out in 1848, with terraced lawns, exotic flowers, and a 20-million-year-old fossil tree trunk.",
            "best_time": "09:00 AM – 06:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "₹50",
            "latitude": 11.4173,
            "longitude": 76.7118,
        },
        {
            "id": "ooty_2",
            "name": "Doddabetta Peak",
            "category": "Viewpoint",
            "category_icon": "⛰️",
            "rating": 4.6,
            "reviews_count": "14.1k",
            "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
            "description": "The highest mountain in the Nilgiri Hills at 2,637 meters. Telescope house offers 360-degree vistas across Tamil Nadu and Kerala.",
            "best_time": "08:30 AM – 11:30 AM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹30",
            "latitude": 11.4011,
            "longitude": 76.7358,
        },
        {
            "id": "ooty_3",
            "name": "Ooty Lake & Boathouse",
            "category": "Lake",
            "category_icon": "🚣",
            "rating": 4.5,
            "reviews_count": "16.9k",
            "photo": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
            "description": "An artificial 65-acre lake surrounded by eucalyptus trees with motor, rowing, and paddle boats plus a mini toy train.",
            "best_time": "09:00 AM – 05:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "₹20 (Boating extra)",
            "latitude": 11.4075,
            "longitude": 76.6908,
        },
        {
            "id": "ooty_4",
            "name": "Pykara Waterfalls & Lake",
            "category": "Waterfall",
            "category_icon": "🌊",
            "rating": 4.6,
            "reviews_count": "8.7k",
            "photo": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
            "description": "Picturesque tiered waterfalls tumbling over rocks, followed by serene speed boating in Pykara reservoir.",
            "best_time": "10:00 AM – 04:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "₹20",
            "latitude": 11.4722,
            "longitude": 76.6022,
        },
    ],
    "Agra": [
        {
            "id": "agra_1",
            "name": "Taj Mahal",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.9,
            "reviews_count": "120.0k",
            "photo": "https://images.unsplash.com/photo-1564507592333-c60657eea523?w=800&q=80",
            "description": "UNESCO World Heritage wonder of the world. An exquisite white marble mausoleum commissioned in 1631 by Mughal Emperor Shah Jahan.",
            "best_time": "06:00 AM – 09:00 AM (Sunrise, closed Fridays)",
            "suggested_duration": "3 hours",
            "entry_fee": "₹50 (Mausoleum ₹200)",
            "latitude": 27.1751,
            "longitude": 78.0421,
        },
        {
            "id": "agra_2",
            "name": "Agra Fort",
            "category": "Heritage",
            "category_icon": "🏰",
            "rating": 4.7,
            "reviews_count": "45.0k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "Massive 16th-century red sandstone fortress that was the main residence of the Mughal emperors until 1638.",
            "best_time": "09:00 AM – 05:00 PM",
            "suggested_duration": "2.5 hours",
            "entry_fee": "₹50",
            "latitude": 27.1795,
            "longitude": 78.0211,
        },
        {
            "id": "agra_3",
            "name": "Mehtab Bagh (Moonlight Garden)",
            "category": "Park",
            "category_icon": "🌺",
            "rating": 4.6,
            "reviews_count": "18.2k",
            "photo": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
            "description": "Charbagh complex aligned perfectly opposite the Taj Mahal across the Yamuna River, providing world-class sunset photography.",
            "best_time": "05:00 PM – 06:45 PM (Sunset)",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹25",
            "latitude": 27.1798,
            "longitude": 78.0422,
        },
        {
            "id": "agra_4",
            "name": "Fatehpur Sikri",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.7,
            "reviews_count": "24.0k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "Akbar's magnificent abandoned capital city featuring the towering Buland Darwaza and Salim Chishti tomb.",
            "best_time": "09:00 AM – 04:00 PM",
            "suggested_duration": "3 hours",
            "entry_fee": "₹50",
            "latitude": 27.0945,
            "longitude": 77.6679,
        },
    ],
    "Varanasi": [
        {
            "id": "varanasi_1",
            "name": "Dashashwamedh Ghat & Ganga Aarti",
            "category": "Heritage",
            "category_icon": "🛕",
            "rating": 4.9,
            "reviews_count": "48.0k",
            "photo": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&q=80",
            "description": "The main and most vibrant riverbank ghat on the holy Ganges. Renowned worldwide for the spectacular evening Maha Ganga Aarti.",
            "best_time": "05:30 PM – 07:30 PM",
            "suggested_duration": "2.5 hours",
            "entry_fee": "Free (Boat ride ₹200+)",
            "latitude": 25.3076,
            "longitude": 83.0107,
        },
        {
            "id": "varanasi_2",
            "name": "Kashi Vishwanath Temple",
            "category": "Temple",
            "category_icon": "🛕",
            "rating": 4.8,
            "reviews_count": "55.0k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "One of the twelve most sacred Jyotirlingas of Lord Shiva, crowned with a shimmering 800kg gold spire.",
            "best_time": "05:00 AM – 11:00 AM, 04:00 PM – 09:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 25.3109,
            "longitude": 83.0107,
        },
        {
            "id": "varanasi_3",
            "name": "Assi Ghat & Sunrise Boat Ride",
            "category": "Lake",
            "category_icon": "🚣",
            "rating": 4.7,
            "reviews_count": "22.5k",
            "photo": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
            "description": "Southernmost ghat famous for peaceful morning yoga, Subah-e-Banaras music celebrations, and sunrise rowing boat tours.",
            "best_time": "05:30 AM – 08:30 AM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 25.2891,
            "longitude": 83.0069,
        },
        {
            "id": "varanasi_4",
            "name": "Sarnath (Dhamek Stupa & Deer Park)",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.8,
            "reviews_count": "19.0k",
            "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
            "description": "Sacred Buddhist pilgrimage site 10km from Varanasi where Gautama Buddha taught his first sermon after enlightenment.",
            "best_time": "09:00 AM – 05:00 PM",
            "suggested_duration": "3 hours",
            "entry_fee": "₹25",
            "latitude": 25.3811,
            "longitude": 83.0227,
        },
    ],
    "Madurai": [
        {
            "id": "madurai_1",
            "name": "Meenakshi Amman Temple",
            "category": "Temple",
            "category_icon": "🛕",
            "rating": 4.9,
            "reviews_count": "62.0k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "Iconic historic Dravidian temple on the Vaigai river featuring 14 soaring gopurams adorned with thousands of colorful mythological statues.",
            "best_time": "05:00 AM – 12:30 PM, 04:00 PM – 10:00 PM",
            "suggested_duration": "2.5 hours",
            "entry_fee": "Free",
            "latitude": 9.9195,
            "longitude": 78.1193,
        },
        {
            "id": "madurai_2",
            "name": "Thirumalai Nayakkar Mahal",
            "category": "Heritage",
            "category_icon": "🏰",
            "rating": 4.6,
            "reviews_count": "23.4k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "17th-century Indo-Saracenic palace built by King Thirumalai Nayak, renowned for colossal white pillars and evening light-and-sound shows.",
            "best_time": "09:00 AM – 05:00 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹20",
            "latitude": 9.9152,
            "longitude": 78.1235,
        },
        {
            "id": "madurai_3",
            "name": "Gandhi Memorial Museum",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.5,
            "reviews_count": "11.2k",
            "photo": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
            "description": "Housed in the historic palace of Rani Mangammal, housing the original blood-stained garment worn by Mahatma Gandhi in 1948.",
            "best_time": "10:00 AM – 05:30 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "Free",
            "latitude": 9.9317,
            "longitude": 78.1406,
        },
    ],
    "Kanyakumari": [
        {
            "id": "kanya_1",
            "name": "Vivekananda Rock Memorial",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.8,
            "reviews_count": "38.0k",
            "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
            "description": "Monument built in 1970 on an offshore rock where Swami Vivekananda attained enlightenment in 1892, reached by ferry.",
            "best_time": "08:00 AM – 04:00 PM",
            "suggested_duration": "2.5 hours",
            "entry_fee": "₹20 (Ferry ₹50)",
            "latitude": 8.0781,
            "longitude": 77.5552,
        },
        {
            "id": "kanya_2",
            "name": "Thiruvalluvar Statue",
            "category": "Heritage",
            "category_icon": "🗿",
            "rating": 4.7,
            "reviews_count": "26.0k",
            "photo": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&q=80",
            "description": "Towering 133-foot stone sculpture honoring the ancient Tamil poet and philosopher Thiruvalluvar, standing where three oceans meet.",
            "best_time": "08:00 AM – 04:00 PM",
            "suggested_duration": "1 hour",
            "entry_fee": "Included in ferry",
            "latitude": 8.0778,
            "longitude": 77.5564,
        },
        {
            "id": "kanya_3",
            "name": "Sunset Point & Triveni Sangam Beach",
            "category": "Beach",
            "category_icon": "🏖️",
            "rating": 4.7,
            "reviews_count": "31.5k",
            "photo": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800&q=80",
            "description": "Southernmost tip of mainland India where the Arabian Sea, Indian Ocean, and Bay of Bengal converge. Famous for simultaneous sunset & moonrise.",
            "best_time": "05:30 PM – 06:45 PM (Sunset)",
            "suggested_duration": "1.5 hours",
            "entry_fee": "Free",
            "latitude": 8.0776,
            "longitude": 77.5492,
        },
    ],
    "Mysuru": [
        {
            "id": "mysore_1",
            "name": "Mysore Palace (Amba Vilas)",
            "category": "Heritage",
            "category_icon": "🏰",
            "rating": 4.8,
            "reviews_count": "75.0k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "One of India's most visited royal palaces. Famous for magnificent Durbar halls and 100,000 bulbs illuminating on Sundays & festivals.",
            "best_time": "10:00 AM – 05:30 PM (Illumination 7-8 PM weekends)",
            "suggested_duration": "2.5 hours",
            "entry_fee": "₹100",
            "latitude": 12.3051,
            "longitude": 76.6552,
        },
        {
            "id": "mysore_2",
            "name": "Chamundi Hill & Temple",
            "category": "Temple",
            "category_icon": "🛕",
            "rating": 4.7,
            "reviews_count": "34.0k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "Perched at 1,000 meters elevation overlooking Mysore city, housing the ancient Chamundeshwari temple and monolithic Nandi bull.",
            "best_time": "07:30 AM – 02:00 PM, 03:30 PM – 09:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 12.2748,
            "longitude": 76.6706,
        },
        {
            "id": "mysore_3",
            "name": "Brindavan Gardens",
            "category": "Park",
            "category_icon": "🌺",
            "rating": 4.5,
            "reviews_count": "41.0k",
            "photo": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
            "description": "Terraced garden laid across the KRS Dam with topiary, rose terraces, and an illuminated musical dancing fountain in the evening.",
            "best_time": "04:30 PM – 08:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "₹50",
            "latitude": 12.4227,
            "longitude": 76.5728,
        },
    ],
    "Kochi": [
        {
            "id": "kochi_1",
            "name": "Fort Kochi & Chinese Fishing Nets",
            "category": "Heritage",
            "category_icon": "🎣",
            "rating": 4.7,
            "reviews_count": "31.0k",
            "photo": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800&q=80",
            "description": "Historic seaside neighborhood with cantilevered 14th-century Chinese fishing nets (Cheena Vala), art cafes, and spice warehouses.",
            "best_time": "08:00 AM – 11:00 AM, 05:00 PM – 07:00 PM (Sunset)",
            "suggested_duration": "2.5 hours",
            "entry_fee": "Free",
            "latitude": 9.9658,
            "longitude": 76.2421,
        },
        {
            "id": "kochi_2",
            "name": "Mattancherry Palace (Dutch Palace)",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.5,
            "reviews_count": "16.8k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "Portuguese palace gifted to the Raja of Kochi in 1555, housing world-renowned Hindu mythological murals depicting the Ramayana.",
            "best_time": "09:45 AM – 01:00 PM, 02:00 PM – 04:45 PM (Closed Fridays)",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹5",
            "latitude": 9.9583,
            "longitude": 76.2592,
        },
        {
            "id": "kochi_3",
            "name": "Jew Town & Paradesi Synagogue",
            "category": "Heritage",
            "category_icon": "✨",
            "rating": 4.6,
            "reviews_count": "14.5k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "The oldest active synagogue in the Commonwealth (1568), with hand-painted Chinese porcelain floor tiles and antique brass shops.",
            "best_time": "10:00 AM – 05:00 PM (Closed Saturdays)",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹10",
            "latitude": 9.9575,
            "longitude": 76.2597,
        },
    ],
    "Rishikesh": [
        {
            "id": "rishi_1",
            "name": "Laxman Jhula & Ram Jhula",
            "category": "Viewpoint",
            "category_icon": "🌉",
            "rating": 4.8,
            "reviews_count": "36.0k",
            "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
            "description": "Iconic iron suspension footbridges across the holy Ganges, connecting ashrams, temples, and bustling riverside cafes.",
            "best_time": "08:00 AM – 06:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 30.1348,
            "longitude": 78.3308,
        },
        {
            "id": "rishi_2",
            "name": "Triveni Ghat & Ganga Aarti",
            "category": "Heritage",
            "category_icon": "🛕",
            "rating": 4.8,
            "reviews_count": "28.5k",
            "photo": "https://images.unsplash.com/photo-1561361513-2d000a50f0dc?w=800&q=80",
            "description": "Biggest confluence ghat in Rishikesh where pilgrims bathe and attend the magical evening Maha Aarti ceremony with glowing lamps.",
            "best_time": "05:30 PM – 07:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 30.1039,
            "longitude": 78.2974,
        },
        {
            "id": "rishi_3",
            "name": "Ganges River Rafting Point (Shivpuri)",
            "category": "Nature",
            "category_icon": "🚣",
            "rating": 4.9,
            "reviews_count": "42.0k",
            "photo": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
            "description": "Adventure capital of India, offering thrilling Grade III & IV white-water rafting from Shivpuri or Marine Drive through roaring rapids.",
            "best_time": "09:00 AM – 03:00 PM (Oct – May)",
            "suggested_duration": "3.5 hours",
            "entry_fee": "₹600 – ₹1,200 per person",
            "latitude": 30.1415,
            "longitude": 78.3900,
        },
    ],
    "Goa": [
        {
            "id": "goa_1",
            "name": "Baga Beach",
            "category": "Beach",
            "category_icon": "🏖️",
            "rating": 4.7,
            "reviews_count": "32.0k",
            "photo": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800&q=80",
            "description": "Famous for watersports (parasailing, jet ski), energetic beach shacks, seafood, and nightlife along Tito's Lane.",
            "best_time": "08:00 AM – 07:00 PM (Sunset)",
            "suggested_duration": "3 hours",
            "entry_fee": "Free",
            "latitude": 15.5553,
            "longitude": 73.7517,
        },
        {
            "id": "goa_2",
            "name": "Fort Aguada",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.6,
            "reviews_count": "19.5k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "17th-century Portuguese fortress and historic 4-storey lighthouse overlooking the Arabian Sea and Sinquerim Beach.",
            "best_time": "09:30 AM – 05:30 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹25",
            "latitude": 15.4925,
            "longitude": 73.7733,
        },
        {
            "id": "goa_3",
            "name": "Basilica of Bom Jesus",
            "category": "Heritage",
            "category_icon": "⛪",
            "rating": 4.8,
            "reviews_count": "16.8k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "UNESCO World Heritage site in Old Goa containing the sacred mortal remains of St. Francis Xavier.",
            "best_time": "09:00 AM – 06:00 PM",
            "suggested_duration": "1 hour",
            "entry_fee": "Free",
            "latitude": 15.5008,
            "longitude": 73.9116,
        },
        {
            "id": "goa_4",
            "name": "Dudhsagar Falls",
            "category": "Waterfall",
            "category_icon": "🌊",
            "rating": 4.8,
            "reviews_count": "11.2k",
            "photo": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
            "description": "Four-tiered majestic 310-meter 'Sea of Milk' waterfall nestled inside the Bhagwan Mahaveer Sanctuary.",
            "best_time": "08:00 AM – 02:00 PM (Jeep Safari)",
            "suggested_duration": "4 hours",
            "entry_fee": "₹50 (Safari ₹500+)",
            "latitude": 15.3144,
            "longitude": 74.3143,
        },
    ],
    "Munnar": [
        {
            "id": "munnar_1",
            "name": "Eravikulam National Park",
            "category": "Nature",
            "category_icon": "🦌",
            "rating": 4.7,
            "reviews_count": "13.6k",
            "photo": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
            "description": "Home to the endangered Nilgiri Tahr mountain goat and blue Neelakurinji blooms, with rolling high-altitude grasslands.",
            "best_time": "08:00 AM – 03:30 PM",
            "suggested_duration": "2.5 hours",
            "entry_fee": "₹200",
            "latitude": 10.1518,
            "longitude": 77.0601,
        },
        {
            "id": "munnar_2",
            "name": "Mattupetty Dam & Lake",
            "category": "Lake",
            "category_icon": "🚣",
            "rating": 4.5,
            "reviews_count": "10.4k",
            "photo": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
            "description": "Storage concrete gravity dam with serene reservoir waters, speedboat rides, and wild elephants drinking at dawn.",
            "best_time": "09:30 AM – 05:00 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹20 (Speedboat ₹500)",
            "latitude": 10.1064,
            "longitude": 77.1245,
        },
        {
            "id": "munnar_3",
            "name": "KDHP Tea Museum & Factory",
            "category": "Heritage",
            "category_icon": "☕",
            "rating": 4.6,
            "reviews_count": "9.1k",
            "photo": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&q=80",
            "description": "Fascinating exhibition tracing the century-old history of Munnar's tea plantations with live orthodox tea processing.",
            "best_time": "09:00 AM – 04:00 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹150",
            "latitude": 10.0889,
            "longitude": 77.0592,
        },
    ],
    "Courtallam": [
        {
            "id": "courtallam_1",
            "name": "Main Falls (Peraruvi)",
            "category": "Waterfall",
            "category_icon": "🌊",
            "rating": 4.8,
            "reviews_count": "14.3k",
            "photo": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
            "description": "The largest and most famous waterfall in Courtallam, dropping 60m with herbal medicinal water from the Western Ghats.",
            "best_time": "06:00 AM – 06:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 8.9298,
            "longitude": 77.2694,
        },
        {
            "id": "courtallam_2",
            "name": "Five Falls (Aintharuvi)",
            "category": "Waterfall",
            "category_icon": "🌊",
            "rating": 4.7,
            "reviews_count": "12.8k",
            "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
            "description": "Split into 5 separate streams resembling the five heads of Adishesha serpent; popular for refreshing bathing.",
            "best_time": "07:00 AM – 05:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 8.9211,
            "longitude": 77.2476,
        },
        {
            "id": "courtallam_3",
            "name": "Old Courtallam Falls (Pazhaya Aruvi)",
            "category": "Waterfall",
            "category_icon": "🌊",
            "rating": 4.6,
            "reviews_count": "8.5k",
            "photo": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
            "description": "Quiet, secluded waterfall located 8km from town, surrounded by calm groves and fewer crowds.",
            "best_time": "08:00 AM – 04:30 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "Free",
            "latitude": 8.9567,
            "longitude": 77.3012,
        },
    ],
    "Chennai": [
        {
            "id": "chennai_1",
            "name": "Marina Beach",
            "category": "Beach",
            "category_icon": "🏖️",
            "rating": 4.6,
            "reviews_count": "45.0k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "World's second-longest urban natural sand beach (13km), famous for evening breeze, street food, and the lighthouse.",
            "best_time": "05:00 PM – 08:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 13.0500,
            "longitude": 80.2824,
        },
        {
            "id": "chennai_2",
            "name": "Kapaleeshwarar Temple",
            "category": "Temple",
            "category_icon": "🛕",
            "rating": 4.8,
            "reviews_count": "21.0k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "7th-century Dravidian architectural marvel dedicated to Lord Shiva in Mylapore, featuring an intricately sculpted rainbow gopuram.",
            "best_time": "06:00 AM – 12:00 PM, 04:30 PM – 09:00 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "Free",
            "latitude": 13.0336,
            "longitude": 80.2697,
        },
        {
            "id": "chennai_3",
            "name": "Besant Nagar Beach (Edward Elliot's)",
            "category": "Beach",
            "category_icon": "🏖️",
            "rating": 4.6,
            "reviews_count": "18.5k",
            "photo": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800&q=80",
            "description": "Relaxed beach popular with youngsters, with Schmidt Memorial, vibrant cafes, and fresh seafood stalls.",
            "best_time": "05:30 PM – 09:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 12.9998,
            "longitude": 80.2718,
        },
    ],
    "Bengaluru": [
        {
            "id": "blr_1",
            "name": "Lalbagh Botanical Garden",
            "category": "Park",
            "category_icon": "🌺",
            "rating": 4.7,
            "reviews_count": "38.0k",
            "photo": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
            "description": "240-acre garden commissioned by Hyder Ali, featuring the iconic Victorian Glass House and 3-billion-year-old Lalbagh Rock.",
            "best_time": "06:00 AM – 09:00 AM, 04:00 PM – 06:30 PM",
            "suggested_duration": "2.5 hours",
            "entry_fee": "₹30",
            "latitude": 12.9507,
            "longitude": 77.5848,
        },
        {
            "id": "blr_2",
            "name": "Bangalore Palace",
            "category": "Heritage",
            "category_icon": "🏰",
            "rating": 4.5,
            "reviews_count": "24.5k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "Tudor-style royal estate with fortified towers, stained glass, wood carvings, and royal memorabilia from the Wadiyar dynasty.",
            "best_time": "10:00 AM – 05:30 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "₹250",
            "latitude": 12.9988,
            "longitude": 77.5921,
        },
        {
            "id": "blr_3",
            "name": "Cubbon Park",
            "category": "Park",
            "category_icon": "🌳",
            "rating": 4.7,
            "reviews_count": "29.0k",
            "photo": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
            "description": "300-acre lush lung space in the city center with bamboo groves, bandstands, running tracks, and the red Seshadri Iyer Memorial.",
            "best_time": "06:00 AM – 06:00 PM",
            "suggested_duration": "2 hours",
            "entry_fee": "Free",
            "latitude": 12.9763,
            "longitude": 77.5929,
        },
    ],
    "Jaipur": [
        {
            "id": "jaipur_1",
            "name": "Hawa Mahal (Palace of Winds)",
            "category": "Heritage",
            "category_icon": "🏛️",
            "rating": 4.7,
            "reviews_count": "34.0k",
            "photo": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
            "description": "Iconic pink sandstone honeycomb facade with 953 jharokhas (casements) designed for royal ladies to view street life.",
            "best_time": "09:00 AM – 04:30 PM",
            "suggested_duration": "1.5 hours",
            "entry_fee": "₹50",
            "latitude": 26.9239,
            "longitude": 75.8267,
        },
        {
            "id": "jaipur_2",
            "name": "Amber Palace & Fort",
            "category": "Heritage",
            "category_icon": "🏰",
            "rating": 4.8,
            "reviews_count": "31.2k",
            "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
            "description": "Majestic hilltop fort built of red sandstone and marble, overlooking Maota Lake, famous for Sheesh Mahal (Mirror Palace).",
            "best_time": "08:00 AM – 05:30 PM",
            "suggested_duration": "3 hours",
            "entry_fee": "₹100",
            "latitude": 26.9855,
            "longitude": 75.8513,
        },
    ],
}

class PlacesService:
    @staticmethod
    def clean_destination_name(raw_name: str) -> str:
        """
        Cleans trip names like 'Kodai Trip 2026' into 'Kodaikanal'
        """
        if not raw_name:
            return ""

        text = raw_name.lower().strip()
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

        # Alias lookup
        for key, val in DESTINATION_ALIASES.items():
            if key in cleaned:
                return val

        if cleaned:
            return cleaned.title()
        return raw_name.strip().title()

    @classmethod
    def get_places(cls, raw_destination: str, category_filter: str = "all") -> dict:
        """
        Retrieves tourist places for ANY destination in India.
        Order of resolution:
        1. Curated high-res catalog (instant 0ms)
        2. Wikipedia Travel API (dynamic real spots & photos across India)
        3. OpenStreetMap Overpass query fallback
        4. Generic city POIs
        """
        clean_name = cls.clean_destination_name(raw_destination)
        if not clean_name:
            return {
                "destination": raw_destination or "",
                "clean_name": "",
                "count": 0,
                "places": []
            }

        cache_key = f"{clean_name.lower()}:{category_filter.lower()}"
        now = datetime.now(timezone.utc).timestamp()

        # Check Cache
        if cache_key in _PLACES_CACHE:
            entry = _PLACES_CACHE[cache_key]
            if now - entry["timestamp"] < CACHE_TTL_SECONDS:
                return {
                    "destination": raw_destination,
                    "clean_name": clean_name,
                    "count": len(entry["places"]),
                    "places": entry["places"],
                    "cached": True
                }

        # 1. Check curated catalog
        matched_dest = None
        for dest_key in TOP_DESTINATIONS_PLACES.keys():
            if dest_key.lower() == clean_name.lower() or dest_key.lower() in clean_name.lower():
                matched_dest = dest_key
                break

        places = []
        if matched_dest:
            places = list(TOP_DESTINATIONS_PLACES[matched_dest])
        else:
            # 2. Query Wikipedia Travel & Heritage Engine (fast, covers every town in India)
            places = cls._fetch_wikipedia_places(clean_name)

            # 3. If Wikipedia had 0 results, try OpenStreetMap Overpass
            if not places:
                places = cls._fetch_osm_places(clean_name)

            # 4. Fallback if still empty
            if not places:
                places = cls._generate_generic_places(clean_name)

        # Apply category filter if requested
        if category_filter and category_filter.lower() != "all":
            filt = category_filter.lower()
            places = [p for p in places if p.get("category", "").lower() == filt]

        # Save in cache
        _PLACES_CACHE[cache_key] = {
            "timestamp": now,
            "places": places
        }

        return {
            "destination": raw_destination,
            "clean_name": clean_name,
            "count": len(places),
            "places": places,
            "cached": False
        }

    @classmethod
    def _fetch_wikipedia_places(cls, destination: str) -> list:
        """
        Queries Wikipedia Free Search API for tourist attractions & heritage in any Indian town/city.
        Returns real spots, extracts, and Wikimedia Commons thumbnails.
        """
        try:
            query = urllib.parse.quote(f"Tourist attractions in {destination}")
            url = (
                f"https://en.wikipedia.org/w/api.php?action=query"
                f"&generator=search&gsrsearch={query}&gsrlimit=8"
                f"&prop=extracts|pageimages|coordinates"
                f"&exintro=1&explaintext=1&exchars=220&pithumbsize=800&format=json"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "TripPlannerApp/1.0 (contact@tripplanner.local)"}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    return []

                results = []
                # Blacklist metadata or state names
                ignored_titles = {
                    destination.lower(),
                    "tourist attraction",
                    "tourism in india",
                    f"tourism in {destination.lower()}",
                    "list of tourist attractions",
                    "meghalaya", "tamil nadu", "kerala", "karnataka", "uttar pradesh",
                    "maharashtra", "rajasthan", "himachal pradesh", "uttarakhand",
                    "west bengal", "goa", "assam", "gujarat", "punjab", "odisha", "bihar"
                }

                for idx, page in enumerate(pages.values()):
                    title = page.get("title", "").strip()
                    extract = page.get("extract", "").strip()

                    # Blacklist metadata, districts, or non-matching pages
                    if not title or title.lower() in ignored_titles or "list of" in title.lower() or "district" in title.lower():
                        continue

                    # Relevance check: destination should be mentioned in title or extract
                    dest_lower = destination.lower()
                    if dest_lower not in title.lower() and dest_lower not in extract.lower():
                        continue

                    if not extract:
                        extract = f"Popular cultural and sightseeing attraction in {destination}."

                    # Determine category from title and text
                    lower_text = (title + " " + extract).lower()
                    if any(w in lower_text for w in ["waterfall", "falls", "cascade"]):
                        cat, icon = "Waterfall", "🌊"
                    elif any(w in lower_text for w in ["lake", "dam", "river", "ghat", "backwater"]):
                        cat, icon = "Lake", "🚣"
                    elif any(w in lower_text for w in ["temple", "shrine", "mosque", "church", "cathedral", "gurdwara", "basilica"]):
                        cat, icon = "Temple", "🛕"
                    elif any(w in lower_text for w in ["beach", "coast", "cove"]):
                        cat, icon = "Beach", "🏖️"
                    elif any(w in lower_text for w in ["fort", "palace", "monument", "memorial", "stupa", "caves"]):
                        cat, icon = "Heritage", "🏛️"
                    elif any(w in lower_text for w in ["peak", "viewpoint", "valley", "cliff", "hill"]):
                        cat, icon = "Viewpoint", "🌄"
                    elif any(w in lower_text for w in ["park", "garden", "sanctuary", "zoo", "forest"]):
                        cat, icon = "Park", "🌺"
                    else:
                        cat, icon = "Attraction", "⭐"

                    # Get Wikimedia photo or high quality fallback
                    photo = page.get("thumbnail", {}).get("source")
                    if not photo:
                        # Category-themed fallback photo
                        photo_map = {
                            "Waterfall": "https://images.unsplash.com/photo-1432405972618-c60b0225b8f9?w=800&q=80",
                            "Lake": "https://images.unsplash.com/photo-1596422846543-75c6fc197f07?w=800&q=80",
                            "Temple": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
                            "Beach": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=800&q=80",
                            "Heritage": "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800&q=80",
                            "Viewpoint": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
                            "Park": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?w=800&q=80",
                        }
                        photo = photo_map.get(cat, "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80")

                    coords = page.get("coordinates", [{}])[0]

                    results.append({
                        "id": f"wiki_{page.get('pageid', idx)}",
                        "name": title,
                        "category": cat,
                        "category_icon": icon,
                        "rating": round(4.5 + (idx % 4) * 0.1, 1),
                        "reviews_count": f"{4.5 + (idx % 6):.1f}k",
                        "photo": photo,
                        "description": extract,
                        "best_time": "09:00 AM – 05:30 PM",
                        "suggested_duration": "2 hours",
                        "entry_fee": "Free / Nominal",
                        "latitude": coords.get("lat", 0.0),
                        "longitude": coords.get("lon", 0.0),
                    })

                return results
        except Exception as e:
            logger.warning(f"Wikipedia attractions search failed for {destination}: {e}")
            return []

    @classmethod
    def _fetch_osm_places(cls, destination: str) -> list:
        """
        Fetches tourist places from OpenStreetMap Nominatim + Overpass API.
        """
        try:
            query = urllib.parse.quote(f"{destination}, India")
            geo_url = f"https://nominatim.openstreetmap.org/search?format=json&q={query}&limit=1"
            req = urllib.request.Request(
                geo_url,
                headers={"User-Agent": "TripPlannerApp/1.0 (contact@tripplanner.local)"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode("utf-8"))
                if not data:
                    return []
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])

            overpass_q = f"""
            [out:json][timeout:5];
            (
              node["tourism"~"attraction|viewpoint|museum"](around:10000,{lat},{lon});
              node["historic"~"monument|castle|ruins"](around:10000,{lat},{lon});
            );
            out 8;
            """
            op_url = "https://overpass-api.de/api/interpreter"
            op_data = urllib.parse.urlencode({"data": overpass_q}).encode("utf-8")
            op_req = urllib.request.Request(
                op_url,
                data=op_data,
                headers={"User-Agent": "TripPlannerApp/1.0"}
            )
            with urllib.request.urlopen(op_req, timeout=5) as op_resp:
                op_json = json.loads(op_resp.read().decode("utf-8"))
                elements = op_json.get("elements", [])
                results = []
                for i, el in enumerate(elements):
                    tags = el.get("tags", {})
                    name = tags.get("name") or tags.get("name:en")
                    if not name:
                        continue
                    tourism = tags.get("tourism") or tags.get("historic") or "Attraction"
                    cat_map = {
                        "viewpoint": ("Viewpoint", "🌄"),
                        "attraction": ("Attraction", "⭐"),
                        "museum": ("Museum", "🏛️"),
                        "monument": ("Heritage", "🏛️"),
                        "castle": ("Heritage", "🏰"),
                    }
                    cat_name, cat_icon = cat_map.get(tourism.lower(), ("Attraction", "📍"))
                    results.append({
                        "id": f"osm_{el.get('id', i)}",
                        "name": name,
                        "category": cat_name,
                        "category_icon": cat_icon,
                        "rating": round(4.4 + (i % 5) * 0.1, 1),
                        "reviews_count": f"{2.0 + (i % 5):.1f}k",
                        "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
                        "description": tags.get("description") or f"Popular sightseeing spot and {cat_name.lower()} in {destination}.",
                        "best_time": "09:00 AM – 05:00 PM",
                        "suggested_duration": "1.5 hours",
                        "entry_fee": tags.get("fee", "Free / Nominal"),
                        "latitude": el.get("lat", lat),
                        "longitude": el.get("lon", lon),
                    })
                return results
        except Exception as e:
            logger.warning(f"OSM Overpass lookup skipped for {destination}: {e}")
            return []

    @classmethod
    def _generate_generic_places(cls, destination: str) -> list:
        return [
            {
                "id": f"gen_1_{destination.lower()}",
                "name": f"{destination} City Center & Promenade",
                "category": "Explore",
                "category_icon": "🏙️",
                "rating": 4.5,
                "reviews_count": "5.4k",
                "photo": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&q=80",
                "description": f"The vibrant focal point of {destination}, ideal for local shopping, street food, and sightseeing.",
                "best_time": "10:00 AM – 07:00 PM",
                "suggested_duration": "2 hours",
                "entry_fee": "Free",
                "latitude": 0.0,
                "longitude": 0.0,
            },
            {
                "id": f"gen_2_{destination.lower()}",
                "name": f"{destination} Sunset Viewpoint",
                "category": "Viewpoint",
                "category_icon": "🌄",
                "rating": 4.6,
                "reviews_count": "3.8k",
                "photo": "https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?w=800&q=80",
                "description": f"Scenic high ground offering gorgeous panoramic sunset and sunrise views over {destination}.",
                "best_time": "05:00 PM – 06:45 PM",
                "suggested_duration": "1.5 hours",
                "entry_fee": "Free",
                "latitude": 0.0,
                "longitude": 0.0,
            },
            {
                "id": f"gen_3_{destination.lower()}",
                "name": f"{destination} Heritage Landmark",
                "category": "Heritage",
                "category_icon": "🛕",
                "rating": 4.7,
                "reviews_count": "4.2k",
                "photo": "https://images.unsplash.com/photo-1548013146-72479768bada?w=800&q=80",
                "description": f"Historic landmark showcasing the timeless heritage and cultural architecture of {destination}.",
                "best_time": "08:00 AM – 12:00 PM",
                "suggested_duration": "1.5 hours",
                "entry_fee": "Free",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        ]
