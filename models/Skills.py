import asyncio
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import json
import re
from cleaned import process_single_resume

load_dotenv()
