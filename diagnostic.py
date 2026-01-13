import os
import sys
from dotenv import load_dotenv

# Force reload of environment variables
load_dotenv(override=True)

print("=== Diagnostic Start ===")
print(f"Current Working Directory: {os.getcwd()}")
print(f"Python Executable: {sys.executable}")

# Check .env file existence
env_path = os.path.join(os.getcwd(), ".env")
print(f"Checking for .env at: {env_path}")
print(f".env exists: {os.path.exists(env_path)}")

# Check Environment Variables
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
print(f"OPENAI_API_KEY present: {bool(api_key)}")
if api_key:
    print(f"OPENAI_API_KEY prefix: {api_key[:10]}...")
    print(f"OPENAI_API_KEY length: {len(api_key)}")
else:
    print("WARNING: OPENAI_API_KEY is Missing or Empty!")

print(f"OPENAI_BASE_URL: {base_url}")

# Verify rag_engine import
try:
    import rag_engine
    print(f"Imported rag_engine from: {rag_engine.__file__}")
    
    # Check if the function object has the updated code (introspect)
    import inspect
    source = inspect.getsource(rag_engine.ask_ai)
    print("Checking ask_ai source code for debug prints...")
    if "Debug: Using API Key" in source:
        print("SUCCESS: rag_engine.ask_ai contains new debug code.")
    else:
        print("FAILURE: rag_engine.ask_ai DOES NOT contain new debug code. Old version loaded?")
        
except ImportError as e:
    print(f"Error importing rag_engine: {e}")

print("=== Diagnostic End ===")
