import ast
import os

def run_code(code: str):
    # Save generated code to a temp file
    with open("temp_code.py", "w") as f:
        f.write(code)

    try:
        # Just check for syntax errors instead of running it
        with open("temp_code.py", "r") as f:
            source = f.read()
        
        ast.parse(source)  # This checks syntax without running the code
        return {"status": "success", "output": "Syntax check passed!"}

    except SyntaxError as e:
        return {"status": "error", "output": f"SyntaxError: {e}"}

    finally:
        if os.path.exists("temp_code.py"):
            os.remove("temp_code.py")


# Test it
if __name__ == "__main__":
    good_code = "print('Hello from the sandbox!')"
    result = run_code(good_code)
    print("Test 1:", result)

    bad_code = "def broken(:\n    pass"
    result = run_code(bad_code)
    print("Test 2:", result)