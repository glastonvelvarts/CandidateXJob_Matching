import asyncio
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import json
import re
from cleaned import process_single_resume

load_dotenv()

# Set up Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Initialize Gemini LLM
llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)

# Define prompt template with more explicit JSON instruction
prompt_template = PromptTemplate(
    input_variables=["projects_text"],
    template="""
    Extract structured project details from the given unstructured resume text. 
    Format the output in valid JSON with the following structure:

    [
        {{
            "project_name": "<Project Name>",
            "tools_used": ["<Tool 1>", "<Tool 2>", ...],
            "description": "<Brief description of project>"
        }}
    ]

    Text:
    {projects_text}

    Return ONLY the JSON with no other text, explanation or decorations:
    """
)

# Simplified function to just extract and return structured projects
def extract_projects_from_resume(cleaned_data):
    raw_projects = cleaned_data.get("Projects", [])
    if not raw_projects:
        print("No projects found in the resume.")
        return []
    
    # Combine all project-related text
    projects_text = "\n".join(map(str, raw_projects))

    
    try:
        # Use the newer pattern (prompt | llm) instead of deprecated LLMChain
        chain = prompt_template | llm
        response = chain.invoke({"projects_text": projects_text})
        
        # Try to extract JSON from the response
        response_text = str(response)
        
        # Clean up the response - often LLMs add markdown code blocks
        json_text = response_text
        
        # Remove markdown code blocks if present
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_text)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try without language specifier
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', json_text)
            if json_match:
                json_text = json_match.group(1)
        
        # Try to parse the cleaned text as JSON
        try:
            structured_projects = json.loads(json_text)
            return structured_projects
            
        except json.JSONDecodeError:
            print(f"Failed to parse response as JSON. Raw response:\n{json_text[:200]}...")
            
            # Fallback: Try to fix common JSON issues
            fixed_json = json_text.replace("'", '"')
            fixed_json = re.sub(r'(\w+):', r'"\1":', fixed_json)
            
            try:
                structured_projects = json.loads(fixed_json)
                print("Successfully parsed JSON after fixing format issues")
                return structured_projects
            except json.JSONDecodeError:
                print("Still couldn't parse JSON even after fixing common issues")
                return []
        
    except Exception as e:
        print(f"Error processing projects: {str(e)}")
        return []

# Async wrapper function
async def main():
    # Get the cleaned resume data
    cleaned_data = await process_single_resume()
    
    # Extract structured projects
    structured_projects = extract_projects_from_resume(cleaned_data)
    
    # Print the structured projects
    print(json.dumps(structured_projects, indent=4))

# Run the async function
asyncio.run(main())



# import asyncio
# import requests
# from bs4 import BeautifulSoup
# from langchain_google_genai import GoogleGenerativeAI
# from langchain.prompts import PromptTemplate
# from dotenv import load_dotenv
# import os
# import json
# import re
# from cleaned import process_single_resume

# load_dotenv()

# # Set up Gemini API key
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# # Initialize Gemini LLM
# llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)

# # Define prompt template with more explicit JSON instruction
# prompt_template = PromptTemplate(
#     input_variables=["projects_text"],
#     template="""
#     Extract structured project details from the given unstructured resume text. 
#     Format the output in valid JSON with the following structure:

#     [
#         {{
#             "project_name": "<Project Name>",
#             "tools_used": ["<Tool 1>", "<Tool 2>", ...],
#             "description": "<Brief description of project>"
#         }}
#     ]

#     Text:
#     {projects_text}

#     Return ONLY the JSON with no other text, explanation or decorations:
#     """
# )

# def scrape_github_repositories(username):
#     """
#     Scrape public GitHub repositories for a given username
#     """
#     base_url = f"https://github.com/{username}"
#     # base_url=f"https://github.com/{glastonvelvarts}"
#     repos_url = f"{base_url}?tab=repositories"
    
#     try:
#         # Scrape repositories page
#         response = requests.get(repos_url)
#         response.raise_for_status()
        
#         # Parse HTML
#         soup = BeautifulSoup(response.text, 'html.parser')
        
#         # Find repository links
#         repo_items = soup.find_all('article', class_='Box-row')
        
#         # List to store project details
#         github_projects = []
#         skills = set()
        
#         for repo in repo_items:
#             # Extract repository name
#             repo_link = repo.find('a', itemprop='name')
#             if not repo_link:
#                 continue
            
