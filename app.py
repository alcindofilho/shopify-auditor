import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import plotly.graph_objects as go
import json

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="Shopify Audit Pro", page_icon="⚡", layout="wide")

# Custom CSS for SaaS-like Polish
st.markdown("""
<style>
    /* Remove default top padding */
    .block-container {padding-top: 2rem;}
    
    /* Global Typography */
    h1, h2, h3 {font-family: 'Inter', sans-serif; color: #1a1a1a;}
    
    /* Metrics Cards */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* Action Plan Cards */
    .action-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        height: 100%;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .action-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    
    /* Pros/Cons Text */
    .pro-item { color: #008060; font-weight: 600; margin-bottom: 8px; }
    .con-item { color: #d82c0d; font-weight: 600; margin-bottom: 8px; }
    
    /* Button Styling */
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
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

# --- 3. HELPER FUNCTIONS ---

def create_gauge_chart(score):
    """Creates a professional speedometer chart for the score."""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Store Health Score", 'font': {'size': 20, 'color': "#333"}},
        gauge = {
            'axis': {'range': [None, 10], 'tickwidth': 1},
            'bar': {'color': "#008060"},  # Shopify Green
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e5e7eb",
            'steps': [
                {'range': [0, 4], 'color': '#fff1f0'}, # Red
                {'range': [4, 7], 'color': '#fffbe6'}, # Yellow
                {'range': [7, 10], 'color': '#f6ffed'} # Green
            ],
        }
    ))
    fig.update_layout(height=280, margin=dict(l=20,r=20,t=40,b=20))
    return fig

def scrape_shopify_store(url):
    """Scrapes the homepage for text content."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        url = url.strip()
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, f"Could not load site (Status: {response.status_code})"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Safe extraction
        title = soup.title.string if soup.title else "No Title"
        meta = soup.find('meta', attrs={'name': 'description'})
        desc = meta['content'] if meta else "No Meta Description"
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2'])]
        body = soup.get_text(separator=' ', strip=True)[:3000]
        
        return {
            "title": title,
            "description": desc,
            "headings": headings[:8],
            "body": body
        }, None
    except Exception as e:
        return None, f"Scraping Error: {str(e)}"

def analyze_store_json(data):
    """Sends data to Gemini and enforces JSON output."""
    # Using the robust model from your list
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a Senior Shopify Strategy Consultant. 
    Analyze this store data:
    - Title: {data['title']}
    - Desc: {data['description']}
    - Headings: {data['headings']}
    - Content: {data['body'][:2000]}

    Return ONLY a valid raw JSON object (no markdown, no code blocks) with this exact structure:
    {{
        "score": <integer 1-10>,
        "score_summary": "<short 10-word reason for score>",
        "hook_analysis": "<Professional critique of the H1/Hero section>",
        "seo_analysis": "<Technical critique of Title/Meta>",
        "pros": ["<Strong Point 1>", "<Strong Point 2>", "<Strong Point 3>"],
        "cons": ["<Critical Flaw 1>", "<Critical Flaw 2>", "<Critical Flaw 3>"],
        "quick_wins": [
            {{
                "title": "<Actionable Headline>",
                "why": "<One sentence explaining the lost revenue/opportunity>",
                "how": "<Specific technical instruction>",
                "impact": "High Impact",
                "effort": "Low Effort",
                "app": "<Specific Shopify App Name>"
            }},
            {{
                "title": "<Actionable Headline>",
                "why": "<One sentence explanation>",
                "how": "<Specific technical instruction>",
                "impact": "Medium Impact",
                "effort": "Medium Effort",
                "app": "<Specific Shopify App Name>"
            }},
            {{
                "title": "<Actionable Headline>",
                "why": "<One sentence explanation>",
                "how": "<Specific technical instruction>",
                "impact": "High Impact",
                "effort": "Low Effort",
                "app": "<Specific Shopify App Name>"
            }}
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

st.title("⚡ Shopify Store Audit Pro")
st.markdown("Enter your URL below to get a professional AI analysis of your conversion strategy.")

# Input Area
col_input, col_btn = st.columns([3, 1])
with col_input:
    url_input = st.text_input("Store URL", placeholder="brandname.com", label_visibility="collapsed")
with col_btn:
    analyze_btn = st.button("Audit Store 🚀", type="primary")

if analyze_btn:
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
                    # --- DASHBOARD HEADER ---
                    st.markdown("---")
                    
                    # Layout: Gauge (Left) + Executive Summary (Right)
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        fig = create_gauge_chart(audit['score'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        st.subheader("📝 Executive Summary")
                        st.info(f"**Verdict:** {audit['score_summary']}")
                        st.write(f"**🎯 Hook Check:** {audit['hook_analysis']}")
                        st.write(f"**🔍 SEO Check:** {audit['seo_analysis']}")

                    st.markdown("---")

                    # --- PROS & CONS GRID ---
                    col_left, col_right = st.columns(2)

                    with col_left:
                        st.subheader("✅ The Good")
                        for pro in audit['pros']:
                            st.markdown(f"<div class='pro-item'>✓ {pro}</div>", unsafe_allow_html=True)
                            
                    with col_right:
                        st.subheader("❌ The Bad")
                        for con in audit['cons']:
                            st.markdown(f"<div class='con-item'>✖ {con}</div>", unsafe_allow_html=True)

                    st.markdown("---")
                    
                    # --- ACTION PLAN (The Money Maker) ---
                    st.markdown("## 🚀 Your Growth Roadmap")
                    st.write("Prioritize these 3 actions to immediately improve conversion rates.")
                    
                    # Affiliate Links Map (Edit these!)
                    affiliate_links = {
                        "Judge.me": "https://judge.me/ref/YOUR_ID",
                        "Loox": "https://loox.io/app/YOUR_ID",
                        "Klaviyo": "https://klaviyo.com/partner/YOUR_ID",
                        "Privy": "https://privy.com/ref/YOUR_ID",
                        "PageFly": "https://pagefly.io?ref=YOUR_ID",
                        "ReConvert": "https://www.reconvert.io/?ref=YOUR_ID"
                    }

                    # Create 3 columns for the cards
                    cols = st.columns(3)
                    
                    for i, win in enumerate(audit['quick_wins']):
                        with cols[i]:
                            # Determine badge colors dynamically
                            badge_color = "#e6f4ea" if "High" in win['impact'] else "#fff4e5"
                            text_color = "#137333" if "High" in win['impact'] else "#b06000"
                            
                            # Render Card HTML
                            st.markdown(f"""
                            <div class="action-card">
                                <div style="display: flex; gap: 10px; margin-bottom: 12px;">
                                    <span style="background-color: {badge_color}; color: {text_color}; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                                        {win['impact']}
                                    </span>
                                    <span style="background-color: #f1f3f4; color: #5f6368; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                                        {win['effort']}
                                    </span>
                                </div>
                                <h4 style="margin: 0 0 10px 0; color: #202124; font-size: 16px;">
                                    {i+1}. {win['title']}
                                </h4>
                                <p style="font-size: 13px; color: #5f6368; line-height: 1.4; margin-bottom: 8px;">
                                    <strong>🛑 Problem:</strong> {win['why']}
                                </p>
                                <p style="font-size: 13px; color: #202124; line-height: 1.4;">
                                    <strong>💡 Strategy:</strong> {win['how']}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Smart Button Logic
                            st.write("") # Spacer
                            app_name = win['app']
                            # If no affiliate link, fallback to Shopify Search
                            link = affiliate_links.get(app_name, f"https://apps.shopify.com/search?q={app_name}")
                            
                            st.link_button(
                                label=f"Install {app_name} ↗", 
                                url=link, 
                                use_container_width=True
                            )
