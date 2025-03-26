from dotenv import load_dotenv
import os
import asyncio
import json
import pycountry
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from phonenumbers.phonenumberutil import region_code_for_country_code
from cleaned import process_single_resume
from langchain_google_genai import GoogleGenerativeAI
from langchain.schema import HumanMessage

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Initialize Gemini Model and Geocoder only when needed
chat_model = None
geolocator = Nominatim(user_agent="resume_location_finder")

def get_country_from_code(country_code):
    """Convert country code to full country name"""
    if not country_code:
        return None
        
    try:
        if country_code.startswith('+'):
            country_code = country_code[1:]
            
        country_code = region_code_for_country_code(int(country_code))
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else None
    except (ValueError, AttributeError):
        return None

async def get_coordinates(city, state, country):
    """
    Asynchronously get latitude and longitude for a given location
    
    Args:
        city (str): City name
        state (str): State name
        country (str): Country name
    
    Returns:
        dict: A dictionary containing latitude and longitude, or None if not found
    """
    try:
        # Try full location query
        location_query = f"{city}, {state}, {country}".strip(', ')
        location = geolocator.geocode(location_query, timeout=10)
        
        if location:
            return {
                "latitude": location.latitude,
                "longitude": location.longitude
            }
        
        # If full query fails, try city and country
        if city and country:
            location_query = f"{city}, {country}"
            location = geolocator.geocode(location_query, timeout=10)
            
            if location:
                return {
                    "latitude": location.latitude,
                    "longitude": location.longitude
                }
        
        # If city fails, try country
        location = geolocator.geocode(country, timeout=10)
        
        if location:
            return {
                "latitude": location.latitude,
                "longitude": location.longitude
            }
        
        return None
    
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return None

def calculate_distance(location1, location2):
    
    #Calculate distance between two locations in kilometers
    
    #Args:
        #location1 (dict): First location with 'latitude' and 'longitude'
        #location2 (dict): Second location with 'latitude' and 'longitude'
    
    #Returns:
        #float: Distance in kilometers, or None if coordinates are missing
    # Check if both locations have valid coordinates
    if (not location1 or 'latitude' not in location1 or 'longitude' not in location1 or
        not location2 or 'latitude' not in location2 or 'longitude' not in location2):
        return None
    
    # Create coordinate tuples
    coord1 = (location1['latitude'], location1['longitude'])
    coord2 = (location2['latitude'], location2['longitude'])
    
    try:
        # Calculate distance using geodesic method
        distance = geodesic(coord1, coord2).kilometers
        return round(distance, 2)
    except Exception as e:
        print(f"Distance calculation error: {e}")
        return None

async def extract_location(city, state, country_code):
    country_name = get_country_from_code(country_code)
    
    # If we have all the data, return immediately without using LLM
    if city and state and country_name:
        # Get coordinates
        coordinates = await get_coordinates(city, state, country_name)
        
        return {
            "city": city,
            "state": state,
            "country": country_name,
            **(coordinates or {})
        }
    
    # Initialize the model only when needed
    global chat_model
    if chat_model is None:
        chat_model = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)
    
    # Simplified prompt for minimal token usage
    prompt = f"""
Convert this location data to a proper JSON with city, state, and full country name:
City: {city or 'Unknown'}
State: {state or 'Unknown'}
Country: {country_name or country_code or 'Unknown'}

Return ONLY a valid JSON with these three fields.
"""
    
    # Use LLM for missing information
    response = chat_model.invoke([HumanMessage(content=prompt)])
    
    try:
        location_data = json.loads(response)
        
        # Get coordinates
        coordinates = await get_coordinates(
            location_data.get('city', ''), 
            location_data.get('state', ''), 
            location_data.get('country', '')
        )
        
        # Merge location data with coordinates
        return {
            **location_data,
            **(coordinates or {})
        }
    except json.JSONDecodeError:
        # If parsing fails, return structured data without LLM
        user_resume = {
            "city": city or "",
            "state": state or "", 
            "country": country_name or country_code or ""
        }
        
        # Get coordinates for the fallback data
        coordinates = await get_coordinates(
            user_resume.get('city', ''), 
            user_resume.get('state', ''), 
            user_resume.get('country', '')
        )
        
        return {
            **user_resume,
            **(coordinates or {})
        }

async def main():
    # Get data from your existing function
    cleaned_data = await process_single_resume()
    
    if not cleaned_data:
        print("No resume data found.")
        return None
        
    # Extract just the location fields
    city = cleaned_data.get("City", "")
    state = cleaned_data.get("State", "")
    country_code = cleaned_data.get("Country Code", "")
    
    # Get structured location data with coordinates
    location_for_vector_db = await extract_location(city, state, country_code)
    
    # Example employer location for distance calculation
    employer_location = {
        "city": "Meerut",
        "state": "Uttar Pradesh",
        "country": "India"
    }
    
    # Get employer coordinates
    employer_coordinates = await get_coordinates(
        employer_location['city'], 
        employer_location['state'], 
        employer_location['country']
    )
    
    # Combine employer location with coordinates
    employer_location_full = {
        **employer_location,
        **(employer_coordinates or {})
    }
    
    # Calculate distance
    distance = calculate_distance(location_for_vector_db, employer_location_full)
    
    # Prepare final result
    result = {
        "candidate_location": location_for_vector_db,
        "employer_location": employer_location_full,
        "distance_km": distance
    }
    
    print("Location data for vector database:")
    print(json.dumps(result, indent=2))
    
    return result

if __name__ == "__main__":
    asyncio.run(main())