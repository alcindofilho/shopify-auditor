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

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Shopify Store Analyst", page_icon="📈", layout="centered")

# Custom CSS for the Digital Marketing Expert Look
st.markdown("""
<style>
    .report-container {
        background-color: #ffffff;
        padding: 40px;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
    }
    
    h1 { color: #000000; font-family: 'Arial', sans-serif; font-weight: bold; }
    h2 { color: #2c3e50; font-family: 'Arial', sans-serif; }
    
    /* Button Styling */
    .stButton>button { 
        width: 100%; 
        background-color: #2c3e50; /* Professional Navy */
        color: white; 
        font-weight: bold; 
        border: none;
        padding: 12px;
        border-radius: 4px;
    }
    .stButton>button:hover {
        background-color: #34495e;
    }
    
    /* Success Message */
    .stSuccess {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #166534;
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
        body = soup.get_text(separator=' ', strip=True)[:4000] # Increased limit for deeper analysis
        
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
    """Generates the Digital Marketing Audit using Gemini 2.5."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a digital marketing strategist specializing in Shopify and e-commerce.
    
    Analyze the following Shopify store data:
    - URL: {data['url']}
    - Title Tag: {data['title']}
    - Meta Description: {data['description']}
    - Headings: {data['headings']}
    - Content Snippet: {data['body'][:3000]}

    **Your Role:**
    1. Analyze Branding (Visual identity, tone, value prop).
    2. Audit SEO (Meta tags, keywords, structure).
    3. Perform Keyword Analysis (Targeting, intent, gaps).
    4. Provide Traffic Generation Strategies (Organic, Social, Email).

    **Tone:** Analytical but friendly, sophisticated, and specific. Avoid generic advice.

    Return ONLY a valid raw JSON object with this exact structure:
    {{
        "executive_summary": "<2-3 sentence high-level summary of the store's potential.>",
        "score_breakdown": {{
             "score": <integer 1-10>,
             "reason": "<One sentence explaining the score.>"
        }},
        "branding_perception": {{
            "summary": "<Deep dive into brand identity, consistency, and storytelling.>",
            "improvements": ["<Specific suggestion 1>", "<Specific suggestion 2>"]
        }},
        "seo_keyword_review": {{
            "analysis": "<Review of title tags, meta descriptions, and keyword targeting.>",
            "keywords_detected": ["<Keyword 1>", "<Keyword 2>", "<Keyword 3>"],
            "keywords_recommended": ["<Better Keyword 1>", "<Better Keyword 2>", "<Long-tail Keyword 3>"]
        }},
        "traffic_strategies": [
            {{
                "title": "<Strategy Name (e.g. Content Hub)>",
                "detail": "<Specific actionable advice on how to execute this.>",
                "impact": "High/Medium",
                "app": "<Optional: Recommended Shopify App>"
            }},
            {{
                "title": "<Strategy Name>",
                "detail": "<Specific actionable advice.>",
                "impact": "High/Medium",
                "app": "<Optional: Recommended Shopify App>"
            }},
            {{
                "title": "<Strategy Name>",
                "detail": "<Specific actionable advice.>",
                "impact": "High/Medium",
                "app": "<Optional: Recommended Shopify App>"
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
    """Generates a formatted .docx file based on the new 3-section structure."""
    doc = Document()
    
    # Title
    heading = doc.add_heading('Shopify Store Marketing Audit', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Audited Site: {url}")
    current_date = datetime.date.today().strftime("%B %d, %Y")
    doc.add_paragraph(f"Date: {current_date}")
    doc.add_paragraph("_" * 50) 
    
    # 0. Executive Summary & Score
    doc.add_heading('Executive Summary', level=1)
    doc.add_paragraph(audit['executive_summary'])
    
    p_score = doc.add_paragraph()
    run_label = p_score.add_run("Marketing Health Score: ")
    run_label.bold = True
    run_score = p_score.add_run(f"{audit['score_breakdown']['score']}/10")
    run_score.bold = True
    run_score.font.color.rgb = RGBColor(44, 62, 80) 
    
    # 1. Branding Perception Summary
    doc.add_heading('1. Branding Perception Summary', level=1)
    doc.add_paragraph(audit['branding_perception']['summary'])
    
    doc.add_heading(' Suggested Improvements:', level=3)
    for imp in audit['branding_perception']['improvements']:
        doc.add_paragraph(imp, style='List Bullet')

    # 2. SEO & Keyword Review
    doc.add_heading('2. SEO & Keyword Review', level=1)
    doc.add_paragraph(audit['seo_keyword_review']['analysis'])
    
    # Keyword Table
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Light Shading Accent 1'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Keywords Detected'
    hdr_cells[1].text = 'Recommended Keywords'
    
    row_cells = table.add_row().cells
    row_cells[0].text = '\n'.join(audit['seo_keyword_review']['keywords_detected'])
    row_cells[1].text = '\n'.join(audit['seo_keyword_review']['keywords_recommended'])
    
    doc.add_paragraph() # Spacer

    # 3. Traffic Generation Ideas
    doc.add_heading('3. Traffic Generation Ideas', level=1)
    for item in audit['traffic_strategies']:
        p = doc.add_paragraph(style='List Bullet')
        run_title = p.add_run(f"{item['title']}")
        run_title.bold = True
        
        p_detail = doc.add_paragraph(item['detail'])
        p_detail.paragraph_format.left_indent = Pt(18)
        
        if item['app']:
            p_app = doc.add_paragraph()
            p_app.paragraph_format.left_indent = Pt(18)
            run_app = p_app.add_run(f"Tool Suggestion: {item['app']}")
            run_app.italic = True
            run_app.font.color.rgb = RGBColor(100, 100, 100)
        
        doc.add_paragraph() 
        
    # Footer
    doc.add_page_break()
    p_footer = doc.add_paragraph("Report generated by AI Digital Marketing Analyst.")
    p_footer.style = 'Quote'

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. THE UI LAYOUT ---

st.title("🚀 Shopify Store Analyst")
st.markdown("### Digital Marketing & SEO Strategist")
st.markdown("Enter your Shopify URL to receive a comprehensive audit on **Branding**, **SEO**, and **Traffic Generation**.")

url_input = st.text_input("Store URL", placeholder="yourstore.com")

if st.button("Run Marketing Audit", type="primary"):
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
                    # --- PREVIEW SECTION ---
                    st.success("✅ Audit Complete! Download your report below.")
                    
                    with st.container(border=True):
                        st.subheader("Executive Summary")
                        st.write(audit['executive_summary'])
                        st.metric("Health Score", f"{audit['score_breakdown']['score']}/10")
                        
                        # Tabs for the sections
                        tab1, tab2, tab3 = st.tabs(["🎨 Branding", "🔍 SEO", "📈 Traffic"])
                        
                        with tab1:
                            st.write(audit['branding_perception']['summary'])
                            st.markdown("**Improvements:**")
                            for imp in audit['branding_perception']['improvements']:
                                st.markdown(f"- {imp}")
                        
                        with tab2:
                            st.write(audit['seo_keyword_review']['analysis'])
                            col_k1, col_k2 = st.columns(2)
                            with col_k1:
                                st.info("**Current Keywords**")
                                for k in audit['seo_keyword_review']['keywords_detected']:
                                    st.write(f"• {k}")
                            with col_k2:
                                st.success("**Recommended**")
                                for k in audit['seo_keyword_review']['keywords_recommended']:
                                    st.write(f"• {k}")
                                    
                        with tab3:
                            for strat in audit['traffic_strategies']:
                                st.markdown(f"**{strat['title']}**")
                                st.write(strat['detail'])
                                if strat['app']:
                                    st.caption(f"Tool: {strat['app']}")
                                st.markdown("---")

                    # --- DOWNLOAD BUTTON ---
                    doc_file = create_word_doc(audit, url_input)
                    
                    st.markdown("### 📥 Export Report")
                    st.download_button(
                        label="Download Marketing Audit (.docx)",
                        data=doc_file,
                        file_name=f"Marketing_Audit_{url_input}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
