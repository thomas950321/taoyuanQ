import sys
import os

# Add current path
sys.path.append(os.getcwd())

from rag_engine import ask_ai

def main():
    if len(sys.argv) > 1:
        # One-shot mode
        question = " ".join(sys.argv[1:])
        response = ask_ai(question)
        print(f"\nResponse:\n{response}")
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
                response = ask_ai(question)
                print(f"Bot: {response}\n")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()
