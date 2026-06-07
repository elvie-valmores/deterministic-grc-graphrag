import requests
import json
import re
import os
from ingestion.pdf_extractor import CorporatePDFExtractor

class LLMProxy:
    def __init__(self, model="llama3"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"

    def process_text(self, prompt: str):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "format": "json",  # Forces the model to stick to JSON structure
            "stream": False    # We want the full response at once
        }

        print(f"🤖 Sending prompt to {self.model}...")
        response = requests.post(self.url, json=payload)
        
        if response.status_code != 200:
            raise Exception(f"❌ LLM Error: {response.text}")
            
        raw_output = response.json()["response"]
        return self._sanitize_json(raw_output)

    def _sanitize_json(self, raw_text: str) -> dict:
        """
        Uses Regex to hunt for the JSON object in the LLM's chatter.
        """
        # Hunt for the first '{' and last '}'
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not match:
            raise Exception("❌ Parser Error: No valid JSON object found in LLM response.")
            
        json_str = match.group(0)
        return json.loads(json_str)

# --- End-to-End Ingestion Pipeline Test ---
if __name__ == "__main__":
    print("🚀 Starting End-to-End Ingestion Pipeline...")
    
    test_file = "dummy_policy.pdf"
    
    # Check if the PDF exists (it should from our last test)
    if not os.path.exists(test_file):
        print(f"⚠️ '{test_file}' not found. Please run 'python ingestion/pdf_extractor.py' first.")
        exit(1)
        
    # Step 1: Extract and clean the PDF text
    extractor = CorporatePDFExtractor(test_file)
    raw_text = extractor.extract_raw_text()
    clean_text = extractor.sanitize_for_llm(raw_text)
    
    # Step 2: Build the strict enterprise prompt
    final_prompt = extractor.build_llm_prompt(clean_text)
    print("✅ PDF Processed and Prompt Built.")
    
    # Step 3: Send to the Local LLM Proxy
    proxy = LLMProxy()
    try:
        result = proxy.process_text(final_prompt)
        print("\n🎉 SUCCESS! Final Database-Ready JSON:")
        # json.dumps makes it print out nicely formatted in the terminal
        print(json.dumps(result, indent=4))
    except Exception as e:
        print(f"\n❌ Pipeline Failed: {e}")