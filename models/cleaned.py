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
import re
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
    
async def clean_education_history(education_details, resume_text, conversation):
    cleaned_education = []
    data = resume_collection.find_one()
    if not data:
        print("No resume found.")
        return []

    # Convert parsed JSON to a readable string
    resume_text = json.dumps(json.loads(data.get("resumeParseData", "{}")), indent=2)
    
    # Initial population from existing education details
    existing_education = {}
    if education_details and isinstance(education_details, list):
        for edu in education_details:
            key = (edu.get("institution", "").lower(), edu.get("degree", "").lower())
            existing_education[key] = {
                "degree": edu.get("degree", edu.get("specialization", "")),
                "institution": edu.get("institution", ""),
                "specialization": edu.get("specialization", ""),
                "year": edu.get("year", "")
            }

    # LLM-based comprehensive data extraction and filling
    prompt = f"""
    Thoroughly analyze the resume text and extract comprehensive educational information.
    Your goal is to fill in ALL missing or incomplete details about education.
    
    Current Known Education Details:
    {list(existing_education.values())}

    Comprehensive Extraction Requirements:
    - Extract EVERY possible detail about education
    - Fill in missing fields from the resume text
    - Prioritize completeness and accuracy
    - If multiple interpretations exist, choose the most likely one
    - Include any additional context that might help understand the education background

    Output Format (Strict JSON):
    [
      {{
        "degree": "Degree Name (MUST be filled)",
        "specialization": "Specific Field of Study (MUST be filled)",
        "institution": "Full University/College Name (MUST be filled)",
        "year": "Graduation Year or Study Period (MUST be filled)"
      }}
    ]

    IMPORTANT: Ensure NO empty fields. If unsure, use best guess or contextual inference.

    Resume Text:
    {resume_text}
    """

    try:
        response = conversation.run(prompt)
        response = response.strip("`")
        response = re.sub(r"^```(?:json)?\n|\n```$", "", response.strip(), flags=re.MULTILINE)

        # Ensure valid JSON structure
        response = response.lstrip()
        if not response.startswith("[") and not response.startswith("{"):
            response = response.split("\n", 1)[-1]  # Remove first invalid line

        parsed_education = json.loads(response)

        # Merge and update education entries
        for new_edu in parsed_education:
            key = (new_edu.get("institution", "").lower(), new_edu.get("degree", "").lower())

            if key in existing_education:
                # Update existing entry with more comprehensive information
                for field in ["degree", "specialization", "institution", "year"]:
                    if new_edu.get(field):
                        existing_education[key][field] = new_edu[field]
            else:
                # Add new entry if not already present
                existing_education[key] = {
                    "degree": new_edu.get("degree", ""),
                    "specialization": new_edu.get("specialization", ""),
                    "institution": new_edu.get("institution", ""),
                    "year": new_edu.get("year", "")
                }

    except (json.JSONDecodeError, TypeError) as parse_error:
        print(f"JSON Parsing Error: {parse_error}")
        print(f"Raw LLM Response: {response}")
    except Exception as e:
        print(f"Error in education extraction: {e}")

    # Final cleanup: remove empty entries
    cleaned_education = [
        edu for edu in existing_education.values()
        if all(edu.values())  # Ensures all fields are filled
    ]

    return cleaned_education

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

async def extract_projects_from_resume_parse(resume_parse_data, conversation, resume_text, dev_project_details):
    projects = []

    # Fetch data from database safely
    try:
        data = resume_collection.find_one() or {}
        dev_project_details = data.get("devProjectDetails", [])
        resume_parse_data = data.get("resumeParseData", {})
    except Exception as e:
        print(f"Error fetching data from database: {e}")
        dev_project_details = []

    # 1. Prioritize devProjectDetails
    if dev_project_details:
        return [
            {
                "project_name": project.get("name", ""),
                "tools_used/skill_used": project.get("techStack/tools", []),
                "Soft_skills": project.get("Soft_skills", []),
                "description": project.get("description", "")
            }
            for project in dev_project_details
        ]

    # 2. Extract projects from parsed resume data
    parsed_data = {}
    if isinstance(resume_parse_data, str):
        try:
            parsed_data = json.loads(resume_parse_data)
        except json.JSONDecodeError:
            print("Error decoding resumeParseData for project extraction.")
    elif isinstance(resume_parse_data, dict):
        parsed_data = resume_parse_data

    if parsed_data:
        parsed_projects = parsed_data.get("Projects", [])
        if parsed_projects:
            return await process_projects(parsed_projects, conversation)

        # 3. If no projects, check EmploymentHistory
        employment_history = parsed_data.get("EmploymentHistory", {}).get("Positions", [])
        employment_projects = await extract_projects_from_employment(conversation, employment_history)
        projects.extend(employment_projects)
    
    # 4. If no projects found, use LLM extraction from resume text
    if not projects:
        projects = await extract_projects_from_resume_text(conversation, resume_text)

    return projects

