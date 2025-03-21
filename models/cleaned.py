# from langchain_google_genai import GoogleGenerativeAI
# from langchain.chains import ConversationChain
# from langchain.memory import ConversationBufferMemory
# from langchain.prompts import PromptTemplate
# from dotenv import load_dotenv
# import os
# from pymongo import MongoClient

# load_dotenv()
# print(os.getenv("GEMINI_API_KEY"))  # This should print your API key
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

# # Function to fill missing details using LLM
# def fill_missing_details(field_name, existing_value, resume_text):
#     if existing_value:  # If already filled, return as is
#         return existing_value
    
#     prompt = PromptTemplate(
#         input_variables=["field_name", "resume_text"],
#         template="Extract the {field_name} from the given resume text. If missing, return None.\nResume:\n{resume_text}"
#     )
#     response = conversation.run(prompt.format(field_name=field_name, resume_text=resume_text))
#     return response.strip() if response else existing_value

# # Process all resumes
# parsed_resumes = resume_collection.find()

# for data in parsed_resumes:
#     resume_text = data.get("resumeParseData", "")

#     # Extract and fill missing details
#     cleaned_data = {
#         "Full Name": fill_missing_details("full name", f"{data.get('fName', '')} {data.get('lName', '')}".strip(), resume_text),
#         "Email": fill_missing_details("email", data.get("email", ""), resume_text),
#         "Phone Number": fill_missing_details("phone number", data.get("number", ""), resume_text),
#         "Current Job Title": fill_missing_details("current job title", data.get("devDesg", ""), resume_text),
#         "Current Salary (INR)": data.get("devCSalar", ""),
#         "Expected Salary (INR)": data.get("devESalary", ""),
#         "Notice Period": data.get("devNoticePeriod", ""),
#         "City": fill_missing_details("city", data.get("devCity", ""), resume_text),
#         "State": data.get("devState", ""),
#         "Country Code": fill_missing_details("country code", data.get("devCountryCode", ""), resume_text),
#         "Total Experience (Years)": data.get("devTotalExperience", ""),
#         "Education": [
#             {
#                 "specialization": fill_missing_details("specialization", edu.get("specialization", ""), resume_text),
#                 "institution": fill_missing_details("institution", edu.get("institution", ""), resume_text)
#             }
#             for edu in data.get("devAcademic", [])
#         ],
#         "Employment History": [
#             {
#                 "designation": fill_missing_details("designation", job.get("designation", ""), resume_text),
#                 "company": fill_missing_details("company name", job.get("companyName", ""), resume_text),
#                 "from": fill_missing_details("start date", job.get("from", ""), resume_text),
#                 "to": fill_missing_details("end date", job.get("to", ""), resume_text),
#             }
#             for job in data.get("devEmployment", []) if job.get("designation") or job.get("companyName")
#         ],
#         "Skills": fill_missing_details("skills", ", ".join(data.get("devSkills", [])), resume_text).split(", "),
#         "Certifications": [
#             fill_missing_details("certification", cert.get("certificateName", ""), resume_text)
#             for cert in data.get("devCertificates", [])
#         ],
#         "Job Preference": data.get("jobPreference", [])
#     }

#     # Insert updated resume data into Cleaned collection
#     cleaned_collection.insert_one(cleaned_data)

# print("All parsed resumes have been enhanced and inserted into MongoDB.")

#from langchain_google_genai import GoogleGenerativeAI
# from langchain.chains import ConversationChain
# from langchain.memory import ConversationBufferMemory
# from langchain.prompts import PromptTemplate
# from dotenv import load_dotenv
# import os
# from pymongo import MongoClient
# import asyncio
# import time
# from concurrent.futures import ThreadPoolExecutor

# load_dotenv()
# print(os.getenv("GEMINI_API_KEY"))  # This should print your API key
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

# # Function to fill missing details using LLM (async for parallel execution)
# async def fill_missing_details(field_name, existing_value, resume_text):
#     if existing_value:  # If already filled, return as is
#         return existing_value
    
#     prompt = PromptTemplate(
#         input_variables=["field_name", "resume_text"],
#         template="Extract the {field_name} from the given resume text. If missing, return None.\nResume:\n{resume_text}"
#     )
#     loop = asyncio.get_event_loop()
    
#     try:
#         response = await loop.run_in_executor(None, conversation.run, prompt.format(field_name=field_name, resume_text=resume_text))
#         time.sleep(1)  # Rate limit delay
#         return response.strip() if response else existing_value
#     except Exception as e:
#         print(f"Error fetching {field_name}: {e}")
#         return existing_value

# # Function to process resumes in batches
# async def process_resumes():
#     BATCH_SIZE = 50  # Reduce batch size to prevent overload
#     executor = ThreadPoolExecutor(max_workers=5)  # Reduce parallel workers

#     while True:
#         parsed_resumes = resume_collection.find().limit(BATCH_SIZE)  # Reload cursor
#         batch = list(parsed_resumes)
#         if not batch:
#             break
        
#         tasks = []
#         for data in batch:
#             resume_text = data.get("resumeParseData", "")
#             tasks.append(asyncio.ensure_future(
#                 process_single_resume(data, resume_text)
#             ))
        
