import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Shopify Audit Report", page_icon="📄", layout="centered")

# Custom CSS for a Clean Document Look
st.markdown("""
<style>
    .report-container {
        background-color: #ffffff;
        padding: 40px;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        font-family: 'Georgia', serif; /* Serif font for report feel */
        color: #333;
    }
    h1, h2, h3 { font-family: 'Helvetica', sans-serif; color: #1a1a1a; }
    .stButton>button { width: 100%; background-color: #008060; color: white; }
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
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = url.strip()
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, f"Could not load site (Status: {response.status_code})"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return {
            "url": url,
            "title": soup.title.string if soup.title else "No Title",
            "description": soup.find('meta', attrs={'name': 'description'})['content'] if soup.find('meta', attrs={'name': 'description'}) else "No Description",
            "headings": [h.get_text().strip() for h in soup.find_all(['h1', 'h2'])][:8],
            "body": soup.get_text(separator=' ', strip=True)[:3000]
        }, None
    except Exception as e:
        return None, f"Scraping Error: {str(e)}"

def analyze_store_json(data):
    """Generates a detailed text-heavy report in JSON."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a Senior Consultant creating a formal audit report for a client.
    
    Client URL: {data['url']}
    Client Data: 
    - Title: {data['title']}
    - Desc: {data['description']}
    - Content: {data['body'][:2000]}

    Return ONLY a valid raw JSON object with this structure:
    {{
        "executive_summary": "<A professional 3-sentence summary of the store's current status and potential.>",
        "score_breakdown": {{
             "score": <integer 1-10>,
             "reason": "<Formal explanation of the score>"
        }},
        "sections": [
            {{
                "title": "1. Persuasion & First Impressions",
                "content": "<Detailed paragraph analyzing the hook, value prop, and user journey. Use professional tone.>"
            }},
            {{
                "title": "2. SEO & Technical Health",
                "content": "<Detailed paragraph critiquing the meta tags, keywords, and content structure.>"
            }},
            {{
                "title": "3. Conversion Strategy",
                "content": "<Detailed paragraph regarding social proof, urgency, and calls to action.>"
            }}
        ],
        "action_plan": [
            {{
                "step": "Step 1: Optimize Trust",
                "detail": "<Specific advice on what to change regarding reviews/trust.>",
                "app": "Judge.me or Loox"
            }},
            {{
                "step": "Step 2: Capture & Retain",
                "detail": "<Specific advice on email capture/SMS.>",
                "app": "Klaviyo or Privy"
            }},
            {{
                "step": "Step 3: Increase Average Order Value",
                "detail": "<Specific advice on upsells or bundles.>",
                "app": "ReConvert or Bundles"
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
    doc.add_heading('Shopify Store Strategic Audit', 0)
    doc.add_paragraph(f"Audited Site: {url}")
    doc.add_paragraph(f"Date: {json.dumps('Today')}") # Simple date placeholder
    
    # Executive Summary
    doc.add_heading('Executive Summary', level=1)
    doc.add_paragraph(audit['executive_summary'])
    
    # Score
    p = doc.add_paragraph()
    run = p.add_run(f"Overall Health Score: {audit['score_breakdown']['score']}/10")
    run.bold = True
    run.font.color.rgb = RGBColor(0, 128, 96) # Shopify Green
    doc.add_paragraph(audit['score_breakdown']['reason'])
    
    # Detailed Sections
    for section in audit['sections']:
        doc.add_heading(section['title'], level=2)
        doc.add_paragraph(section['content'])
        
    # Action Plan
    doc.add_heading('Strategic Action Plan', level=1)
    for item in audit['action_plan']:
        p = doc.add_paragraph(style='List Bullet')
        runner = p.add_run(f"{item['step']}")
        runner.bold = True
        doc.add_paragraph(item['detail'], style='List Continue')
        doc.add_paragraph(f"Recommended Tool: {item['app']}", style='Macro Text Char') # Italicize
        
    # Disclaimer
    doc.add_page_break()
    doc.add_paragraph("This report was generated by AI Auditor. Some links may be affiliate links.", style='Quote')

    # Save to memory buffer
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. THE UI LAYOUT ---

st.title("📄 Professional Store Report Generator")
st.markdown("Generate a formal PDF/Docx ready report for your stakeholders.")

url_input = st.text_input("Enter Store URL", placeholder="brandname.com")

if st.button("Generate Report", type="primary"):
    if not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Analyzing store strategy..."):
            data, error = scrape_shopify_store(url_input)
            
            if error:
                st.error(error)
            else:
                audit = analyze_store_json(data)
                
                if "error" in audit:
                    st.error("Analysis failed. Please try again.")
                else:
                    # --- PREVIEW SECTION ---
                    st.success("Analysis Complete! Preview below.")
                    
                    with st.container(border=True):
                        st.subheader("Executive Summary")
                        st.write(audit['executive_summary'])
                        
                        st.metric("Health Score", f"{audit['score_breakdown']['score']}/10")
                        
                        st.subheader("Detailed Findings")
                        for sec in audit['sections']:
                            st.markdown(f"**{sec['title']}**")
                            st.write(sec['content'])
                            
                        st.subheader("Recommended Actions")
                        for action in audit['action_plan']:
                            st.markdown(f"**{action['step']}**: {action['detail']}")
                            st.caption(f"Tool: {action['app']}")

                    # --- DOWNLOAD BUTTON ---
                    # Create the file in memory
                    doc_file = create_word_doc(audit, url_input)
                    
                    st.markdown("### 📥 Export")
                    st.download_button(
                        label="Download Report for Google Docs (.docx)",
                        data=doc_file,
                        file_name=f"Audit_Report_{url_input}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
