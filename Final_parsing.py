import fitz
import re
import json
import spacy
import docx
import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

load_dotenv()
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Suppress GRPC warning
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = '0'

# Load NLP Model
nlp = spacy.load("en_core_web_md")

# Configure Google Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name=GEMINI_MODEL)

# Extract text from PDF (Ensuring all pages are extracted)
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"  # Extract text from all pages
    return text.strip()

# Extract text from Word document (docx)
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

# Extract text from Word document (doc) - requires antiword
def extract_text_from_doc(doc_path):
    try:
        import subprocess
        result = subprocess.run(["antiword", doc_path], stdout=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error extracting text from .doc file: {e}")
        return ""

# Extract email, phone, and name
def extract_contacts_and_name(text):
    EMAIL_PATTERN = r"[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+"
    PHONE_PATTERN = r"\+?\d{10,15}"

    emails = list(set(re.findall(EMAIL_PATTERN, text)))
    phones = list(set(re.findall(PHONE_PATTERN, text)))

    # Extract name (First line, assuming it contains the name)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    name = lines[0] if lines else "Unknown"

    return name, emails, phones

# Improved Skill Extraction (Searches entire document)
def extract_skills(text):
    skills_set = set()
    skill_keywords = ["skills", "technical skills", "technologies", "expertise"]

    lines = text.split("\n")
    for i, line in enumerate(lines):
        if any(word in line.lower() for word in skill_keywords):
            possible_skills = re.split(r",|\u2022|\||\n", lines[i + 1]) if i + 1 < len(lines) else []
            for skill in possible_skills:
                skill = skill.strip()
                if skill and len(skill) > 1:
                    skills_set.add(skill)

    return list(skills_set)

# Improved Section Extraction (Finds multiple sections across pages)
def extract_section(text, section_names):
    lines = text.split("\n")
    section_data = []
    start = -1

    for i, line in enumerate(lines):
        for name in section_names:
            if name.lower() in line.lower():
                start = i + 1
                break
        if start != -1:
            break

    if start == -1:
        return None

    for j in range(start, len(lines)):
        if any(lines[j].strip().lower().startswith(s.lower()) for s in section_names):
            break  # Stop at the next section title
        section_data.append(lines[j].strip())

    return list(filter(None, section_data))

def refine_with_gemini(data):
    """Refine the parsed resume data using Gemini API."""
    prompt = """You are a professional resume parser. Analyze and enhance the following resume data while maintaining the same JSON structure. Focus on:
1. Organizing and cleaning the text in each section
2. Identifying and separating distinct entries in education, work experience, etc.
3. Extracting dates, titles, and organizations where possible
4. Maintaining all original information while improving its presentation

Resume data to refine:
{data}

Return ONLY the refined JSON data with no additional text or markdown.""".format(data=json.dumps(data, indent=2))

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean up response and extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1]
        
        response_text = response_text.strip()
        
        try:
            refined_data = json.loads(response_text)
            return refined_data
        except json.JSONDecodeError:
            print("Failed to parse Gemini response as JSON. Using original data.")
            return data
            
    except Exception as e:
        print(f"Error in Gemini refinement: {e}")
        return data

def Resume_Parser(file_path):
    try:
        # Extract text based on file type
        if file_path.endswith(".pdf"):
            text = extract_text_from_pdf(file_path)
        elif file_path.endswith(".docx"):
            text = extract_text_from_docx(file_path)
        elif file_path.endswith(".doc"):
            text = extract_text_from_doc(file_path)
        else:
            print("Unsupported file format")
            return

        # Extract details
        name, emails, phones = extract_contacts_and_name(text)
        skills = extract_skills(text)
        data = {"name": name}
        if emails:
            data["emails"] = emails
        if phones:
            data["phone_numbers"] = phones
        if skills:
            data["skills"] = skills

        # Define sections
        sections = {
            "education": ["education"],
            "work_experience": ["experience", "work experience"],
            "projects": ["projects", "project experience"],
            "certifications": ["certifications", "certificates"],
            "volunteering": ["volunteering", "volunteer experience"],
            "publications": ["publications", "research papers"],
            "achievements": ["achievements", "awards"]
        }

        for key, section_names in sections.items():
            extracted_data = extract_section(text, section_names)
            if extracted_data:
                data[key] = extracted_data

        # Refine with Gemini and save single output
        final_data = refine_with_gemini(data)
        
        output_filename = "Resume_parsed.json"
        
        # Save final data to JSON file
        with open(output_filename, "w", encoding='utf-8') as json_file:
            json.dump(final_data, json_file, indent=4, ensure_ascii=False)
            print(f"Parsed resume data written to {output_filename}")
        return final_data
    except Exception as e:
        print(f"Error processing resume: {e}")


