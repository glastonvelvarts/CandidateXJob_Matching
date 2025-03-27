# # import asyncio
# # from langchain_google_genai import GoogleGenerativeAI
# # from langchain.prompts import PromptTemplate
# # from dotenv import load_dotenv
# # import os
# # import json
# # import re
# # from cleaned import process_single_resume

# # load_dotenv()

# # # Set up Gemini API key
# # GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# # GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# # # Initialize Gemini LLM
# # llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)

# # # Define prompt template with more explicit JSON instruction
# # prompt_template = PromptTemplate(
# #     input_variables=["projects_text"],
# #     template="""
# #     Extract structured project details from the given unstructured resume text. 
# #     Format the output in valid JSON with the following structure:

# #     [
# #         {{
# #             "project_name": "<Project Name>",
# #             "tools_used": ["<Tool 1>", "<Tool 2>", ...],
# #             "description": "<Brief description of project>"
# #         }}
# #     ]

# #     Text:
# #     {projects_text}

# #     Return ONLY the JSON with no other text, explanation or decorations:
# #     """
# # )

# # # Simplified function to just extract and return structured projects
# # def extract_projects_from_resume(cleaned_data):
# #     raw_projects = cleaned_data.get("Projects", [])
# #     if not raw_projects:
# #         print("No projects found in the resume.")
# #         return []
    
# #     # Combine all project-related text
# #     projects_text = "\n".join(map(str, raw_projects))

    
# #     try:
# #         # Use the newer pattern (prompt | llm) instead of deprecated LLMChain
# #         chain = prompt_template | llm
# #         response = chain.invoke({"projects_text": projects_text})
        
# #         # Try to extract JSON from the response
# #         response_text = str(response)
        
# #         # Clean up the response - often LLMs add markdown code blocks
# #         json_text = response_text
        
# #         # Remove markdown code blocks if present
# #         json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_text)
# #         if json_match:
# #             json_text = json_match.group(1)
# #         else:
# #             # Try without language specifier
# #             json_match = re.search(r'```\s*([\s\S]*?)\s*```', json_text)
# #             if json_match:
# #                 json_text = json_match.group(1)
        
# #         # Try to parse the cleaned text as JSON
# #         try:
# #             structured_projects = json.loads(json_text)
# #             return structured_projects
            
# #         except json.JSONDecodeError:
# #             print(f"Failed to parse response as JSON. Raw response:\n{json_text[:200]}...")
            
# #             # Fallback: Try to fix common JSON issues
# #             fixed_json = json_text.replace("'", '"')
# #             fixed_json = re.sub(r'(\w+):', r'"\1":', fixed_json)
            
# #             try:
# #                 structured_projects = json.loads(fixed_json)
# #                 print("Successfully parsed JSON after fixing format issues")
# #                 return structured_projects
# #             except json.JSONDecodeError:
# #                 print("Still couldn't parse JSON even after fixing common issues")
# #                 return []
        
# #     except Exception as e:
# #         print(f"Error processing projects: {str(e)}")
# #         return []

# # # Async wrapper function
# # async def main():
# #     # Get the cleaned resume data
# #     cleaned_data = await process_single_resume()
    
# #     # Extract structured projects
# #     structured_projects = extract_projects_from_resume(cleaned_data)
    
# #     # Print the structured projects
# #     print(json.dumps(structured_projects, indent=4))

# # # Run the async function
# # asyncio.run(main())

# import asyncio
# from langchain_google_genai import GoogleGenerativeAI
# from langchain.prompts import PromptTemplate
# from dotenv import load_dotenv
# import os
# import json
# import re
# import cleaned
# from cleaned import process_single_resume

# load_dotenv()

# # Set up Gemini API key
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# # Initialize Gemini LLM
# llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)



# # Define prompt template with more explicit JSON instruction
# prompt_template = PromptTemplate(
#     input_variables=["employment_history_text"],
#     template="""
#     Extract structured details from the given unstructured employment history text.
#     For each role, the "project_name" should be the job designation or appropriate role based on the description.
#     Identify both technical tools used AND other skills demonstrated (e.g., leadership, collaboration, problem-solving, communication).

#     Format the output in valid JSON with the following structure:

#     [
#         {{
#             "project_name": "<Job Designation>",
#             "tools_used/skill_used": ["<Tool 1>", "<Tool 2>", ...],
#             "Soft_skills": ["<Soft Skill 1>", "<Soft Skill 2>", ...],
#             "description": "<Brief description of the role>"
#         }}
#     ]

#     Text:
#     {employment_history_text}

#     Return ONLY a valid JSON array. If no roles can be identified, return an empty JSON array:
#     []
#     """
# )

# # Simplified function to extract structured projects from employment history
# def extract_projects_from_resume(cleaned_data):
#     employment_history = cleaned_data.get("Employment History", [])
#     if not employment_history:
#         print("No employment history found in the cleaned data.")
#         return []

#     employment_history_texts = []
#     for job in employment_history:
#         employment_history_texts.append(json.dumps(job))  # Convert each job dict to a string

#     employment_history_text = "\n".join(employment_history_texts)

#     try:
#         chain = prompt_template | llm
#         response = chain.invoke({"employment_history_text": employment_history_text})

#         response_text = str(response)
#         json_text = response_text

#         json_match = re.search(r'```json\s*([\s\S]*?)\s*```', json_text)
#         if json_match:
#             json_text = json_match.group(1)
#         else:
#             json_match = re.search(r'```\s*([\s\S]*?)\s*```', json_text)
#             if json_match:
#                 json_text = json_match.group(1)

#         try:
#             structured_projects = json.loads(json_text)
#             return structured_projects

#         except json.JSONDecodeError:
#             print(f"Failed to parse response as JSON. Raw response:\n{json_text[:200]}...")
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
#         print(f"Error processing employment history: {str(e)}")
#         return []

# # Async wrapper function
# async def main():
#     # Get the cleaned resume data
#     cleaned_data = await process_single_resume()

#     # Extract structured projects (now including other skills)
#     structured_projects = extract_projects_from_resume(cleaned_data)

#     # Print the structured projects
#     print(json.dumps(structured_projects, indent=4))

# # Run the async function
# asyncio.run(main())