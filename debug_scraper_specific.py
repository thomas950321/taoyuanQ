import requests
from bs4 import BeautifulSoup

url = "https://a18.taoyuanq.com/zh/q-halloween"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

print(f"Fetching {url}...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Final URL: {response.url}")
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator='\n')
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        print(f"Content length: {len(clean_text)}")
        print("--- Start of Content ---")
        print(clean_text[:1000]) # Print first 1000 chars
        print("--- End of Preview ---")
        
        if "萬聖" in clean_text:
            print("Found keyword '萬聖' in content.")
        else:
            print("WARNING: Keyword '萬聖' NOT found in content.")
    else:
        print("Failed to retrieve content.")

except Exception as e:
    print(f"Error: {e}")
