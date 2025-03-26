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
    
    # First, check devAcademic for basic degree information
    if education_details and isinstance(education_details, list):
        for edu in education_details:
            # Prepare initial entry with degree from devAcademic
            current_edu = {
                "degree": edu.get("specialization", ""),
                "institution": edu.get("institution", ""),
                "specialization": "",  # We'll try to fill this
                "year": "",
            }
            cleaned_education.append(current_edu)

    # Use LLM to extract more detailed education information
    prompt = """
    From the given resume text, carefully extract detailed educational information:
    - For each educational entry, identify:
      1. Full Degree Name (e.g., Master of Science, Bachelor of Science)
      2. Specific Specialization/Major (e.g., Computer Science, Geology, Engineering)
      3. Institution Name
      4. Graduation Year or Study Period

    Provide the most comprehensive and accurate details possible. 
    If multiple degrees are found, list all.

    Output Format (as JSON):
    [
      {
        "degree": "Full Degree Name",
        "specialization": "Specific Field of Study",
        "institution": "University Name",
        "year": "Graduation Year"
      }
    ]

    Resume Text:
    """ + resume_text

    try:
        # If no previous education details, start with an empty list
        if not cleaned_education:
            cleaned_education = []

        # Run LLM extraction
        response = conversation.run(prompt)
        
        # Try to parse the response as JSON
        try:
            parsed_education = json.loads(response)
            
            # Merge or add new education details
            for edu in parsed_education:
                # Check if this entry already exists
                existing_entry = next((item for item in cleaned_education 
                                       if item['institution'] == edu.get('institution')), None)
                
                if existing_entry:
                    # Update existing entry with more detailed information
                    existing_entry['specialization'] = edu.get('specialization', existing_entry.get('specialization', ''))
                    existing_entry['degree'] = edu.get('degree', existing_entry.get('degree', ''))
                    existing_entry['year'] = edu.get('year', existing_entry.get('year', ''))
                else:
                    # Add new entry
                    cleaned_education.append({
                        "specialization": edu.get('specialization', ''),
                        "institution": edu.get('institution', ''),
                        "degree": edu.get('degree', ''),
                        "year": edu.get('year', '')
                    })
        
        except (json.JSONDecodeError, TypeError):
            print("Could not parse education details from LLM response")
    
    except Exception as e:
        print(f"Error extracting education details: {e}")
    
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

async def extract_projects_from_resume_parse(resume_parse_data, conversation, resume_text):
    projects = []
    
    # First, extract projects from parsed data
    if isinstance(resume_parse_data, str):
        try:
            parsed_data = json.loads(resume_parse_data)
            employment_history = parsed_data.get("EmploymentHistory", {}).get("Positions", [])
            
            for job in employment_history:
                description = job.get("Description", "")
                if any(keyword in description.lower() for keyword in ["project", "developed", "created", "implemented"]):
                    projects.append({
                        "name": "",
                        "description": description,
                        "techStack": [],
                        "tools": [],
                        "duration": ""
                    })
        except json.JSONDecodeError as e:
            print(f"Error decoding resumeParseData for project extraction: {e}")
    
    # If no projects found in parsed data, use LLM to extract more
    if not projects:
        project_prompt = """
        From the given resume text, carefully extract project details:
        - For each project, identify:
          1. Project Name
          2. Project Description
          3. Technologies/Tech Stack Used IF MENTIONED OTHERWISE use Project Description to extract them
          4. Tools Used IF MENTIONED OTHERWISE use Project Description to extract them
          5. Project Duration (approximate)

        Output Format (as JSON):
        [
          {
            "name": "Project Name",
            "description": "Detailed Project Description",
            "techStack": ["Technology1", "Technology2"],
            "tools": ["Tool1", "Tool2"],
            "duration": "e.g., 3 months, Summer 2022"
          }
        ]

        Resume Text:
        """ + resume_text

        try:
            response = conversation.run(project_prompt)
            
            try:
                parsed_projects = json.loads(response)
                
                for project in parsed_projects:
                    projects.append({
                        "name": project.get("name", ""),
                        "description": project.get("description", ""),
                        "techStack": project.get("techStack", []),
                        "tools": project.get("tools", []),
                        "duration": project.get("duration", "")
                    })
            
            except (json.JSONDecodeError, TypeError):
                print("Could not parse project details from LLM response")
        
        except Exception as e:
            print(f"Error extracting project details: {e}")
    
    return projects

def extract_project_details(devProjectDetails, resumeParseData, employmentDetails, llm):
    projects = set()
    
    # 1. Check if user has added projects in devProjectDetails
    if devProjectDetails:
        projects.update(devProjectDetails)
    
    # 2. Check if resumeParseData contains a 'Projects' section
    if resumeParseData.get("Projects"):
        projects.update(resumeParseData["Projects"])
    
    # 3. If no projects found, extract from employmentDetails using LLM
    if not projects and employmentDetails:
        extracted_projects = llm.extract_projects_from_employment(employmentDetails) or []
        projects.update(extracted_projects)
    
    return list(projects)


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
    
    # Use the updated project extraction with conversation
    projects = await extract_projects_from_resume_parse(resume_text, conversation, resume_text)
    dev_projects = data.get("devProjects", [])

    # Merge projects, avoiding duplicates
    if dev_projects:
        # Convert both lists to sets of tuples for comparison
        project_set = set(tuple(proj.items()) for proj in projects)
        
        for dev_proj in dev_projects:
            # Convert dev project to a tuple for comparison
            dev_proj_tuple = tuple(dev_proj.items())
            
            # Add only if not already in existing projects
            if dev_proj_tuple not in project_set:
                projects.append(dev_proj)

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


