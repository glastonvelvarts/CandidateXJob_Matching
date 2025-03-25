# from openai import OpenAI
# from dotenv import load_dotenv
# import os
# import json
# from typing import List, Dict, Any
# import asyncio
# from cleaned import process_single_resume

# load_dotenv()

# # Set up OpenAI API key and model
# OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
# OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL", "gpt-3.5-turbo")

# # Initialize OpenAI client
# client = OpenAI(api_key=OPEN_AI_API_KEY)

# async def extract_company_details(company_name: str, resume_text: str = "") -> Dict[str, Any]:
#     """
#     Extract detailed information about a company using OpenAI
    
#     Args:
#         company_name (str): Name of the company
#         resume_text (str, optional): Full resume text for context
    
#     Returns:
#         Dict containing company details
#     """
#     prompt = f"""
#     Comprehensively analyze the company '{company_name}':

#     Provide details on:
#     1. Company Classification:
#     - Type (MNC, Startup, SME, etc.)
#     - Industry/Sector 
#     - Company Size
#     - Business Model (Product-based, Service-based, Consulting, etc.)

#     2. Company Profile:
#     - Primary Business Focus
#     - Key Technologies or Domain
#     - Market Positioning
#     - Notable Characteristics

#     3. Work Environment:
#     - Company Culture
#     - Typical Tech Stack
#     - Innovation Level
#     - Growth Potential

#     Return a structured JSON-like response with clear, concise information.
#     If any detail is uncertain, use "Not Determinable".
#     """

#     try:
#         # Use OpenAI to extract company details
#         response = await asyncio.to_thread(
#             client.chat.completions.create,
#             model=OPEN_AI_MODEL,
#             messages=[
#                 {"role": "system", "content": "You are an expert company and industry analyst."},
#                 {"role": "user", "content": prompt}
#             ],
#             response_format={"type": "json_object"},
#             max_tokens=500
#         )
        
#         # Extract the text response and parse JSON
#         response_text = response.choices[0].message.content
        
#         # Parse the JSON response
#         try:
#             details = json.loads(response_text)
#             details["company_name"] = company_name
#             return details
#         except json.JSONDecodeError:
#             return {
#                 "company_name": company_name,
#                 "error": "Failed to parse company details"
#             }

#     except Exception as e:
#         print(f"Error extracting details for {company_name}: {e}")
#         return {
#             "company_name": company_name,
#             "error": str(e)
#         }

# async def process_companies(employment_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#     """
#     Process all companies in the employment history
    
#     Args:
#         employment_history (list): List of employment entries
    
#     Returns:
#         List of company details
#     """
#     # Extract details for each company
#     tasks = []
#     for job in employment_history:
#         company_name = job.get("company", "")
#         if company_name:
#             task = extract_company_details(company_name)
#             tasks.append(task)

#     # Run all tasks concurrently
#     company_details = await asyncio.gather(*tasks)

#     return company_details

# def main():
#     # Get employment history from process_single_resume
#     resume_data = process_single_resume()
#     employment_history = resume_data.get("Employment History", [])

#     # Run async function to get company details
#     company_details = asyncio.run(process_companies(employment_history))

#     # Save company details to a JSON file
#     with open("company_details.json", "w") as f:
#         json.dump(company_details, f, indent=4)

#     # Print company details
#     for company in company_details:
#         print(f"\nCompany: {company['company_name']}")
#         for key, value in company.items():
#             if key != 'company_name':
#                 print(f"{key.replace('_', ' ').title()}: {value}")

# if __name__ == "__main__":
#     main()
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import asyncio
from typing import List, Dict, Any
from cleaned import process_single_resume

load_dotenv()

# Set up Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# Initialize Gemini model
model = genai.GenerativeModel(model_name=GEMINI_MODEL)

async def extract_company_details(company_name: str, resume_text: str = "") -> Dict[str, Any]:
    """
    Extract detailed information about a company using Gemini
    """
    prompt = f"""
    Comprehensively analyze the company '{company_name}' and provide the details in **valid JSON format**.

    Example JSON response format:
    {{
        "company_name": "{company_name}",
        "classification": {{
            "type": "MNC / Startup / SME / Government / etc.",
            "industry": "IT / Healthcare / Finance / Manufacturing / etc.",
            "size": "Small / Medium / Large",
            "business_model": "Product-based / Service-based / Consulting / Government Entity / etc."
        }},
        "profile": {{
            "primary_focus": "Software Development / Finance / Research / Manufacturing / etc.",
            "technologies_or_domain": ["AI", "Cloud Computing", "Medical Research", "Automobile Engineering"],
            "market_position": "Leading / Emerging / Established / Niche Player",
            "notable_characteristics": "Innovation-driven / Customer-focused / R&D intensive / etc."
        }},
        "work_environment": {{
            "culture": "Collaborative / Fast-paced / Bureaucratic / etc.",
            "tech_stack": ["React", "Django", "SAP", "AutoCAD"],
            "innovation_level": "High / Moderate / Low",
            "growth_potential": "Strong / Moderate / Limited"
        }}
    }}

    Return the response **only** in JSON format with no extra text or explanations.
    """
    try:
        response = await asyncio.to_thread(model.generate_content, [prompt])
        response_text = response.text.strip()

        # Ensure response is valid JSON
        try:
            details = json.loads(response_text)
            details["company_name"] = company_name
            return details
        except json.JSONDecodeError:
            print(f"Error parsing JSON for {company_name}: {response_text}")
            return {
                "company_name": company_name,
                "error": "Failed to parse company details",
                "raw_response": response_text  # Save raw response for debugging
            }

    except Exception as e:
        print(f"Error extracting details for {company_name}: {e}")
        return {
            "company_name": company_name,
            "error": str(e)
        }

async def process_companies(employment_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process all companies in the employment history
    """
    tasks = []
    for job in employment_history:
        company_name = job.get("company", "")
        if company_name:
            task = extract_company_details(company_name)
            tasks.append(task)
    
    company_details = await asyncio.gather(*tasks)
    return company_details

def main():
    resume_data = asyncio.run(process_single_resume())
    employment_history = resume_data.get("Employment History", [])
    
    company_details = asyncio.run(process_companies(employment_history))
    
    with open("company_details.json", "w") as f:
        json.dump(company_details, f, indent=4)
    
    for company in company_details:
        print(f"\nCompany: {company['company_name']}")
        for key, value in company.items():
            if key != 'company_name':
                print(f"{key.replace('_', ' ').title()}: {value}")

if __name__ == "__main__":
    main()
