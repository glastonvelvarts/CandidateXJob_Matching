# from langchain_google_genai import GoogleGenerativeAI
# from langchain.chains import ConversationChain
# from langchain.memory import ConversationBufferMemory
# from langchain.prompts import PromptTemplate
# from dotenv import load_dotenv
# import os
# from pymongo import MongoClient
# import asyncio
# import time
# import json

# load_dotenv()

# # Set up Gemini API key and model
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# # MongoDB connection
# MONGO_URI = os.getenv("MONGO_URI")
# client = MongoClient(MONGO_URI)
# db = client["CandidateMatch"]
# resume_collection = db["Resume_parsed"]
# cleaned_collection = db["Cleaned"]

# # LangChain model setup
# llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)
# conversation = ConversationChain(llm=llm, memory=ConversationBufferMemory())

# # Function to fill missing details using LLM (keeping for potential edge cases)
# async def fill_missing_details(field_name, existing_value, resume_text):
#     if existing_value and existing_value.strip():
#         return existing_value.strip()

#     prompt = f"""
#     FIND and Extract only the {field_name} from the given resume text.
#     If missing, return None. Return only the value without any explanations.
#     Resume:
#     {resume_text}
#     """
#     loop = asyncio.get_event_loop()

#     try:
#         response = await loop.run_in_executor(None, conversation.run, prompt)
#         if response:
#             response = response.strip()
#             if response.lower().startswith("none"):
#                 return None
#             return response
#         return None
#     except Exception as e:
#         print(f"Error fetching {field_name}: {e}")
#         return None

# def clean_employment_history(employment_positions):
#     cleaned_history = []
#     if employment_positions and isinstance(employment_positions, list):
#         for pos in employment_positions:
#             cleaned_history.append({
#                 "designation": pos.get("JobTitle", {}).get("Normalized", ""),
#                 "company": pos.get("Employer", {}).get("Name", {}).get("Normalized", ""),
#                 "from": pos.get("StartDate", {}).get("Date", "").split("T")[0],
#                 "to": pos.get("EndDate", {}).get("Date", "").split("T")[0] if pos.get("IsCurrent") is not True else "Present",
#                 "aboutRole": pos.get("Description", ""),
#                 "techUsed": [], # We can potentially extract these from the description later
#                 "toolUsed": [], # Same as techUsed
#                 "stillWorking": pos.get("IsCurrent", False),
#                 "location": pos.get("Employer", {}).get("Location", {}).get("Municipality", ""),
#             })
#     return cleaned_history

# def clean_education_history(education_details):
#     cleaned_education = []
#     if education_details and isinstance(education_details, list):
#         for edu in education_details:
#             cleaned_education.append({
#                 "specialization": ", ".join(edu.get("Majors", [])),
#                 "institution": edu.get("SchoolName", {}).get("Normalized", ""),
#                 "degree": edu.get("Degree", {}).get("Normalized", ""),
#                 "year": edu.get("LastEducationDate", {}).get("Date", "").split("-")[0] if edu.get("LastEducationDate", {}).get("FoundYear") else "",
#             })
#     return cleaned_education

# async def extract_projects_from_resume_parse(resume_parse_data):
#     projects = []
#     if isinstance(resume_parse_data, str):
#         try:
#             parsed_data = json.loads(resume_parse_data)
#             employment_history = parsed_data.get("EmploymentHistory", {}).get("Positions", [])
#             for job in employment_history:
#                 description = job.get("Description", "")
#                 if "project" in description.lower() or "developed" in description.lower() or "created" in description.lower():
#                     projects.append({
#                         "name": "",
#                         "description": description,
#                         "techStack": [],
#                         "tools": [],
#                         "githubLink": "",
#                         "duration": ""
#                     })
#         except json.JSONDecodeError as e:
#             print(f"Error decoding resumeParseData for project extraction: {e}")
#     return projects

# def extract_skills_from_resume_parse(resume_parse_data):
#     skills = []
#     if isinstance(resume_parse_data, str):
#         try:
#             parsed_data = json.loads(resume_parse_data)
#             skills_data_list = parsed_data.get("SkillsData", [])
#             for skills_data in skills_data_list:
#                 taxonomies = skills_data.get("Taxonomies", [])
#                 for taxonomy in taxonomies:
#                     sub_taxonomies = taxonomy.get("SubTaxonomies", [])
#                     for sub_taxonomy in sub_taxonomies:
#                         skill_list = sub_taxonomy.get("Skills", [])
#                         for skill_item in skill_list:
#                             skill_name = skill_item.get("Name")
#                             if skill_name and skill_name not in skills:
#                                 skills.append(skill_name)
#         except json.JSONDecodeError as e:
#             print(f"Error decoding resumeParseData for skill extraction: {e}")
#     return sorted(list(set(skills))) # Remove duplicates and sort

