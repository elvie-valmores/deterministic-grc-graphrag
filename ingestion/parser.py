import json
import re
from typing import Dict, Any

def clean_llm_json(raw_response: str) -> Dict[str, Any]:
    """
    Middleware to strip conversational text and Markdown from LLM outputs.
    Ensures that only the core JSON object is passed to the parser.
    """
    # Use regex to find anything between the first { and the last }
    match = re.search(r'\{.*\}', raw_response, re.DOTALL)
    
    if match:
        clean_text = match.group(0)
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            # Passing the specific decode error up the chain helps with logging and debugging
            raise ValueError(f"LLM returned malformed JSON even after stripping: {e}")
    else:
        raise ValueError("No JSON object found in LLM response.")

def extract_compliance_data(llm_client, prompt: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    The Retry Loop: Forces the LLM to output valid JSON.
    If the LLM hallucinates markdown or bad JSON, it feeds the error back 
    to the LLM so it can correct its own mistake.
    """
    # Create a working copy of the prompt so we don't permanently mutate the original input
    current_prompt = prompt 
    
    for attempt in range(max_retries):
        try:
            # In a real scenario, this calls your local LLM (e.g., via Ollama/LangChain)
            raw_output = llm_client.generate(current_prompt) 
            
            # Pass the raw text through our sanitization middleware
            validated_json = clean_llm_json(raw_output)
            return validated_json
            
        except ValueError as e:
            print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
            # Append instructions to the prompt to tell the LLM exactly why it failed
            current_prompt += f"\n\nSystem Error: {e}. Please output ONLY valid JSON without markdown formatting."
            
    raise Exception("Max retries exceeded. LLM failed to return structured data.")