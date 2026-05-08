from dotenv import load_dotenv
import os
from langchain_groq import ChatGroq

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

response = llm.invoke(
    "You are a DevOps AI agent. "
    "A server has 95% CPU usage and 500 errors per minute. "
    "What is the most likely root cause?"
)

print(response.content)