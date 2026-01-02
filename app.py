import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import datetime

# --- 1. AGENCY CONFIGURATION ---
AGENCY_NAME = "Inkroast"
AGENCY_URL = "https://www.inkroast.com"
BOOKING_LINK = "https://portal.inkroast.com/discovery"

# --- 2. CONFIGURATION & STYLING ---
st.set_page_config(page_title=f"{AGENCY_NAME} Store Auditor", page_icon="☕", layout="centered")

st.markdown("""
<style>
    /* Report Container */
    .report-container {
        background-color: #ffffff;
        padding: 40px;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
    }
    
    /* Typography */
    h1 { color: #1a1a1a; font-family: 'Arial', sans-serif; font-weight: 800; }
    h2 { color: #2c3e50; font-family: 'Arial', sans-serif; font-weight: 600; }
    
    /* "Generate Report" Button - INKROAST GREEN */
    .stButton>button { 
        width: 100%; 
        background-color: #008060; /* Shopify/Growth Green */
        color: white; 
        font-weight: bold; 
        border: none;
        padding: 14px;
        border-radius: 6px;
        font-size: 16px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #004c3f; /* Darker Green on Hover */
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* Success Message Box */
    .stSuccess {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #166534;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f1f3f4;
        border-radius: 4px;
        padding: 10px 20px;
        gap: 1px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e6fffa;
        color: #008060;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. AUTHENTICATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("⚠️ API Key missing. Please set GEMINI_API_KEY in Streamlit Secrets.")
    st.stop()

# --- 4. CORE FUNCTIONS ---

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
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2', 'h3'])]
        body = soup.get_text(separator=' ', strip=True)[:4500]
        
        return {
            "url": url,
            "title": title,
            "description": desc,
            "headings": headings[:20],
            "body": body
        }, None
    except Exception as e:
        return None, f"Scraping Error: {str(e)}"

def analyze_store_json(data):
    """Generates the Inkroast Strategic Audit."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a Senior Digital Strategist at {AGENCY_NAME}, a high-end Shopify Agency.
    
    Analyze this store:
    - URL: {data['url']}
    - Title: {data['title']}
    - Desc: {data['description']}
    - Content: {data['body'][:3500]}

    **Your Role:**
    Identify revenue leaks and opportunities for growth using the "Inkroast Method" (Brand + SEO + Tech).
    
    Return ONLY a valid raw JSON object with this exact structure:
    {{
        "executive_summary": "<2-3 sentence high-level summary of the store's potential.>",
        "score_breakdown": {{
             "score": <integer 1-10>,
             "reason": "<One sentence explaining the score.>"
        }},
        "branding_perception": {{
            "summary": "<Deep dive into brand identity and storytelling.>",
            "improvements": ["<Specific suggestion 1>", "<Specific suggestion 2>"]
        }},
        "seo_keyword_review": {{
            "analysis": "<Review of technical SEO and keywords.>",
            "keywords_detected": ["<Keyword 1>", "<Keyword 2>", "<Keyword 3>"],
            "keywords_recommended": ["<Better Keyword 1>", "<Better Keyword 2>", "<Long-tail Keyword 3>"]
        }},
        "traffic_strategies": [
            {{
                "title": "<Strategy Name (e.g. SEO Content Hub)>",
                "detail": "<Specific actionable advice.>",
                "impact": "High/Medium",
                "app": "<Recommended Shopify App (e.g. Plug In SEO)>",
                "service_match": "SEO Optimization"
            }},
            {{
                "title": "<Strategy Name (e.g. Email Retention)>",
                "detail": "<Specific actionable advice.>",
                "impact": "High/Medium",
                "app": "<Recommended Shopify App (e.g. Klaviyo)>",
                "service_match": "Email Automation Setup"
            }},
            {{
                "title": "<Strategy Name (e.g. Social Proof)>",
                "detail": "<Specific actionable advice.>",
                "impact": "High/Medium",
                "app": "<Recommended Shopify App (e.g. Judge.me, Loox)>",
                "service_match": "CRO Audit & Design"
            }}
        ]
    }}
    """
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json)
    except Exception as e:
        return {"error": str(e)}

def create_word_doc(audit, url):
    """Generates a formatted .docx file with Inkroast Branding."""
    doc = Document()
    
    # Title
    heading = doc.add_heading(f'{AGENCY_NAME} Strategic Audit', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Audited Site: {url}")
    current_date = datetime.date.today().strftime("%B %d, %Y")
    doc.add_paragraph(f"Date: {current_date}")
    doc.add_paragraph("_" * 50) 
    
    # Executive Summary
    doc.add_heading('Executive Summary', level=1)
    doc.add_paragraph(audit['executive_summary'])
    
    p_score = doc.add_paragraph()
    run_label = p_score.add_run("Marketing Health Score: ")
    run_label.bold = True
    run_score = p_score.add_run(f"{audit['score_breakdown']['score']}/10")
    run_score.bold = True
    run_score.font.color.rgb = RGBColor(0, 128, 96) # Green
    
    # Sections
    doc.add_heading('1. Branding & Identity', level=1)
    doc.add_paragraph(audit['branding_perception']['summary'])
    for imp in audit['branding_perception']['improvements']:
        doc.add_paragraph(imp, style='List Bullet')

    doc.add_heading('2. SEO & Keywords', level=1)
    doc.add_paragraph(audit['seo_keyword_review']['analysis'])
    
    # Traffic Strategies
    doc.add_heading('3. Growth Opportunities', level=1)
    for item in audit['traffic_strategies']:
        p = doc.add_paragraph(style='List Bullet')
        run_title = p.add_run(f"{item['title']}")
        run_title.bold = True
        
        p_detail = doc.add_paragraph(item['detail'])
        p_detail.paragraph_format.left_indent = Pt(18)
        
        # Tool & Service Recommendation
        p_meta = doc.add_paragraph()
        p_meta.paragraph_format.left_indent = Pt(18)
        run_tool = p_meta.add_run(f"Tool: {item['app']}  |  ")
        run_tool.italic = True
        run_service = p_meta.add_run(f"Inkroast Service: {item['service_match']}")
        run_service.bold = True
        run_service.font.color.rgb = RGBColor(0, 128, 96)
        
        doc.add_paragraph() # Spacer
        
    # --- AGENCY PITCH SECTION ---
    doc.add_page_break()
    doc.add_heading('Turn this Audit into Revenue', level=1)
    doc.add_paragraph("You have the roadmap, now you need the execution. Inkroast specializes in implementing these exact strategies for Shopify brands.")
    
    doc.add_heading('How we can help:', level=2)
    doc.add_paragraph("• Technical SEO Implementation", style='List Bullet')
    doc.add_paragraph("• Conversion Rate Optimization (CRO)", style='List Bullet')
    doc.add_paragraph("• Email & SMS Automation Setup", style='List Bullet')
    
    p_call = doc.add_paragraph()
    p_call.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_call = p_call.add_run("\nBook your free implementation review:\n")
    run_call.bold = True
    run_link = p_call.add_run(BOOKING_LINK)
    run_link.font.color.rgb = RGBColor(0, 0, 255)
    run_link.underline = True

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 5. THE UI LAYOUT ---

st.title(f"☕ {AGENCY_NAME} Store Analyst")
st.markdown("### Complimentary Brand & SEO Audit")
st.markdown("Enter your Shopify URL. Our AI Agent will analyze your brand and identify **opportunities where Inkroast can help you grow.**")

url_input = st.text_input("Store URL", placeholder="yourstore.com", label_visibility="collapsed")

if st.button("Generate My Report 🚀", type="primary"):
    if not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Analyzing brand identity and SEO structure..."):
            data, error = scrape_shopify_store(url_input)
            
            if error:
                st.error(error)
            else:
                audit = analyze_store_json(data)
                
                if "error" in audit:
                    st.error("Analysis failed. Please try again.")
                else:
                    # --- PREVIEW ---
                    st.success("✅ Analysis Complete.")
                    
                    with st.container(border=True):
                        st.subheader("Executive Summary")
                        st.write(audit['executive_summary'])
                        st.metric("Health Score", f"{audit['score_breakdown']['score']}/10")
                        
                        tab1, tab2, tab3 = st.tabs(["🎨 Brand", "🔍 SEO", "📈 Growth Plan"])
                        
                        with tab1:
                            st.write(audit['branding_perception']['summary'])
                            st.markdown("**Core Improvements:**")
                            for imp in audit['branding_perception']['improvements']:
                                st.markdown(f"- {imp}")
                        
                        with tab2:
                            st.write(audit['seo_keyword_review']['analysis'])
                            col1, col2 = st.columns(2)
                            with col1:
                                st.info("**Current Keywords**")
                                for k in audit['seo_keyword_review']['keywords_detected']:
                                    st.write(f"• {k}")
                            with col2:
                                st.success("**Missed Opportunities**")
                                for k in audit['seo_keyword_review']['keywords_recommended']:
                                    st.write(f"• {k}")
                                    
                        with tab3:
                            st.info("High-impact strategies we recommend for your store:")
                            for strat in audit['traffic_strategies']:
                                st.markdown(f"**{strat['title']}**")
                                st.write(strat['detail'])
                                
                                # The "Hybrid" Recommendation
                                st.markdown(f"""
                                <div style="background-color:#f9fafb; padding:10px; border-radius:5px; border-left: 3px solid #008060; font-size: 14px;">
                                    <strong>🛠 Tool:</strong> {strat['app']} <br>
                                    <strong>🚀 Service:</strong> {strat['service_match']}
                                </div>
                                """, unsafe_allow_html=True)
                                st.markdown("---")
                            
                            # CALL TO ACTION IN UI
                            st.markdown(f"### Ready to implement?")
                            st.link_button(
                                label="📅 Book a Discovery Call with Inkroast",
                                url=BOOKING_LINK,
                                use_container_width=True
                            )

                    # --- DOWNLOAD ---
                    doc_file = create_word_doc(audit, url_input)
                    
                    st.markdown("### 📥 Take this report with you")
                    st.download_button(
                        label="Download PDF Report (.docx)",
                        data=doc_file,
                        file_name=f"{AGENCY_NAME}_Audit_{url_input}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
