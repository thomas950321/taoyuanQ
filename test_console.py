import sys
import os

# Add current path
sys.path.append(os.getcwd())

from advanced_rag import query_rag_advanced as ask_ai, fetch_and_process_website

def main():
    print("Initializing RAG system (Fetching website data)...")
    try:
        fetch_and_process_website()
    except Exception as e:
        print(f"Initialization warning: {e}")

    if len(sys.argv) > 1:
        # One-shot mode
        question = " ".join(sys.argv[1:])
        response, usage = ask_ai(question, return_usage=True)
        print(f"\nResponse:\n{response}")
        print(f"\n[Token Usage] Input: {usage.get('prompt_tokens')}, Output: {usage.get('completion_tokens')}, Total: {usage.get('total_tokens')}")
    else:
        # Interactive mode
        print("=== TaoyuanQ Bot Console (Type 'exit' to quit) ===")
        while True:
            try:
                question = input("\nYou: ")
                if question.lower().strip() in ('exit', 'quit'):
                    break
                if not question.strip():
                    continue
                print("Bot is thinking...")
                response, usage = ask_ai(question, return_usage=True)
                print(f"Bot: {response}")
                print(f"\n[Token Usage] Input: {usage.get('prompt_tokens')}, Output: {usage.get('completion_tokens')}, Total: {usage.get('total_tokens')}\n")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
