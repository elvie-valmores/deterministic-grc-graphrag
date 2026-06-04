from ingestion.parser import extract_compliance_data

# 1. We create a "Mock" or "Fake" LLM client
class MockLLM:
    def generate(self, prompt: str) -> str:
        print("--> [Mock LLM] Generating a messy response...")
        # This is exactly what a real LLM usually outputs: conversational text + markdown
        return """
        Sure! Here is the mapping you requested based on the framework:
        
        ```json
        {
            "framework": "NIST AI RMF",
            "clause": "GOVERN-1.1",
            "internal_policy": "Corporate AI Risk Handbook",
            "relationship": "SATISFIES"
        }
        ```
        
        Let me know if you need anything else!
        """

# 2. We initialize our fake LLM
fake_llm = MockLLM()

# 3. We run our pipeline
print("Starting Ingestion Pipeline Test...\n")

try:
    # We pass the fake LLM and a fake prompt into your new function
    result = extract_compliance_data(llm_client=fake_llm, prompt="Map this policy for me.")
    
    print("\n✅ SUCCESS! The parser stripped the markdown and returned a clean Python Dictionary:")
    print(result)
    print(f"Data Type: {type(result)}")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")