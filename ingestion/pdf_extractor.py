import fitz  # PyMuPDF
import re
import os

class CorporatePDFExtractor:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def extract_raw_text(self) -> str:
        """
        Reads the PDF and extracts raw text page by page.
        """
        print(f"📄 Loading PDF: {self.file_path}...")
        try:
            doc = fitz.open(self.file_path)
            full_text = ""
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Extract text preserving basic block layout
                full_text += page.get_text("text") + "\n"
                
            print(f"✅ Extracted {len(doc)} pages of text.")
            return full_text
            
        except Exception as e:
            raise Exception(f"❌ Failed to read PDF: {e}")

    def sanitize_for_llm(self, text: str) -> str:
        """
        PDF text is notoriously dirty (extra spaces, broken lines).
        This cleans it so we don't waste LLM tokens on garbage formatting.
        """
        # Replace 3+ newlines with a single double-newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Remove weird hidden unicode characters
        text = text.encode("ascii", "ignore").decode()
        return text.strip()

    def build_llm_prompt(self, cleaned_text: str) -> str:
        """
        Constructs the strict prompt for the Local LLM.
        This is the crucial 'Proxy' step where we force the AI to behave like a data clerk.
        """
        prompt = f"""You are an enterprise GRC auditor. Read the following corporate policy text and extract the core compliance rule.

You MUST format your response as a single, valid JSON object matching this exact Pydantic schema. 
Do NOT include markdown backticks (```json). Do NOT include conversational text. Return ONLY the JSON dictionary.

SCHEMA:
{{
    "framework": "Name of the standard (e.g., Internal AI Policy)",
    "clause": "The section, ID, or clause number",
    "internal_policy": "The title of the document",
    "relationship": "SATISFIES",
    "notes": "A 1-sentence summary of the rule"
}}

RAW DOCUMENT TEXT:
-------------------
{cleaned_text[:3000]} 
-------------------
"""
        return prompt

# --- Testing the Extractor ---
if __name__ == "__main__":
    test_file = "dummy_policy.pdf"
    
    # Auto-generate a dummy PDF for testing if it doesn't exist
    if not os.path.exists(test_file):
        print(f"⚠️ '{test_file}' not found. Generating a test PDF automatically...")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Corporate AI Policy - Section 4.2: All employees must use approved LLMs. Do not paste proprietary code into public AI models.")
        doc.save(test_file)
        doc.close()
        print(f"✅ Created '{test_file}' successfully!\n")

    extractor = CorporatePDFExtractor(test_file)
    raw_text = extractor.extract_raw_text()
    clean_text = extractor.sanitize_for_llm(raw_text)
    final_prompt = extractor.build_llm_prompt(clean_text)
    
    print("\n--- WHAT WE WILL SEND TO THE LLM ---")
    print(final_prompt)