import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# 1. Page Config
st.set_page_config(page_title="Shopify Store Auditor", layout="centered")

# 2. Sidebar for API Key (or you can use Secrets for your own site)
st.sidebar.title("Configuration")
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
# Note: For your public tool, you will store your API key in Streamlit Secrets, not ask the user.

# 3. The Scraper Function
def scrape_shopify_store(url):
    try:
        # Add a user agent so the site knows we are a bot/browser
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        # Ensure URL has schema
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None, "Failed to load website. It might be password protected."
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract meaningful content
        title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc['content'] if meta_desc else "No Meta Description found"
        
        # Get all headings to understand structure
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3'])]
        
        # Get first 1000 words of body text
        body_text = soup.get_text(separator=' ', strip=True)[:3000]
        
        return {
            "title": title,
            "description": description,
            "headings": headings[:10], # Just the top 10 headings
            "body": body_text
        }, None
        
    except Exception as e:
        return None, str(e)

# 4. The AI Analysis Function
def analyze_store(data, api_key):
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    You are a world-class CRO (Conversion Rate Optimization) and Brand Strategist.
    Analyze the following scraped data from a Shopify store's landing page.
    
    Data:
    - Title: {data['title']}
    - Meta Description: {data['description']}
    - Main Headings: {data['headings']}
    - Page Content Snippet: {data['body'][:1500]}

    Output a strict report in Markdown format with these sections:
    1. **First Impression Score (1-10)**: Be honest.
    2. **Persuasion & Messaging**: Analyze the hook and value proposition.
    3. **SEO Check**: Critique the title and meta description.
    4. **Pros**: 3 things they are doing well.
    5. **Cons**: 3 things hurting their conversion.
    6. **3 Quick Wins**: Specific, actionable changes they can make in 1 hour.
    
    Tone: Professional, direct, and empathetic.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a helpful expert audit tool."},
                  {"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

# 5. The UI Layout
st.title("🛍️ AI Shopify Store Audit")
st.write("Get a free 1-minute critique of your store's persuasion, SEO, and branding.")

url_input = st.text_input("Enter your Shopify Store URL (e.g., mystore.com)")

if st.button("Audit My Store"):
    if not api_key:
        st.error("Please provide an API Key.")
    elif not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Scanning store... (This takes about 5 seconds)"):
            data, error = scrape_shopify_store(url_input)
            
            if error:
                st.error(f"Error: {error}")
            else:
                st.success("Scan complete! Analyzing persuasion and strategy...")
                report = analyze_store(data, api_key)
                st.markdown("---")
                st.markdown(report)