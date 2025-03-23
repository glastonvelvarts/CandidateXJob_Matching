from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
from pymongo import MongoClient
import asyncio
import time

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
        return existing_value
    
    prompt = PromptTemplate(
        input_variables=["field_name", "resume_text"],
        template="Extract the {field_name} from the given resume text. If missing, return None.\nResume:\n{resume_text}"
    )
    loop = asyncio.get_event_loop()
    
    try:
        response = await loop.run_in_executor(None, conversation.run, prompt.format(field_name=field_name, resume_text=resume_text))
        return response.strip() if response else existing_value
    except Exception as e:
        print(f"Error fetching {field_name}: {e}")
        return existing_value
    
 
async def process_single_resume():
    data = resume_collection.find_one()
    if not data:
        print("No resume found.")
        return

    resume_text = data.get("resumeParseData", "")

    # ✅ Parallelize LLM calls using asyncio.gather()
    (
        full_name,
        email,
        phone_number,
        job_title,
        city,
        country_code,
        linkedin,
        github,
        portfolio,
        skills,
        languages,
        certifications,
    ) = await asyncio.gather(
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
        asyncio.gather(*[fill_missing_details("certification", cert.get("certificateName", ""), resume_text) for cert in data.get("devCertificates", [])])
    )

    # ✅ Parallel processing for Employment History
    employment_tasks = [
        asyncio.gather(
            fill_missing_details("designation", job.get("designation", ""), resume_text),
            fill_missing_details("company name", job.get("companyName", ""), resume_text),
            fill_missing_details("start date", job.get("from", ""), resume_text),
            fill_missing_details("end date", job.get("to", ""), resume_text),
            fill_missing_details("job location", job.get("location", ""), resume_text),
        )
        for job in data.get("devEmployment", []) if job.get("designation") or job.get("companyName")
    ]
    employment_results = await asyncio.gather(*employment_tasks)

    employment_history = [
        {
            "designation": res[0],
            "company": res[1],
            "from": res[2],
            "to": res[3],
            "location": res[4],
        }
        for res in employment_results
    ]

    # ✅ Parallel processing for Education
    education_tasks = [
        asyncio.gather(
            fill_missing_details("specialization", edu.get("specialization", ""), resume_text),
            fill_missing_details("institution", edu.get("institution", ""), resume_text),
            fill_missing_details("degree", edu.get("degree", ""), resume_text),
            fill_missing_details("graduation year", edu.get("year", ""), resume_text),
        )
        for edu in data.get("devAcademic", [])
    ]
    education_results = await asyncio.gather(*education_tasks)

    education = [
        {
            "specialization": res[0],
            "institution": res[1],
            "degree": res[2],
            "year": res[3],
        }
        for res in education_results
    ]

    # ✅ Construct final cleaned data
    cleaned_data = {
        "Full Name": full_name,
        "Email": email,
        "Phone Number": phone_number,
        "Current Job Title": job_title,
        "Current Salary (INR)": data.get("devCSalar", ""),
        "Expected Salary (INR)": data.get("devESalary", ""),
        "Notice Period": data.get("devNoticePeriod", ""),
        "City": city,
        "State": data.get("devState", ""),
        "Country Code": country_code,
        "Total Experience (Years)": data.get("devTotalExperience", ""),
        "LinkedIn Profile": linkedin,
        "GitHub Profile": github,
        "Portfolio Website": portfolio,
        "Education": education,
        "Employment History": employment_history,
        "Skills": [skill.strip() for skill in skills.split(",") if skill.strip()],
        "Certifications": certifications,
        "Languages Known": languages,
        "Job Preference": data.get("jobPreference", []),
    }

    return cleaned_data