# async def process_single_resume():
#     data = resume_collection.find_one()
#     if not data:
#         print("No resume found.")
#         return

#     resume_text = data.get("resumeParseData", "")
#     resume_parse_data = json.loads(resume_text) if isinstance(resume_text, str) else {}
#     contact_info = resume_parse_data.get("ContactInformation", {})

#     full_name = f"{data.get('fName', '')} {data.get('lName', '')}".strip() or contact_info.get("FullName", {}).get("Raw", "")
#     email = data.get("email", "") or contact_info.get("EmailAddresses", [None])[0]
#     phone_number = data.get("number", "") or contact_info.get("Telephones", [{}])[0].get("Raw", "")
#     job_title = data.get("devDesg", "")
#     city = data.get("devCity", "") or contact_info.get("Location", {}).get("Municipality", "")
#     state = data.get("devState", "") or contact_info.get("Location", {}).get("Region", "")
#     country_code = data.get("devCountryCode", "") or contact_info.get("Location", {}).get("CountryCode", "")
#     linkedin = data.get("devSocialProfile", {}).get("linkedin", "")
#     github = data.get("devSocialProfile", {}).get("gitHub", "")
#     portfolio = data.get("portfolio", "")
#     languages_str = data.get("languages", "") or ", ".join([lang.get("Language", "") for lang in resume_parse_data.get("LanguageCompetencies", [])])

#     employment_history = clean_employment_history(resume_parse_data.get("EmploymentHistory", {}).get("Positions", []))
#     education = clean_education_history(resume_parse_data.get("Education", {}).get("EducationDetails", []))
#     projects = await extract_projects_from_resume_parse(resume_text)
#     skills = extract_skills_from_resume_parse(resume_text)

#     cleaned_data = {
#         "Full Name": full_name,
#         "Email": email,
#         "Phone Number": phone_number,
#         "Current Job Title": job_title,
#         "City": city,
#         "State": state,
#         "Country Code": country_code,
#         "LinkedIn Profile": linkedin,
#         "GitHub Profile": github,
#         "Portfolio Website": portfolio,
#         "Education": education,
#         "Employment History": employment_history,
#         "Skills": skills,
#         "Languages Known": [lang.strip() for lang in languages_str.split(",") if lang.strip()],
#         "Projects": projects
#     }
#     return cleaned_data

# print("Processing resumes...")
# start_time = time.time()
# cleaned_data = asyncio.run(process_single_resume())

# if cleaned_data:
#     # Save to JSON file
#     with open("cleaned_resume.json", "w") as f:
#         json.dump(cleaned_data, f, indent=4)

#     # Optional: Save to MongoDB
#     cleaned_collection.insert_one(cleaned_data)

# print(f"Processing completed in {time.time() - start_time} seconds.")

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

# Function to fill missing details using LLM (keeping for potential edge cases)
async def fill_missing_details(field_name, existing_value, resume_text):
    if existing_value and existing_value.strip():
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

def clean_employment_history(employment_positions):
    cleaned_history = []
    if employment_positions and isinstance(employment_positions, list):
        for pos in employment_positions:
            cleaned_history.append({
                "designation": pos.get("JobTitle", {}).get("Normalized", ""),
                "company": pos.get("Employer", {}).get("Name", {}).get("Normalized", ""),
                "from": pos.get("StartDate", {}).get("Date", "").split("T")[0],
                "to": pos.get("EndDate", {}).get("Date", "").split("T")[0] if pos.get("IsCurrent") is not True else "Present",
                "aboutRole": pos.get("Description", ""),
                "techUsed": [], # Can be further extracted using NLP
                "toolUsed": [], # Same as techUsed
                "stillWorking": pos.get("IsCurrent", False),
                "location": pos.get("Employer", {}).get("Location", {}).get("Municipality", ""),
            })
    return cleaned_history

