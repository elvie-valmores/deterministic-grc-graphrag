import streamlit as st
import requests
import os
from ingestion.pdf_extractor import CorporatePDFExtractor
from ingestion.llm_proxy import LLMProxy

# The URL of your running FastAPI server
API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="GRC Control Dashboard", layout="wide", page_icon="🛡️")
st.title("🛡️ Deterministic GRC Knowledge Platform")

# Create navigation tabs
tabs = st.tabs(["📄 Document Ingestion", "✅ Approval Queue", "🔍 Graph Search"])

# ==========================================
# TAB 1: AI DOCUMENT INGESTION
# ==========================================
with tabs[0]:
    st.header("Automated Policy Extraction")
    st.markdown("Upload a corporate policy PDF. The local AI will extract the core rules and stage them for review.")
    
    uploaded_file = st.file_uploader("Upload Corporate Policy (PDF)", type=["pdf"])
    
    if uploaded_file is not None:
        if st.button("Extract & Stage Data", type="primary"):
            with st.spinner("Analyzing document with Llama 3..."):
                # Save the uploaded file temporarily so PyMuPDF can read it
                temp_path = "temp_uploaded.pdf"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                try:
                    # 1. Run the Python Extraction Pipeline
                    extractor = CorporatePDFExtractor(temp_path)
                    raw_text = extractor.extract_raw_text()
                    clean_text = extractor.sanitize_for_llm(raw_text)
                    prompt = extractor.build_llm_prompt(clean_text)
                    
                    # 2. Send to Local LLM
                    proxy = LLMProxy()
                    extracted_json = proxy.process_text(prompt)
                    
                    st.success("✅ AI Extraction Complete!")
                    st.json(extracted_json)
                    
                    # 3. Post the data to our FastAPI Staging endpoint
                    response = requests.post(f"{API_BASE_URL}/staging/mappings", json=extracted_json)
                    
                    if response.status_code == 200:
                        st.info("💾 Mapping safely stored in PostgreSQL PENDING queue. Move to the Approval tab.")
                    else:
                        st.error(f"Failed to stage data: {response.text}")
                        
                except Exception as e:
                    st.error(f"Pipeline Error: {e}")
                finally:
                    # Clean up the temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

# ==========================================
# TAB 2: HUMAN-IN-THE-LOOP APPROVALS
# ==========================================
with tabs[1]:
    st.header("Human-in-the-Loop Approvals")
    st.markdown("Review AI-extracted mappings before committing them to the Neo4j Knowledge Graph.")
    
    col1, col2 = st.columns([1, 5])
    if col1.button("🔄 Refresh Queue"):
        pass # Streamlit natively reruns the script on button click
        
    try:
        response = requests.get(f"{API_BASE_URL}/staging/mappings/pending")
        if response.status_code == 200:
            pending_mappings = response.json()
            
            if not pending_mappings:
                st.success("No pending mappings. You're all caught up!")
            else:
                for mapping in pending_mappings:
                    # Create a collapsible box for each pending item
                    with st.expander(f"🚨 PENDING: {mapping['internal_policy']} -> {mapping['clause']}", expanded=True):
                        st.json(mapping)
                        
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("✅ Approve & Commit to Graph", key=f"approve_{mapping['id']}", type="primary", use_container_width=True):
                                # Call Approve Endpoint
                                app_res = requests.post(f"{API_BASE_URL}/staging/approve/{mapping['id']}")
                                # Call Commit Endpoint
                                com_res = requests.post(f"{API_BASE_URL}/staging/commit/{mapping['id']}")
                                
                                if app_res.status_code == 200 and com_res.status_code == 200:
                                    st.success(f"Mapping {mapping['id']} successfully committed to Neo4j!")
                                    st.rerun() # Refresh the UI
                                else:
                                    st.error("Error committing to graph.")
                                    
                        with btn_col2:
                            if st.button("🗑️ Soft Delete (Reject)", key=f"delete_{mapping['id']}", use_container_width=True):
                                del_res = requests.delete(f"{API_BASE_URL}/staging/mappings/{mapping['id']}")
                                if del_res.status_code == 200:
                                    st.warning(f"Mapping {mapping['id']} safely soft-deleted.")
                                    st.rerun() # Refresh the UI
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to FastAPI server. Please ensure `uvicorn api.main:app` is running.")

# ==========================================
# TAB 3: PARAMETRIC GRAPH SEARCH
# ==========================================
with tabs[2]:
    st.header("Query the Knowledge Graph")
    st.markdown("Search for an external regulation clause to see exactly which internal policies satisfy it.")
    
    search_clause = st.text_input("Enter Clause ID (e.g., GOVERN-1.1, Section 4.2)")
    
    if st.button("Search Graph", type="primary"):
        if search_clause:
            try:
                response = requests.get(f"{API_BASE_URL}/compliance/search?clause={search_clause}")
                if response.status_code == 200:
                    data = response.json()
                    st.metric("Total ACTIVE Policies Found", data["total_policies_found"])
                    
                    if data["data"]:
                        st.table(data["data"])
                    else:
                        st.info("No active policies are currently mapped to this clause.")
                else:
                    st.error(f"Search failed: {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a clause to search.")