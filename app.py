import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Coffee SEO Strategist", page_icon="☕", layout="centered")

# Custom CSS for the Coffee SEO Consultant Look
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
    
    h1 { color: #2c1a12; font-family: 'Georgia', serif; font-weight: bold; }
    h2 { color: #4a3b32; font-family: 'Georgia', serif; }
    
    /* Button Styling */
    .stButton>button { 
        width: 100%; 
        background-color: #008060; /* Shopify Green for Growth */
        color: white; 
        font-weight: bold; 
        border: none;
        padding: 12px;
    }
    .stButton>button:hover {
        background-color: #004c3f;
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
        headings = [h.get_text().strip() for h in soup.find_all(['h1', 'h2'])]
        body = soup.get_text(separator=' ', strip=True)[:3500]
        
        return {
            "url": url,
            "title": title,
            "description": desc,
            "headings": headings[:15], # Increased headings to see more structure
            "body": body
        }, None
    except Exception as e:
        return None, f"Scraping Error: {str(e)}"

def analyze_store_json(data):
    """Generates a Coffee SEO & SEM Strategy Report using Gemini."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a Senior Digital Growth Strategist specializing in the Coffee Industry.
    Your expertise focuses on **SEO (Search Engine Optimization)**, **SEM (Paid Search)**, and **Customer Education**.

    Analyze this coffee store data:
    - URL: {data['url']}
    - Title Tag: {data['title']}
    - Meta Description: {data['description']}
    - Headings (H1/H2): {data['headings']}
    - Page Content: {data['body'][:2500]}

    **Your Goal:** Determine if this website is **findable on Google** and if it effectively **answers customer questions** about coffee.

    **Analysis Criteria:**
    1. **Findability (SEO):** Are they using high-intent keywords in their Title/Headings? (e.g., "Specialty Coffee Roaster," "Ethiopian Yirgacheffe," "Dark Roast Beans"). Or is it vague (e.g., "Welcome Home")?
    2. **Educational Value (Q&A):** Does the content answer *how* to brew, roast levels, or flavor notes? Coffee buyers have questions; does this site answer them?
    3. **SEM Readiness:** If they ran Google Ads today, is the landing page clear enough to convert cold traffic?

    Return ONLY a valid raw JSON object with this exact structure:
    {{
        "executive_summary": "<A 3-sentence high-level critique. Focus on their organic visibility and if they are positioning themselves as an authority on coffee.>",
        "score_breakdown": {{
             "score": <integer 1-10>,
             "reason": "<One sentence explaining the score based on SEO and Content depth.>"
        }},
        "sections": [
            {{
                "title": "1. SEO & Search Visibility",
                "content": "<Critique the Title Tag and Headings. Are they targeting specific coffee niches (e.g., 'Cold Brew', 'Espresso') or are they invisible to search engines? Mention specific missing keywords.>"
            }},
            {{
                "title": "2. Customer Q&A & Education",
                "content": "<Coffee buyers have questions. Does this site provide Tasting Notes, Brewing Guides, or Origin stories? Critique the depth of information.>"
            }},
            {{
                "title": "3. SEM & Ad Readiness",
                "content": "<If they paid for clicks, would this page convert? Is the Value Proposition immediate? Is there trust (reviews/badges) above the fold?>"
            }}
        ],
        "action_plan": [
            {{
                "step": "Step 1: Fix Technical SEO",
                "detail": "<Specific advice on Title Tags or Meta Descriptions to rank for terms like 'Fresh Roasted Coffee'.>",
                "app": "Plug In SEO or SEO Manager"
            }},
            {{
                "step": "Step 2: Build 'Answer' Content",
                "detail": "<Create content that answers specific questions (e.g., 'Grind size for V60'). Add an FAQ section.>",
                "app": "HelpCenter | FAQ Chat or Easy FAQ"
            }},
            {{
                "step": "Step 3: Trust for Paid Traffic",
                "detail": "<Add visible reviews or 'As seen in' logos to lower Cost Per Acquisition (CPA) on ads.>",
                "app": "Judge.me or Google Customer Reviews"
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
    """Generates a formatted .docx file."""
    doc = Document()
    
    # Title
    heading = doc.add_heading('Coffee SEO & Search Strategy Audit', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph(f"Audited Site: {url}")
    current_date = datetime.date.today().strftime("%B %d, %Y")
    doc.add_paragraph(f"Date: {current_date}")
    doc.add_paragraph("_" * 50) 
    
    # Executive Summary
    doc.add_heading('1. Executive Summary', level=1)
    doc.add_paragraph(audit['executive_summary'])
    
    # Score Section
    p_score = doc.add_paragraph()
    run_label = p_score.add_run("Search Visibility Score: ")
    run_label.bold = True
    
    run_score = p_score.add_run(f"{audit['score_breakdown']['score']}/10")
    run_score.bold = True
    run_score.font.color.rgb = RGBColor(0, 128, 96) # Growth Green
    
    doc.add_paragraph(audit['score_breakdown']['reason'])
    
    # Detailed Sections
    for section in audit['sections']:
        doc.add_heading(section['title'], level=2)
        doc.add_paragraph(section['content'])
        
    # Action Plan
    doc.add_heading('Strategic Action Plan', level=1)
    for item in audit['action_plan']:
        p = doc.add_paragraph(style='List Bullet')
        run_step = p.add_run(f"{item['step']}")
        run_step.bold = True
        
        p_detail = doc.add_paragraph(item['detail'])
        p_detail.paragraph_format.left_indent = Pt(18)
        
        p_tool = doc.add_paragraph()
        p_tool.paragraph_format.left_indent = Pt(18)
        run_tool = p_tool.add_run(f"Recommended Tool: {item['app']}")
        run_tool.italic = True
        run_tool.font.color.rgb = RGBColor(100, 100, 100)
        
        doc.add_paragraph() 
        
    # Footer
    doc.add_page_break()
    p_footer = doc.add_paragraph("Report generated by AI Coffee Growth Consultant.")
    p_footer.style = 'Quote'

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. THE UI LAYOUT ---

st.title("☕ Coffee SEO & Growth Auditor")
st.markdown("### Search & Content Analysis for Roasters")
st.markdown("Enter your Shopify URL to analyze if your store is **Findable on Google** and answers customer questions effectively.")

url_input = st.text_input("Store URL", placeholder="coffeeroaster.com")

if st.button("Analyze Search Visibility", type="primary"):
    if not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Analyzing Keywords, Meta Tags, and Content Depth..."):
            data, error = scrape_shopify_store(url_input)
            
            if error:
                st.error(error)
            else:
                audit = analyze_store_json(data)
                
                if "error" in audit:
                    st.error("Analysis failed. Please try again.")
                else:
                    # --- PREVIEW SECTION ---
                    st.success("✅ SEO Audit Complete! Download your report below.")
                    
                    with st.container(border=True):
                        st.subheader("Executive Summary")
                        st.write(audit['executive_summary'])
                        
                        st.metric("Visibility Score", f"{audit['score_breakdown']['score']}/10")
                        
                        st.subheader("Key Findings")
                        for sec in audit['sections']:
                            with st.expander(f"📌 {sec['title']}", expanded=True):
                                st.write(sec['content'])
                            
                        st.subheader("Recommended Actions")
                        for action in audit['action_plan']:
                            st.info(f"**{action['step']}**: {action['detail']}")

                    # --- DOWNLOAD BUTTON ---
                    doc_file = create_word_doc(audit, url_input)
                    
                    st.markdown("### 📥 Export to Google Docs / Word")
                    st.download_button(
                        label="Download SEO Strategy Report (.docx)",
                        data=doc_file,
                        file_name=f"Coffee_SEO_Audit_{url_input}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
