from dotenv import load_dotenv
import os
import asyncio
import json
import pycountry
from phonenumbers.phonenumberutil import region_code_for_country_code
from cleaned import process_single_resume
from langchain_google_genai import GoogleGenerativeAI
from langchain.schema import HumanMessage

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Initialize Gemini Model only when needed
chat_model = None

def get_country_from_code(country_code):
    """Convert country code to full country name"""
    if not country_code:
        return None
        
    try:
        # Remove '+' if present
        if country_code.startswith('+'):
            country_code = country_code[1:]
            
        country_code = region_code_for_country_code(int(country_code))
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else None
    except (ValueError, AttributeError):
        return None

async def extract_location(city, state, country_code):
    """Extract structured location data with minimal LLM use"""
    # Try to convert country code to country name
    country_name = get_country_from_code(country_code)
    
    # If we have all the data, return immediately without using LLM
    if city and state and country_name:
        return {
            "city": city,
            "state": state,
            "country": country_name
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
        return location_data
    except json.JSONDecodeError:
        # If parsing fails, return structured data without LLM
        return {
            "city": city or "",
            "state": state or "", 
            "country": country_name or country_code or ""
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
    
    # Get structured location data
    location_for_vector_db = await extract_location(city, state, country_code)
    
    print("Location data for vector database:")
    print(json.dumps(location_for_vector_db, indent=2))
    
    return location_for_vector_db

if __name__ == "__main__":
    asyncio.run(main())


# import os
# from dotenv import load_dotenv
# from typing import List, Dict, Any, Optional
# import asyncio
# import pinecone
# from sentence_transformers import SentenceTransformer

# # Load environment variables
# load_dotenv()
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
# INDEX_NAME = "resume-search"
# NAMESPACE = "locations"

# class LocationVectorDB:
#     def __init__(self):
#         # Initialize the embedding model
#         self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
#         self.vector_size = self.embedding_model.get_sentence_embedding_dimension()
        
#         # Initialize Pinecone
#         pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
        
#         # Create index if it doesn't exist
#         self._create_index_if_not_exists()
        
#         # Connect to the index
#         self.index = pinecone.Index(INDEX_NAME)
    
#     def _create_index_if_not_exists(self):
#         """Create the vector index if it doesn't already exist"""
#         if INDEX_NAME not in pinecone.list_indexes():
#             pinecone.create_index(
#                 name=INDEX_NAME,
#                 dimension=self.vector_size,
#                 metric="cosine"
#             )
#             print(f"Created new Pinecone index: {INDEX_NAME}")
    
#     def _create_location_string(self, location_data: Dict[str, str]) -> str:
#         """Create a string representation of location data for embedding"""
#         parts = []
#         if location_data.get("city"):
#             parts.append(location_data["city"])
#         if location_data.get("state"):
#             parts.append(location_data["state"])
#         if location_data.get("country"):
#             parts.append(location_data["country"])
        
#         return ", ".join(parts)
    
#     def _get_location_embedding(self, location_data: Dict[str, str]) -> List[float]:
#         """Convert location data to vector embedding"""
#         location_string = self._create_location_string(location_data)
#         return self.embedding_model.encode(location_string).tolist()
    
#     async def store_location(self, 
#                              resume_id: str, 
#                              location_data: Dict[str, str]) -> bool:
#         """Store a single location with its resume ID"""
#         try:
#             # Create the embedding vector
#             vector = self._get_location_embedding(location_data)
            
#             # Prepare metadata
#             metadata = {
#                 "resume_id": resume_id,
#                 "city": location_data.get("city", ""),
#                 "state": location_data.get("state", ""),
#                 "country": location_data.get("country", ""),
#                 "location_text": self._create_location_string(location_data)
#             }
            
#             # Upsert the vector
#             self.index.upsert(
#                 vectors=[(resume_id, vector, metadata)],
#                 namespace=NAMESPACE
#             )
#             return True
#         except Exception as e:
#             print(f"Error storing location: {e}")
#             return False
    
#     async def batch_store_locations(self, location_data_list: List[Dict[str, Any]]) -> int:
#         """Store multiple locations in a batch
        
#         Each dict in the list should have:
#         - resume_id: Unique identifier for the resume
#         - location: Dict with city, state, country
#         """
#         success_count = 0
#         vectors_to_upsert = []
        
#         for item in location_data_list:
#             try:
#                 resume_id = item.get("resume_id")
#                 location = item.get("location", {})
                
#                 if not resume_id or not location:
#                     continue
                
#                 # Create the embedding vector
#                 vector = self._get_location_embedding(location)
                
#                 # Prepare metadata
#                 metadata = {
#                     "resume_id": resume_id,
#                     "city": location.get("city", ""),
#                     "state": location.get("state", ""),
#                     "country": location.get("country", ""),
#                     "location_text": self._create_location_string(location)
#                 }
                
#                 vectors_to_upsert.append((resume_id, vector, metadata))
#                 success_count += 1
#             except Exception as e:
#                 print(f"Error processing location: {e}")
        
#         # Upsert in batches of 100 to avoid API limitations
#         batch_size = 100
#         for i in range(0, len(vectors_to_upsert), batch_size):
#             batch = vectors_to_upsert[i:i+batch_size]
#             self.index.upsert(vectors=batch, namespace=NAMESPACE)
        
#         return success_count
    
#     async def search_by_location(self, 
#                                 query_location: Dict[str, str], 
#                                 limit: int = 10) -> List[Dict[str, Any]]:
#         """Search for resumes by location similarity"""
#         # Convert query location to embedding
#         query_vector = self._get_location_embedding(query_location)
        
#         # Search in Pinecone
#         results = self.index.query(
#             vector=query_vector,
#             top_k=limit,
#             namespace=NAMESPACE,
#             include_metadata=True
#         )
        
#         # Format and return results
#         formatted_results = []
#         for match in results['matches']:
#             formatted_results.append({
#                 "resume_id": match['metadata'].get("resume_id"),
#                 "location": {
#                     "city": match['metadata'].get("city", ""),
#                     "state": match['metadata'].get("state", ""),
#                     "country": match['metadata'].get("country", "")
#                 },
#                 "similarity_score": match['score']
#             })
        
#         return formatted_results
    
#     async def filter_by_region(self, 
#                                country: Optional[str] = None,
#                                state: Optional[str] = None,
#                                limit: int = 100) -> List[Dict[str, Any]]:
#         """Filter resumes by exact country and/or state match"""
#         filter_conditions = {}
#         if country:
#             filter_conditions["country"] = {"$eq": country}
#         if state:
#             filter_conditions["state"] = {"$eq": state}
            
#         # Return empty list if no filters provided
#         if not filter_conditions:
#             return []
        
#         # Create combined filter
#         filter_expr = {"$and": [{k: v} for k, v in filter_conditions.items()]} if len(filter_conditions) > 1 else filter_conditions
        
#         # Search with metadata filter
#         results = self.index.query(
#             vector=[0.0] * self.vector_size,  # Dummy vector since we're just filtering
#             top_k=limit,
#             namespace=NAMESPACE,
#             include_metadata=True,
#             filter=filter_expr
#         )
        
#         # Format and return results
#         formatted_results = []
#         for match in results['matches']:
#             formatted_results.append({
#                 "resume_id": match['metadata'].get("resume_id"),
#                 "location": {
#                     "city": match['metadata'].get("city", ""),
#                     "state": match['metadata'].get("state", ""),
#                     "country": match['metadata'].get("country", "")
#                 }
#             })
            
#         return formatted_results

# # Integration function with existing location extraction code
# async def integrate_with_location_extraction():
#     """Example of integrating with your existing location extraction code"""
#     from location import extract_location, process_single_resume
    
#     # Initialize the vector database
#     vector_db = LocationVectorDB()
    
#     # Get cleaned resume data (your existing function)
#     cleaned_data = await process_single_resume()
    
#     if not cleaned_data:
#         print("No resume data found.")
#         return
    
#     # Extract location data (your existing function)
#     city = cleaned_data.get("City", "")
#     state = cleaned_data.get("State", "")
#     country_code = cleaned_data.get("Country Code", "")
    
#     # Get structured location data using your function
#     location_data = await extract_location(city, state, country_code)
    
#     # Store in vector database
#     resume_id = cleaned_data.get("ResumeID", str(hash(str(cleaned_data))))
#     result = await vector_db.store_location(resume_id, location_data)
    
#     if result:
#         print(f"Successfully stored location data for resume {resume_id}")
#     else:
#         print(f"Failed to store location data for resume {resume_id}")

# # Example usage
# async def example_usage():
#     vector_db = LocationVectorDB()
    
#     # Example data
#     test_location = {
#         "resume_id": "test123",
#         "location": {"city": "Mumbai", "state": "Maharashtra", "country": "India"}
#     }
    
#     # Store a single location
#     await vector_db.store_location(test_location["resume_id"], test_location["location"])
    
#     # Search
#     results = await vector_db.search_by_location({"city": "Mumbai", "state": "Maharashtra", "country": "India"})
#     print(f"Found {len(results)} matching results")
    
#     # Filter by country
#     india_results = await vector_db.filter_by_region(country="India")
#     print(f"Found {len(india_results)} resumes from India")

# if __name__ == "__main__":
#     # Run the example
#     asyncio.run(example_usage())