async def process_projects(parsed_projects, conversation):
    projects = []
    for project in parsed_projects:
        description = project.get("description", "")
        tools_used = project.get("tools_used/skill_used", [])
        soft_skills = project.get("Soft_skills", [])
        
        project_name = project.get("project_name", "")
        if isinstance(project_name, dict):
            project_name = project_name.get("Normalized", project_name.get("Raw", ""))

        # Remove unwanted fields like "Raw", "Normalized", "Probability"
        if isinstance(project_name, dict):
            project_name = project_name.get("Normalized", "")

        # Use LLM if details are missing
        if not tools_used or not soft_skills:
            extracted_data = await run_llm_extraction(conversation, description)
            tools_used = extracted_data.get("tools_used/skill_used", tools_used)
            soft_skills = extracted_data.get("Soft_skills", soft_skills)

        projects.append({
            "project_name": project_name,
            "tools_used/skill_used": tools_used,
            "Soft_skills": soft_skills,
            "description": description
        })
    return projects

async def extract_projects_from_employment(conversation, employment_history):
    projects = []
    for job in employment_history:
        job_title = job.get("JobTitle", "")
        description = job.get("Description", "")
        if description:
            extracted_data = await run_llm_extraction(conversation, description)
            projects.append({
                "project_name": job_title,
                "tools_used/skill_used": extracted_data.get("tools_used/skill_used", []),
                "Soft_skills": extracted_data.get("Soft_skills", []),
                "description": description
            })
    return projects

async def extract_projects_from_resume_text(conversation, resume_text):
    project_prompt = """
    Extract structured details from the given resume text.
    For each role, the "project_name" should be the job designation or appropriate role based on the description.
    Identify both technical tools used AND other skills demonstrated (e.g., leadership, collaboration, problem-solving, communication).

    Format the output in valid JSON with the following structure:

    [
        {
            "project_name": "<Job Designation>",
            "tools_used/skill_used": ["<Tool 1>", "<Tool 2>", ...],
            "Soft_skills": ["<Soft Skill 1>", "<Soft Skill 2>", ...],
            "description": "<Brief description of the role>"
        }
    ]

    Resume Text:
    {resume_text} 

    Return ONLY a valid JSON array. If no roles can be identified, return an empty JSON array:
    []
    """
    return await run_llm_json_extraction(conversation, project_prompt)

async def run_llm_extraction(conversation, description):
    prompt = f"""
    Extract the following details from the given description:
    - List of tools/technologies used
    - List of soft skills demonstrated
    
    Description:
    {description}

    Output in JSON:
    {{
      "tools_used/skill_used": ["Technology1", "Technology2"],
      "Soft_skills": ["Skill1", "Skill2"]
    }}
    """
    return await run_llm_json_extraction(conversation, prompt)

async def run_llm_json_extraction(conversation, prompt):
    try:
        response = conversation.run(prompt).strip()
        response = re.sub(r"^```(?:json)?\n|\n```$", "", response, flags=re.MULTILINE)
        extracted_data = json.loads(response) if response.startswith("{") or response.startswith("[") else []
        return extracted_data
    except (json.JSONDecodeError, TypeError):
        print("Error parsing JSON from LLM response.")
    except Exception as e:
        print(f"LLM extraction error: {e}")
    return []

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
    portfolio = data.get("devSocialProfile", {}).get("portfolio", "")

    # Skills: Combine and prioritize data.get("devSkills")
    candidate_skills = [skill.strip() for skill in data.get("devSkills", []) if skill.strip()]
    parsed_skills = extract_skills_from_resume_parse(resume_text)
    all_skills = sorted(list(set(candidate_skills + parsed_skills)))

    # Languages: Prioritize data.get("languages")
    candidate_languages = [lang.strip() for lang in data.get("languages", "").split(",") if lang.strip()]
    parsed_languages = [lang.get("Language", "").strip() for lang in resume_parse_data.get("LanguageCompetencies", []) if lang.get("Language")]
    all_languages = sorted(list(set(candidate_languages + parsed_languages)))

    employment_history = clean_employment_history(resume_parse_data.get("EmploymentHistory", {}).get("Positions", []))
    education = await clean_education_history(
        data.get("devAcademic", []), 
        resume_text, 
        conversation
    )
    #work preference
    work_preference=data.get("jobPreference","")
    work_experience = data.get("devTotalExperience", "")
    # Use the updated project extraction with conversation
    projects = await extract_projects_from_resume_parse(
        resume_text, 
        conversation, 
        resume_text, 
        data.get("devProjects", [])
    )

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
        "Work Experience": work_experience,
        "Education": education,
        "Employment History": employment_history,
        "Work Preference": work_preference,
        "Skills": all_skills,
        "Languages Known": all_languages,
        "Projects": projects
    }
    return cleaned_data


async def main():
    print("Processing resumes...")
    start_time = time.time()
    cleaned_data = await process_single_resume()


    if cleaned_data:
        # Save to JSON file
        with open("cleaned_resume.json", "w") as f:
            json.dump(cleaned_data, f, indent=4)


        # Optional: Save to MongoDB
        # cleaned_collection.insert_one(cleaned_data)

    print(f"Processing completed in {time.time() - start_time} seconds.")

if __name__ == "__main__":
    asyncio.run(main())


