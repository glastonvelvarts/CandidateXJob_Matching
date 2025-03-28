from cleaned import process_single_resume
import json
import re
import datetime
import asyncio
from langchain_google_genai import GoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")

# Load the resume data
resume_data = asyncio.run(process_single_resume())

# Safely extract employment history
employment_history = resume_data.get("Employment History", [])
if employment_history:
    company_names = [entry.get("company") for entry in employment_history]

    from_dates = []
    to_dates = []

    for entry in employment_history:
        try:
            from_date = datetime.datetime.strptime(entry.get("from"), "%Y-%m-%d")
            from_dates.append(from_date)
        except (TypeError, ValueError):
            from_dates.append(None)

        to_date_raw = entry.get("to")
        if to_date_raw == "Present":  # Handle 'Present'
            to_dates.append(datetime.datetime.now())  # Set 'Present' to current date
        else:
            try:
                to_date = datetime.datetime.strptime(to_date_raw, "%Y-%m-%d")
                to_dates.append(to_date)
            except (TypeError, ValueError):
                to_dates.append(None)

    # Calculate differences (stability in months)
    stability = [
        (to_date - from_date).days // 30 if from_date and to_date else None
        for from_date, to_date in zip(from_dates, to_dates)
    ]

    # Prepare readable summary for analysis
    employment_summary = "\n".join([
        f"{company}: {months} months – {'Long tenure' if months >= 36 else 'Moderate tenure' if months >= 24 else 'Short tenure'}"
        for company, months in zip(company_names, stability) if months is not None
    ])

    # Feed data to LangChain for professional analysis
    llm = GoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GEMINI_API_KEY)
    prompt_template = PromptTemplate(
        input_variables=["employment_summary"],
        template=("Here is the employment summary: {employment_summary}. "
                  "Based on this data, please provide a professional analysis of job stability in line with company standards.")
    )
    chain = LLMChain(llm=llm, memory=ConversationBufferMemory(), prompt=prompt_template)

    # Run the analysis
    analysis = chain.run({"employment_summary": employment_summary})
    print("Analysis:")
    print(analysis)
else:
    print("No Employment History found.")