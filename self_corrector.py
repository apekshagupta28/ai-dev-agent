from code_generator import generate_code
from code_executor import run_code

def generate_and_fix(title, description, max_retries=3):
    code = generate_code(title, description)
    
    for attempt in range(1, max_retries + 1):
        print(f"\n🔄 Attempt {attempt}/{max_retries}")
        print("🧪 Testing code in sandbox...")
        
        result = run_code(code)
        
        if result["status"] == "success":
            print("✅ Code passed!")
            return code
        else:
            print(f"❌ Error found:\n{result['output']}")
            
            if attempt < max_retries:
                print("🤖 Asking AI to fix it...")
                code = fix_code(code, result["output"])
            else:
                print("❌ Max retries reached. Could not fix code.")
                return None
    
    return None


def fix_code(broken_code, error_message):
    from groq import Groq
    import os
    from dotenv import load_dotenv
    load_dotenv()

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""
You are an expert Python developer.
The following code has an error. Fix it and return ONLY the corrected code.
No explanations, no markdown, no backticks.

Broken Code:
{broken_code}

Error:
{error_message}
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# Test it
if __name__ == "__main__":
    title = "Build a login page in Flask"
    description = "Create a /login route with username and password fields"
    
    final_code = generate_and_fix(title, description)
    
    if final_code:
        print("\n✅ Final working code is ready!")