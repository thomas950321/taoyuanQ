import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import sys
from rag_engine import ask_ai

def main():
    print("="*50)
    print("桃園Q 即時 AI 測試工具 (動態爬取官網內容)")
    print("="*50)
    print("提示：此版本會每次提問時即時訪問官網，確保資訊最新。")

    print("\n您可以開始提問了（輸入 'exit' 或 'quit' 結束測試）")
    
    while True:
        question = input("\n您的問題: ").strip()
        
        if question.lower() in ['exit', 'quit']:
            print("測試結束。")
            break
        
        if not question:
            continue
            
        print("正在爬取官網並由 AI 分析中，請稍候...")
        answer = ask_ai(question)
        print(f"\nAI 回答 (基於即時官網資料):\n{answer}")
        print("-" * 30)

if __name__ == "__main__":
    main()