def clean_education_history(education_details):
    cleaned_education = []
    if education_details and isinstance(education_details, list):
        for edu in education_details:
            degree_name = edu.get("Degree", {}).get("Normalized")
            if not degree_name:
                degree_name = edu.get("Name", {}).get("Normalized") # Check another potential location

            cleaned_education.append({
                "specialization": ", ".join(edu.get("Majors", [])),
                "institution": edu.get("SchoolName", {}).get("Normalized", ""),
                "degree": degree_name or "",
                "year": edu.get("LastEducationDate", {}).get("Date", "").split("-")[0] if edu.get("LastEducationDate", {}).get("FoundYear") else "",
            })
    return cleaned_education

async def extract_projects_from_resume_parse(resume_parse_data):
    projects = []
    if isinstance(resume_parse_data, str):
        try:
            parsed_data = json.loads(resume_parse_data)
            employment_history = parsed_data.get("EmploymentHistory", {}).get("Positions", [])
            for job in employment_history:
                description = job.get("Description", "")
                if "project" in description.lower() or "developed" in description.lower() or "created" in description.lower():
                    projects.append({
                        "name": "",
                        "description": description,
                        "techStack": [],
                        "tools": [],
                        "githubLink": "",
                        "duration": ""
                    })
        except json.JSONDecodeError as e:
            print(f"Error decoding resumeParseData for project extraction: {e}")
    return projects

def extract_skills_from_resume_parse(resume_parse_data):
    skills = set()
    if isinstance(resume_parse_data, str):
        try:
            parsed_data = json.loads(resume_parse_data)
            skills_data_list = parsed_data.get("SkillsData", [])
            for skills_data in skills_data_list:
                taxonomies = skills_data.get("Taxonomies", [])
                for taxonomy in taxonomies:
                    sub_taxonomies = taxonomy.get("SubTaxonomies", [])
                    for sub_taxonomy in sub_taxonomies:
                        skill_list = sub_taxonomy.get("Skills", [])
                        for skill_item in skill_list:
                            skill_name = skill_item.get("Name")
                            if skill_name:
                                skills.add(skill_name)
        except json.JSONDecodeError as e:
            print(f"Error decoding resumeParseData for skill extraction: {e}")
    return sorted(list(skills))

async def process_single_resume():
    data = resume_collection.find_one()
    if not data:
        print("No resume found.")
        return

    resume_text = data.get("resumeParseData", "")
    resume_parse_data = json.loads(resume_text) if isinstance(resume_text, str) else {}
    contact_info = resume_parse_data.get("ContactInformation", {})

    full_name = data.get("fName", "").strip() + " " + data.get("lName", "").strip() if data.get("fName") or data.get("lName") else contact_info.get("FullName", {}).get("Raw", "")
    email = data.get("email", "") or contact_info.get("EmailAddresses", [None])[0]
    phone_number = data.get("number", "") or contact_info.get("Telephones", [{}])[0].get("Raw", "")
    job_title = data.get("devDesg", "")
    city = data.get("devCity", "") or contact_info.get("Location", {}).get("Municipality", "")
    state = data.get("devState", "") or contact_info.get("Location", {}).get("Region", "")
    country_code = data.get("devCountryCode", "") or contact_info.get("Location", {}).get("CountryCode", "")
    linkedin = data.get("devSocialProfile", {}).get("linkedin", "")
    github = data.get("devSocialProfile", {}).get("gitHub", "")
    portfolio = data.get("portfolio", "")

    # Skills: Combine and prioritize data.get("devSkills")
    candidate_skills = [skill.strip() for skill in data.get("devSkills", []) if skill.strip()]
    parsed_skills = extract_skills_from_resume_parse(resume_text)
    all_skills = sorted(list(set(candidate_skills + parsed_skills)))

    # Languages: Prioritize data.get("languages")
    candidate_languages = [lang.strip() for lang in data.get("languages", "").split(",") if lang.strip()]
    parsed_languages = [lang.get("Language", "").strip() for lang in resume_parse_data.get("LanguageCompetencies", []) if lang.get("Language")]
    all_languages = sorted(list(set(candidate_languages + parsed_languages)))

    employment_history = clean_employment_history(resume_parse_data.get("EmploymentHistory", {}).get("Positions", []))
    education = clean_education_history(resume_parse_data.get("Education", {}).get("EducationDetails", []))
    projects = await extract_projects_from_resume_parse(resume_text)

    # Try to get current job title from resume if not provided
    if not job_title:
        job_title = await fill_missing_details("current job title", "", resume_text)

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
        "Employment History": employment_history,
        "Skills": all_skills,
        "Languages Known": all_languages,
        "Projects": projects
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
    # cleaned_collection.insert_one(cleaned_data)

print(f"Processing completed in {time.time() - start_time} seconds.")