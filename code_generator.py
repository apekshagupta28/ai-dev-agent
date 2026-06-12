from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_code(ticket_title, ticket_description):
    prompt = f"""
You are an expert Python developer.
Your job is to write clean, working Python code based on the task below.

Task Title: {ticket_title}
Task Description: {ticket_description}

Rules:
- Return ONLY the Python code, nothing else
- No explanations, no markdown, no backticks
- The code must be complete and runnable
- Only use these installed packages: flask
- Do NOT use flask_wtf, wtforms, or any external packages
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# Test it with your SCRUM-5 ticket
if __name__ == "__main__":
    title = "Build a login page in Flask"
    description = "Create a /login route with username and password fields"

    print("🤖 Generating code...")
    code = generate_code(title, description)
    print("=" * 40)
    print(code)
    print("=" * 40)