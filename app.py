import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="API Connection Tester")

st.title("🔌 API Connection Tester")

# 1. Load Key
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    st.success(f"✅ Key found: {api_key[:5]}... (hidden)")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"❌ Key loading failed: {e}")
    st.stop()

# 2. Test Listing Models
st.write("Testing connection to Google...")

try:
    # This asks Google: "What models am I allowed to use?"
    models = list(genai.list_models())
    
    st.success("✅ Connection Successful! Here are your available models:")
    
    # Print the model names nicely
    valid_models = []
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            valid_models.append(m.name)
            st.code(m.name)
            
    if not valid_models:
        st.warning("⚠️ Connection worked, but no text-generation models were found. This is a region/permissions issue.")
        
except Exception as e:
    st.error("❌ Connection Failed.")
    st.error(f"Error Message: {e}")
    st.info("If the error says '403' or 'Permission Denied', your API key is invalid.")
    st.info("If the error says '400' or 'User location is not supported', you are in a blocked country (EU/UK).")