#         cleaned_batch = await asyncio.gather(*tasks)
#         cleaned_collection.insert_many(cleaned_batch)
#         print(f"Inserted {len(cleaned_batch)} resumes into Cleaned collection.")
#         time.sleep(2)  # Batch processing delay

# async def process_single_resume(data, resume_text):
#     return {
#         "Full Name": await fill_missing_details("full name", f"{data.get('fName', '')} {data.get('lName', '')}".strip(), resume_text),
#         "Email": await fill_missing_details("email", data.get("email", ""), resume_text),
#         "Phone Number": await fill_missing_details("phone number", data.get("number", ""), resume_text),
#         "Current Job Title": await fill_missing_details("current job title", data.get("devDesg", ""), resume_text),
#         "Current Salary (INR)": data.get("devCSalar", ""),
#         "Expected Salary (INR)": data.get("devESalary", ""),
#         "Notice Period": data.get("devNoticePeriod", ""),
#         "City": await fill_missing_details("city", data.get("devCity", ""), resume_text),
#         "State": data.get("devState", ""),
#         "Country Code": await fill_missing_details("country code", data.get("devCountryCode", ""), resume_text),
#         "Total Experience (Years)": data.get("devTotalExperience", ""),
#         "Education": [
#             {
#                 "specialization": await fill_missing_details("specialization", edu.get("specialization", ""), resume_text),
#                 "institution": await fill_missing_details("institution", edu.get("institution", ""), resume_text)
#             }
#             for edu in data.get("devAcademic", [])
#         ],
#         "Employment History": [
#             {
#                 "designation": await fill_missing_details("designation", job.get("designation", ""), resume_text),
#                 "company": await fill_missing_details("company name", job.get("companyName", ""), resume_text),
#                 "from": await fill_missing_details("start date", job.get("from", ""), resume_text),
#                 "to": await fill_missing_details("end date", job.get("to", ""), resume_text),
#             }
#             for job in data.get("devEmployment", []) if job.get("designation") or job.get("companyName")
#         ],
#         "Skills": (await fill_missing_details("skills", ", ".join(data.get("devSkills", [])), resume_text)).split(", "),
#         "Certifications": [
#             await fill_missing_details("certification", cert.get("certificateName", ""), resume_text)
#             for cert in data.get("devCertificates", [])
#         ],
#         "Job Preference": data.get("jobPreference", [])
#     }

# if __name__ == "__main__":
#     asyncio.run(process_resumes())
#     print("All parsed resumes have been enhanced and inserted into MongoDB.")

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
print(os.getenv("GEMINI_API_KEY"))  # This should print your API key
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

# Process the single resume
async def process_single_resume():
    data = resume_collection.find_one()
    if not data:
        print("No resume found.")
        return
    
    resume_text = data.get("resumeParseData", "")
    cleaned_data = {
        "Full Name": await fill_missing_details("full name", f"{data.get('fName', '')} {data.get('lName', '')}".strip(), resume_text),
        "Email": await fill_missing_details("email", data.get("email", ""), resume_text),
        "Phone Number": await fill_missing_details("phone number", data.get("number", ""), resume_text),
        "Current Job Title": await fill_missing_details("current job title", data.get("devDesg", ""), resume_text),
        "Current Salary (INR)": data.get("devCSalar", ""),
        "Expected Salary (INR)": data.get("devESalary", ""),
        "Notice Period": data.get("devNoticePeriod", ""),
        "City": await fill_missing_details("city", data.get("devCity", ""), resume_text),
        "State": data.get("devState", ""),
        "Country Code": await fill_missing_details("country code", data.get("devCountryCode", ""), resume_text),
        "Total Experience (Years)": data.get("devTotalExperience", ""),
        "Education": [
            {
                "specialization": await fill_missing_details("specialization", edu.get("specialization", ""), resume_text),
                "institution": await fill_missing_details("institution", edu.get("institution", ""), resume_text)
            }
            for edu in data.get("devAcademic", [])
        ],
        "Employment History": [
            {
                "designation": await fill_missing_details("designation", job.get("designation", ""), resume_text),
                "company": await fill_missing_details("company name", job.get("companyName", ""), resume_text),
                "from": await fill_missing_details("start date", job.get("from", ""), resume_text),
                "to": await fill_missing_details("end date", job.get("to", ""), resume_text),
            }
            for job in data.get("devEmployment", []) if job.get("designation") or job.get("companyName")
        ],
        "Skills": [skill.strip() for skill in (await fill_missing_details("skills", ", ".join(data.get("devSkills", [])), resume_text)).split(",") if skill.strip()],
        "Certifications": [
            await fill_missing_details("certification", cert.get("certificateName", ""), resume_text)
            for cert in data.get("devCertificates", [])
        ],
        "Job Preference": data.get("jobPreference", [])
    }
    
    cleaned_collection.insert_one(cleaned_data)
    print("Inserted 1 resume into Cleaned collection.")

if __name__ == "__main__":
    asyncio.run(process_single_resume())
    print("Processing complete.")

