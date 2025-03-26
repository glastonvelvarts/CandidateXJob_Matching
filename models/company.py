import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
import asyncio
import re
from typing import List, Dict, Any
from cleaned import process_single_resume

load_dotenv()

# Set up Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")

# Initialize Gemini model
model = genai.GenerativeModel(model_name=GEMINI_MODEL)

def clean_json_response(response_text: str) -> Dict[str, Any]:
    """
    Clean and parse JSON response, handling code block markers
    """
    # Remove code block markers and extra whitespace
    response_text = response_text.replace('```json', '').replace('```', '').strip()
    
    try:
        # Try parsing the cleaned text
        return json.loads(response_text)
    except json.JSONDecodeError:
        # If direct parsing fails, try to extract JSON content
        try:
            # Find JSON-like content between first { and last }
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except:
            pass
    
    # Fallback
    return {
        "company_name": "Unknown",
        "error": "Failed to parse company details",
        "raw_response": response_text
    }

async def extract_company_details(company_name: str) -> Dict[str, Any]:
    """
    Extract detailed information about a company using Gemini
    """
    prompt = f"""
    Provide a detailed JSON analysis of the company '{company_name}':

    {{
        "company_name": "{company_name}",
        "classification": {{
            "type": "Startup/MNC/SME/etc",
            "industry": "IT/Finance/or Any other industry",
            "size": "Small/Medium/Large/etc",
            "business_model": "Product/Service/Consulting/etc"
        }},
        "profile": {{
            "primary_focus": "Core business domain",
            "technologies_or_domain": ["Tech1", "Tech2"],
            "market_position": "Leading/Emerging/Established",
            "notable_characteristics": "Key company traits"
        }},
        "work_environment": {{
            "culture": "Collaborative/Fast-paced",
            "tech_stack": ["Language1", "Framework2"],
            "innovation_level": "High/Moderate/Low",
            "growth_potential": "Strong/Moderate/Limited"
        }}
    }}

    Ensure the response is a valid, parseable JSON with detailed, realistic information.
    """
    
    try:
        # Use generate_content with error handling
        response = model.generate_content(prompt)
        
        # Clean and parse the response
        company_details = clean_json_response(response.text)
        
        # Ensure company name is included
        company_details['company_name'] = company_name
        
        return company_details

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
    # Fetch resume data
    resume_data = asyncio.run(process_single_resume())
    employment_history = resume_data.get("Employment History", [])
    
    # Extract company details
    company_details = asyncio.run(process_companies(employment_history))
    
    # Save to JSON
    with open("company_details.json", "w") as f:
        json.dump(company_details, f, indent=4)
    
    # Pretty print
    for company in company_details:
        print(f"\nCompany: {company.get('company_name', 'Unknown')}")
        for key, value in company.items():
            if key not in ['company_name', 'error']:
                print(f"{key.replace('_', ' ').title()}: {json.dumps(value, indent=2)}")

if __name__ == "__main__": 
    main()