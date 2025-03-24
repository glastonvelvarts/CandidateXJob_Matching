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
    
    prompt = f"Extract only the {field_name} from the given resume text. If missing, return None. Return only the value without any explanations or additional text.\nResume:\n{resume_text}"
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
    
async def process_single_resume():
    data = resume_collection.find_one()
    if not data:
        print("No resume found.")
        return

    resume_text = data.get("resumeParseData", "")

    # Parallelize LLM calls
    details = await asyncio.gather(
        fill_missing_details("full name", f"{data.get('fName', '')} {data.get('lName', '')}".strip(), resume_text),
        fill_missing_details("email", data.get("email", ""), resume_text),
        fill_missing_details("phone number", data.get("number", ""), resume_text),
        fill_missing_details("current job title", data.get("devDesg", ""), resume_text),
        fill_missing_details("city", data.get("devCity", ""), resume_text),
        fill_missing_details("country code", data.get("devCountryCode", ""), resume_text),
        fill_missing_details("LinkedIn profile", data.get("linkedin", ""), resume_text),
        fill_missing_details("GitHub profile", data.get("github", ""), resume_text),
        fill_missing_details("portfolio website", data.get("portfolio", ""), resume_text),
        fill_missing_details("skills", ", ".join(data.get("devSkills", [])), resume_text),
        fill_missing_details("languages", data.get("languages", ""), resume_text),
    )
    
    (full_name, email, phone_number, job_title, city, country_code, linkedin, github, portfolio, skills, languages) = details

    employment_history = []
    for job in data.get("devEmployment", []):
        employment_details = await asyncio.gather(
            fill_missing_details("designation", job.get("designation", ""), resume_text),
            fill_missing_details("company name", job.get("companyName", ""), resume_text),
            fill_missing_details("start date", job.get("from", ""), resume_text),
            fill_missing_details("end date", job.get("to", ""), resume_text),
            fill_missing_details("job location", job.get("location", ""), resume_text),
        )
        employment_history.append({
            "designation": employment_details[0],
            "company": employment_details[1],
            "from": employment_details[2],
            "to": employment_details[3],
            "location": employment_details[4],
        })

    education = []
    for edu in data.get("devAcademic", []):
        education_details = await asyncio.gather(
            fill_missing_details("specialization", edu.get("specialization", ""), resume_text),
            fill_missing_details("institution", edu.get("institution", ""), resume_text),
            fill_missing_details("degree", edu.get("degree", ""), resume_text),
            fill_missing_details("graduation year", edu.get("year", ""), resume_text),
        )
        education.append({
            "specialization": education_details[0],
            "institution": education_details[1],
            "degree": education_details[2],
            "year": education_details[3],
        })

    cleaned_data = {
        "Full Name": full_name,
        "Email": email,
        "Phone Number": phone_number,
        "Current Job Title": job_title,
        "City": city,
        "Country Code": country_code,
        "LinkedIn Profile": linkedin,
        "GitHub Profile": github,
        "Portfolio Website": portfolio,
        "Education": education,
        "Employment History": employment_history,
        "Skills": [skill.strip() for skill in skills.split(",") if skill.strip()],
        "Languages Known": languages,
    }

    return cleaned_data

print("Processing resumes...")
start_time = time.time()
cleaned_data = asyncio.run(process_single_resume())

if cleaned_data:
    with open("cleaned_resume.json", "w") as f:
        json.dump(cleaned_data, f, indent=4)

print(f"Processing completed in {time.time() - start_time} seconds.")
