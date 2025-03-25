from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import asyncio
import time
import json

load_dotenv()

# Set up Gemini API key and model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")  
client = MongoClient(MONGO_URI)
db = client["CandidateMatch"]
resume_collection = db["Resume_parsed"]
cleaned_collection = db["Cleaned"]

# LangChain model setup
llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)
conversation = ConversationChain(llm=llm, memory=ConversationBufferMemory())

# Function to fill missing details using LLM
async def fill_missing_details(field_name, existing_value, resume_text):
    if existing_value:
        return existing_value.strip()
    
    prompt = f"""
    FIND and Extract only the {field_name} from the given resume text. 
    If missing, return None. Return only the value without any explanations.
    Resume:
    {resume_text}
    """
    loop = asyncio.get_event_loop()
    
    try:
        response = await loop.run_in_executor(None, conversation.run, prompt)
        if response:
            response = response.strip()
            if response.lower().startswith("none"):
                return None
            return response
        return None
    except Exception as e:
        print(f"Error fetching {field_name}: {e}")
        return None

def clean_employment_history(employment_data):
    # Create a dictionary to track unique employment entries
    unique_entries = {}
    
    for entry in employment_data:
        # Create a unique key based on company and designation
        key = f"{entry.get('company', '').lower()}_{entry.get('designation', '').lower()}"
        
        # If this entry doesn't exist or has a more recent date range, add/update it
        if key not in unique_entries or (
            entry.get('from') and 
            (not unique_entries[key].get('from') or 
             entry.get('from') < unique_entries[key].get('from'))
        ):
            unique_entries[key] = entry
    
    # Convert back to list and sort by start date
    cleaned_history = list(unique_entries.values())
    
    # Sort by start date (assuming 'from' is in a sortable format like YYYY-MM-DD)
    cleaned_history.sort(key=lambda x: x.get('from', ''), reverse=True)
    
    return cleaned_history

async def process_single_resume():
    data = resume_collection.find_one()
    if not data:
        print("No resume found.")
        return

    resume_text = data.get("resumeParseData", "")

    # Extract basic details
    details = await asyncio.gather(
        fill_missing_details("full name", f"{data.get('fName', '')} {data.get('lName', '')}".strip(), resume_text),
        fill_missing_details("email", data.get("email", ""), resume_text),
        fill_missing_details("phone number", data.get("number", ""), resume_text),
        fill_missing_details("current job title", data.get("devDesg", ""), resume_text),
        fill_missing_details("city", data.get("devCity", ""), resume_text),
        fill_missing_details("state", data.get("devState", ""), resume_text),
        fill_missing_details("country code", data.get("devCountryCode", ""), resume_text),
        fill_missing_details("LinkedIn profile", data.get("devSocialProfile.linkedin", ""), resume_text),
        fill_missing_details("GitHub profile", data.get("devSocialProfile.gitHub", ""), resume_text),
        fill_missing_details("portfolio website", data.get("portfolio", ""), resume_text),
        fill_missing_details("skills", ", ".join(data.get("devSkills", [])), resume_text),
        fill_missing_details("languages", data.get("languages", ""), resume_text),
    )
    
    (full_name, email, phone_number, job_title, city, state, country_code, linkedin, github, portfolio, skills, languages) = details

    # Extract Employment History
    employment_history = []
    for job in data.get("devEmployment", []):
        employment_details = await asyncio.gather(
            fill_missing_details("designation", job.get("designation", ""), resume_text),
            fill_missing_details("company name", job.get("companyName", ""), resume_text),
            fill_missing_details("start date", job.get("from", ""), resume_text),
            fill_missing_details("end date", job.get("to", ""), resume_text),
            fill_missing_details("job location", job.get("location", ""), resume_text),
        )
        
        # Only add non-empty employment entries
        if any(employment_details):
            employment_history.append({
                "designation": employment_details[0] or job.get("designation", ""),
                "company": employment_details[1] or job.get("companyName", ""),
                "from": employment_details[2] or job.get("from", ""),
                "to": employment_details[3] or job.get("to", ""),
                "location": employment_details[4] or job.get("location", ""),
            })

    # Clean and deduplicate employment history
    cleaned_employment_history = clean_employment_history(employment_history)

    # Extract Education Details
    education = []
    for edu in data.get("devAcademic", []):
        education_details = await asyncio.gather(
            fill_missing_details("specialization", edu.get("specialization", ""), resume_text),
            fill_missing_details("institution", edu.get("institution", ""), resume_text),
            fill_missing_details("degree", edu.get("degree", ""), resume_text),
            fill_missing_details("graduation year", edu.get("year", ""), resume_text),
        )
        education.append({
            "specialization": education_details[0] or edu.get("specialization", ""),
            "institution": education_details[1] or edu.get("institution", ""),
            "degree": education_details[2] or edu.get("degree", ""),
            "year": education_details[3] or edu.get("year", ""),
        })

    # Extract Projects (Check both devProjectDetails & LLM)
    projects = data.get("devProjectDetails", [])
    if not projects:
        print("No projects found in devProjectDetails, extracting from resume text...")
        projects = await fill_missing_details("project details", "", resume_text)
    
    cleaned_data = {
        "Full Name": full_name,
        "Email": email,
        "Phone Number": phone_number,
        "Current Job Title": job_title,
        "City": city,
        "State": state,
        "Country Code": country_code,
        "LinkedIn Profile": linkedin,
        "GitHub Profile": github,
        "Portfolio Website": portfolio,
        "Education": education,
        "Employment History": cleaned_employment_history,
        "Skills": [skill.strip() for skill in skills.split(",") if skill.strip()],
        "Languages Known": languages,
        "Projects": projects if isinstance(projects, list) else [projects]  # Ensure projects is a list
    }
    return cleaned_data

print("Processing resumes...")
start_time = time.time()
cleaned_data = asyncio.run(process_single_resume())

if cleaned_data:
    # Save to JSON file
    with open("cleaned_resume.json", "w") as f:
        json.dump(cleaned_data, f, indent=4)
    
    # Optional: Save to MongoDB
    cleaned_collection.insert_one(cleaned_data)

print(f"Processing completed in {time.time() - start_time} seconds.")