import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

# 1. Page Config
st.set_page_config(page_title="Shopify Store Auditor", layout="centered")

# 2. Load API Key from Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except FileNotFoundError:
    st.error("Secrets file not found. Please add your GEMINI_API_KEY to Streamlit Secrets.")
    st.stop()
except Exception as e:
    st.error(f"Error configuring API: {e}")
    st.stop()

# 3. The Scraper Function (Unchanged)
def scrape_shopify_store(url):
    try:
        # Add a user agent
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None, "Failed to load website. It might be password protected."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc else "No Meta Description found"
        
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3'])]
        body_text = soup.get_text(separator=' ', strip=True)[:3000]
        
        return {
            "title": title,
            "description": description,
            "headings": headings[:10],
            "body": body_text
        }, None
        
    except Exception as e:
        return None, str(e)

# 4. The AI Analysis Function (Updated with Error Handling)
def analyze_store(data):
    # Try the Flash model first (Fast & Cheap)
    model_name = 'gemini-1.5-flash'
    
    try:
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        You are a specialized Shopify Store Consultant.
        Analyze the scraped data below to provide a strategic audit.
        
        Data:
        - Title: {data['title']}
        - Meta Description: {data['description']}
        - Main Headings: {data['headings']}
        - Page Content Snippet: {data['body'][:2000]}

        **Your Goal:** Identify gaps in Persuasion, SEO, and Trust, and recommend specific Shopify Ecosystem tools to fix them.

        Output a report in Markdown format with these exact sections:

        ### 1. 🚦 First Impression Score (1-10)
        *Give a score and a 1-sentence reason why.*

        ### 2. 🧠 Persuasion & Messaging
        *Analyze the "Hook" (First headline) and the "Value Prop". Are they clear? Do they solve a problem?*

        ### 3. 🔍 SEO Health Check
        *Critique the Title Tag and Meta Description. Are they keyword-rich?*

        ### 4. ✅ The Good (Pros)
        *Bullet points of 3 things they are doing well.*

        ### 5. ❌ The Bad (Cons)
        *Bullet points of 3 things hurting conversion.*

        ### 6. 🚀 3 Quick Wins (with App Recommendations)
        *Suggest 3 specific actionable changes. For every problem, suggest a specific Shopify App solution.*

        **Tone:** Professional, encouraging, but brutally honest about the flaws.
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        # If Flash fails, print the error in the app so we can see it, 
        # and try the older stable model 'gemini-pro'
        return f"Error with main model: {str(e)}. \n\n Please try refreshing the page."



# 5. The UI Layout
st.title("🛍️ AI Shopify Store Audit (Powered by Gemini)")
st.write("Get a free 1-minute critique of your store's persuasion, SEO, and branding.")

url_input = st.text_input("Enter your Shopify Store URL (e.g., mystore.com)")

if st.button("Audit My Store"):
    if not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Scanning store..."):
            data, error = scrape_shopify_store(url_input)
            
            if error:
                st.error(f"Error: {error}")
            else:
                st.success("Scan complete! Gemini is analyzing strategy...")
                report = analyze_store(data)
                st.markdown("---")
                st.markdown(report)