#             repo_name = repo_link.text.strip()
#             repo_url = f"https://github.com{repo_link['href']}"
            
#             # Try to get repository details
#             try:
#                 repo_response = requests.get(repo_url)
#                 repo_response.raise_for_status()
#                 repo_soup = BeautifulSoup(repo_response.text, 'html.parser')
                
#                 # Extract description
#                 description_tag = repo_soup.find('meta', property='og:description')
#                 description = description_tag['content'] if description_tag else "No description"
                
#                 # Find programming languages
#                 language_tags = repo_soup.find_all('span', class_='color-fg-default text-bold mr-1')
#                 repo_languages = [lang.text.strip() for lang in language_tags]
                
#                 # Add languages to skills
#                 skills.update(repo_languages)
                
#                 # Project details
#                 project = {
#                     "project_name": repo_name,
#                     "description": description,
#                     "url": repo_url,
#                     "tools_used": repo_languages
#                 }
                
#                 github_projects.append(project)
                
#             except requests.RequestException as e:
#                 print(f"Error fetching details for {repo_name}: {e}")
        
#         return {
#             "projects": github_projects,
#             "skills": list(skills)
#         }
    
#     except requests.RequestException as e:
#         print(f"Error scraping GitHub repositories: {e}")
#         return {"projects": [], "skills": []}

# # Simplified function to just extract and return structured projects
# def extract_projects_from_resume(cleaned_data):
#     raw_projects = cleaned_data.get("Projects", [])
#     if not raw_projects:
#         print("No projects found in the resume.")
#         return []
    
#     # Combine all project-related text
#     projects_text = "\n".join(raw_projects)
    
#     try:
#         # Use the newer pattern (prompt | llm) instead of deprecated LLMChain
#         chain = prompt_template | llm
#         response = chain.invoke({"projects_text": projects_text})
        
#         # Try to extract JSON from the response
#         response_text = str(response)
        
#         # Clean up the response - often LLMs add markdown code blocks
#         json_text = response_text
        
#         # Remove markdown code blocks if present
#         json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_text)
#         if json_match:
#             json_text = json_match.group(1)
#         else:
#             # Try without language specifier
#             json_match = re.search(r'```\s*([\s\S]*?)\s*```', json_text)
#             if json_match:
#                 json_text = json_match.group(1)
        
#         # Try to parse the cleaned text as JSON
#         try:
#             structured_projects = json.loads(json_text)
#             return structured_projects
            
#         except json.JSONDecodeError:
#             print(f"Failed to parse response as JSON. Raw response:\n{json_text[:200]}...")
            
#             # Fallback: Try to fix common JSON issues
#             fixed_json = json_text.replace("'", '"')
#             fixed_json = re.sub(r'(\w+):', r'"\1":', fixed_json)
            
#             try:
#                 structured_projects = json.loads(fixed_json)
#                 print("Successfully parsed JSON after fixing format issues")
#                 return structured_projects
#             except json.JSONDecodeError:
#                 print("Still couldn't parse JSON even after fixing common issues")
#                 return []
        
#     except Exception as e:
#         print(f"Error processing projects: {str(e)}")
#         return []

# # Async wrapper function
# async def main():
#     # Get the cleaned resume data
#     cleaned_data = await process_single_resume()
    
#     # Extract GitHub username from cleaned data
#     github_username = cleaned_data.get("GitHub Profile", "")
    
#     # Initialize final projects list
#     all_projects = {
#         "resume_projects": [],
#         "github_projects": [],
#         "combined_projects": []
#     }
    
#     # Extract structured projects from resume
#     if cleaned_data.get("Projects"):
#         all_projects["resume_projects"] = extract_projects_from_resume(cleaned_data)
    
#     # Scrape GitHub projects if username exists
#     if github_username:
#         github_data = scrape_github_repositories(github_username)
#         all_projects["github_projects"] = github_data.get("projects", [])
    
#     # Combine projects with some deduplication logic
#     combined_projects = all_projects["resume_projects"].copy()
    
#     # Add GitHub projects that aren't already in resume projects
#     for gh_project in all_projects["github_projects"]:
#         # Check if project with same name doesn't already exist
#         if not any(proj.get("project_name") == gh_project["project_name"] for proj in combined_projects):
#             combined_projects.append(gh_project)
    
#     all_projects["combined_projects"] = combined_projects
    
#     # Print the final projects
#     print(json.dumps(all_projects, indent=4))

# # Run the async function
# if __name__ == "__main__":
#     asyncio.run(main())