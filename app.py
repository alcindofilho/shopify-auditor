import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import plotly.graph_objects as go
import json
import re

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="Shopify Audit Pro", page_icon="⚡", layout="wide")

# Custom CSS for SaaS-like Polish
st.markdown("""
<style>
    /* Remove default top padding */
    .block-container {padding-top: 2rem;}
    
    /* Card Styling */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Typography */
    h1 {font-family: 'Inter', sans-serif; font-weight: 700; color: #1a1a1a;}
    h3 {font-family: 'Inter', sans-serif; font-weight: 600; color: #333;}
    
    /* Pros/Cons Colors */
    .pro-item {color: #008060; font-weight: 500;}
    .con-item {color: #d82c0d; font-weight: 500;}
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Key missing. Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# --- 3. HELPER FUNCTIONS ---

def create_gauge_chart(score):
    """Creates a speedometer chart for the score."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Store Health Score", 'font': {'size': 24, 'color': "#333"}},
        gauge = {
            'axis': {'range': [None, 10], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#008060"},  # Shopify Green
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 5], 'color': '#ffe0e0'},
                {'range': [5, 8], 'color': '#fff4e0'},
                {'range': [8, 10], 'color': '#e0ffe0'}],
        }
    ))
    fig.update_layout(height=300, margin=dict(l=20,r=20,t=50,b=20))
    return fig

def scrape_shopify_store(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        url = url.strip()
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, f"Could not load site (Status: {response.status_code})"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return {
            "title": soup.title.string if soup.title else "No Title",
            "description": soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "No Description",
            "headings": [h.get_text().strip() for h in soup.find_all(['h1', 'h2'])][:8],
            "body": soup.get_text(separator=' ', strip=True)[:3000]
        }, None
    except Exception as e:
        return None, str(e)

def analyze_store_json(data):
    # We ask for JSON specifically to build the dashboard
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a specialized Shopify CRO Auditor. 
    Analyze this store data:
    - Title: {data['title']}
    - Desc: {data['description']}
    - Headings: {data['headings']}
    - Content: {data['body'][:2000]}

    Return ONLY a valid raw JSON object (no markdown formatting, no code blocks) with this exact structure:
    {{
        "score": <integer 1-10>,
        "score_summary": "<short 10-word reason for score>",
        "hook_analysis": "<2 sentences on the header/value prop>",
        "seo_analysis": "<2 sentences on title/meta>",
        "pros": ["<pro 1>", "<pro 2>", "<pro 3>"],
        "cons": ["<con 1>", "<con 2>", "<con 3>"],
        "quick_wins": [
            {{ "problem": "<problem>", "solution": "<action>", "app": "<Shopify App Name>" }},
            {{ "problem": "<problem>", "solution": "<action>", "app": "<Shopify App Name>" }},
            {{ "problem": "<problem>", "solution": "<action>", "app": "<Shopify App Name>" }}
        ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's pure JSON
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json)
    except Exception as e:
        return {"error": str(e)}

# --- 4. THE DASHBOARD UI ---

st.title("⚡ Shopify Store Grader")
st.markdown("Enter your URL below to get a professional AI audit.")

url_input = st.text_input("Store URL", placeholder="brandname.com")

if st.button("Generate Report", type="primary"):
    if not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("🕵️ Scanning store and calculating score..."):
            data, error = scrape_shopify_store(url_input)
            
            if error:
                st.error(error)
            else:
                audit = analyze_store_json(data)
                
                if "error" in audit:
                    st.error("AI Analysis failed. Please try again.")
                else:
                    # --- DASHBOARD HEADER (The "Pro" Look) ---
                    st.markdown("---")
                    
                    # Top Section: Score Gauge & Key Stats
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        # Display the Speedometer
                        fig = create_gauge_chart(audit['score'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("📝 Executive Summary")
                        st.info(f"**Verdict:** {audit['score_summary']}")
                        st.write(f"**First Impression:** {audit['hook_analysis']}")
                        st.write(f"**SEO Check:** {audit['seo_analysis']}")

                    st.markdown("---")

                    # --- DETAILED COLUMNS ---
                    col_left, col_right = st.columns(2)

                    with col_left:
                        st.subheader("✅ The Good")
                        for pro in audit['pros']:
                            st.markdown(f"🟢 {pro}")
                            
                    with col_right:
                        st.subheader("❌ The Bad")
                        for con in audit['cons']:
                            st.markdown(f"🔴 {con}")

                    st.markdown("---")
                    
                    # --- ACTION PLAN (The "Consultant" Value) ---
                    st.subheader("🚀 3-Step Action Plan")
                    
                    # Affiliate Links Map
                    affiliate_links = {
                        "Judge.me": "https://judge.me/ref/YOUR_ID",
                        "Loox": "https://loox.io/app/YOUR_ID",
                        "Klaviyo": "https://klaviyo.com/partner/YOUR_ID"
                    }

                    # Display Quick Wins as Cards
                    cols = st.columns(3)
                    for i, win in enumerate(audit['quick_wins']):
                        with cols[i]:
                            st.markdown(f"""
                            <div class="metric-card">
                                <h4>Step {i+1}</h4>
                                <p style="font-size: 14px; color: #666;">{win['problem']}</p>
                                <hr>
                                <p style="font-weight: bold;">{win['solution']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # App Recommendation Button
                            app_name = win['app']
                            link = affiliate_links.get(app_name, "#")
                            st.link_button(f"Install {app_name}", link, use_container_width=True)
