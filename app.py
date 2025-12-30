import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="Shopify Auditor", page_icon="🛍️", layout="centered")

# Custom CSS to make it look like a Pro SaaS
st.markdown("""
<style>
    /* Hide Streamlit default branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom Title Style */
    h1 {
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        color: #1a1a1a;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    
    /* Style the analyze button */
    .stButton>button {
        width: 100%;
        background-color: #008060; /* Shopify Green */
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 5px;
        padding: 0.75rem 1rem;
    }
    .stButton>button:hover {
        background-color: #004c3f;
        color: white;
    }
    
    /* Style the report boxes */
    .report-box {
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. AUTHENTICATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Key missing. Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# --- 3. CORE FUNCTIONS ---

def scrape_shopify_store(url):
    """Scrapes the homepage for text content."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # Smart URL handling
        url = url.strip()
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None, f"Could not load site (Status: {response.status_code})"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract Key Data
        title = soup.title.string if soup.title else "No Title"
        meta = soup.find('meta', attrs={'name': 'description'})
        desc = meta['content'] if meta else "No Meta Description"
        
        # Get headings and body
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2'])]
        body_text = soup.get_text(separator=' ', strip=True)[:3000]
        
        return {
            "title": title,
            "description": desc,
            "headings": headings[:8],
            "body": body_text
        }, None
        
    except Exception as e:
        return None, f"Scraping Error: {str(e)}"

def analyze_store(data):
    """Sends data to Gemini 2.5 Flash for analysis."""
    
    # We use the specific model from your list
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    Act as a veteran Shopify CRO (Conversion Rate Optimization) expert. 
    Audit this store data:
    
    - URL Title: {data['title']}
    - Meta Description: {data['description']}
    - H1/H2 Headings: {data['headings']}
    - Page Content: {data['body'][:1500]}

    Create a strategic report in Markdown.
    
    Structure:
    1. **🚦 Score (1-10)**: Strict score. One sentence explanation.
    2. **🧠 Persuasion Check**: Does the header hook the user? Is the value prop clear?
    3. **🔍 SEO Check**: Critique the Title/Meta for keywords.
    4. **✅ The Good**: 3 bullet points of pros.
    5. **❌ The Bad**: 3 bullet points of cons (e.g. vague copy, no social proof).
    6. **🚀 3 Quick Wins (App Recommendations)**:
       - Suggest 3 specific fixes.
       - IMPORTANT: For each fix, recommend a specific Shopify App (e.g., "Install Judge.me for reviews" or "Use Klaviyo for email").
    """
    
    try:
        response = model.generate_content(prompt)
        report = response.text
        
        # --- BONUS: AFFILIATE LINK INJECTOR ---
        # Automatically turn app names into links (Replace # with your actual links later)
        affiliate_map = {
            "Klaviyo": "https://www.klaviyo.com/partner/signup?utm_source=YOUR_ID",
            "Loox": "https://loox.io/app/YOUR_ID",
            "Judge.me": "https://judge.me/ref/YOUR_ID",
            "PageFly": "https://pagefly.io?ref=YOUR_ID",
            "Privy": "https://privy.com?ref=YOUR_ID"
        }
        
        for app_name, link in affiliate_map.items():
            report = report.replace(app_name, f"[{app_name}]({link})")
            
        return report
        
    except Exception as e:
        return f"Error analyzing store: {str(e)}"

# --- 4. THE UI LAYOUT ---

st.title("🛍️ AI Shopify Auditor")
st.markdown("### Free Instant Store Review")
st.write("Paste your Shopify store URL below to get a breakdown of your Persuasion, SEO, and Design strategy.")

url_input = st.text_input("Store URL", placeholder="brandname.com", label_visibility="collapsed")

if st.button("Audit My Store ⚡"):
    if not url_input:
        st.warning("Please enter a URL first.")
    else:
        with st.status("🕵️ Analyzing store...", expanded=True) as status:
            st.write("Connecting to store...")
            data, error = scrape_shopify_store(url_input)
            
            if error:
                status.update(label="❌ Error", state="error")
                st.error(error)
            else:
                st.write("Reading content & strategy...")
                report = analyze_store(data)
                status.update(label="✅ Audit Complete!", state="complete")
                
                st.markdown("---")
                st.markdown(report)
                
                st.info("💡 Tip: Refresh the page to audit another store.")
