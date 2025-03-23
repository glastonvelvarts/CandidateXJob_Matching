from dotenv import load_dotenv
import os
import asyncio
import pycountry
from phonenumbers.phonenumberutil import region_code_for_country_code
from cleaned import process_single_resume  
# from geopy.geocoders import Nominatim
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

def get_country_name_from_dial_code(dial_code):
    try:
        country_code = region_code_for_country_code(int(dial_code))
        country = pycountry.countries.get(alpha_2=country_code) if country_code else None
        return country.name if country else "Invalid dial code"
    except ValueError:
        return "Invalid country code"

async def main():
    cleaned_data = await process_single_resume()  # ✅ Fetch cleaned_data properly
    if cleaned_data:
        country_code = cleaned_data.get("Country Code", "")
        print(f"Extracted Country Code: {country_code}")

        if country_code:
            country_name = get_country_name_from_dial_code(country_code)
            print(f"Mapped Country Name: {country_name}")
        else:
            print("No country code found.")
    else:
        print("cleaned_data is empty.")

if __name__ == "__main__":
    asyncio.run(main())
