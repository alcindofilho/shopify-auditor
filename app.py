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
st.set_page_config(page_title="Coffee Store Strategist", page_icon="☕", layout="centered")

# Custom CSS for a Premium Coffee Consultant Look
st.markdown("""
<style>
    /* Main Background and Font */
    .report-container {
        background-color: #ffffff;
        padding: 40px;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333;
    }
    
    /* Headers */
    h1 { color: #2c1a12; font-family: 'Georgia', serif; font-weight: bold; }
    h2 { color: #4a3b32; font-family: 'Georgia', serif; }
    h3 { color: #6f4e37; }
    
    /* Button Styling (Coffee Bean Color) */
    .stButton>button { 
        width: 100%; 
        background-color: #6f4e37; 
        color: white; 
        font-weight: bold; 
        border: none;
        padding: 12px;
    }
    .stButton>button:hover {
        background-color: #5d4030;
        color: white;
    }
    
    /* Success Message */
    .stSuccess {
        background-color: #f6f3f0;
        border: 1px solid #d7ccc8;
        color: #4e342e;
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
            "headings": headings[:10],
            "body": body
        }, None
    except Exception as e:
        return None, f"Scraping Error: {str(e)}"

def analyze_store_json(data):
    """Generates a Coffee-Specific Strategy Report using Gemini."""
    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    prompt = f"""
    You are a Senior Business Consultant specializing in the Coffee Industry with 10+ years of experience.
    Your expertise includes:
    1. **Coffee Branding & Packaging:** You understand the nuance of specialty vs. commodity coffee aesthetics (Third Wave, Roast Profiles).
    2. **Shopify Sales Flows:** You are an expert in frictionless buying journeys for consumables (Subscriptions, Bundles, Grind Selection).
    3. **Buying Process Analysis:** You analyze how customers make decisions based on origin, tasting notes, and transparency.

    Analyze this coffee store data:
    - URL: {data['url']}
    - Title: {data['title']}
    - Description: {data['description']}
    - Headings: {data['headings']}
    - Content Snippet: {data['body'][:2500]}

    **Your Goal:** Critique this store strictly through the lens of a premium coffee brand.
    - Does the packaging look premium? 
    - Is the "Roast Date" or "Origin" clear? 
    - Is the subscription model highlighted effectively?

    Return ONLY a valid raw JSON object with this exact structure:
    {{
        "executive_summary": "<A 3-sentence high-level critique. Focus on their market positioning (Premium vs Budget) and immediate gaps in their sales flow.>",
        "score_breakdown": {{
             "score": <integer 1-10>,
             "reason": "<One sentence explaining the score based on coffee industry standards.>"
        }},
        "sections": [
            {{
                "title": "1. Branding, Packaging & Visual Identity",
                "content": "<Analyze the brand vibe. Does it feel like 'Third Wave' specialty coffee or generic? Do the product names and descriptions evoke taste/smell? Critique the visual hierarchy.>"
            }},
            {{
                "title": "2. The Buying Process & Sales Flow",
                "content": "<Critique the path to purchase. Is it easy to select grind type/weight? Are subscriptions pushed effectively? Is the 'Add to Cart' flow frictionless?>"
            }},
            {{
                "title": "3. Market Positioning & Storytelling",
                "content": "<Do they sell 'beans' or a 'morning ritual'? Critique their 'About Us' or origin stories. Are they transparent about sourcing (Fair Trade/Direct Trade)?>"
            }}
        ],
        "action_plan": [
            {{
                "step": "Step 1: Retention & LTV",
                "detail": "<Specific advice on coffee subscriptions or loyalty. Coffee buyers are repeat buyers; are they capturing this?>",
                "app": "Recharge, Bold, or Seal Subscriptions"
            }},
            {{
                "step": "Step 2: Sensory Proof",
                "detail": "<Advice on visualizing taste. Suggest adding flavor wheels, brewing guides, or specific review widgets that mention 'taste'.>",
                "app": "Judge.me or Yotpo"
            }},
            {{
                "step": "Step 3: AOV Optimization",
                "detail": "<Advice on increasing cart size. Suggest bundles (Sampler Packs), brewing gear cross-sells, or free shipping thresholds.>",
                "app": "ReConvert or Frequently Bought Together"
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
    heading = doc.add_heading('Coffee Brand Strategic Audit', 0)
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
    run_label = p_score.add_run("Coffee Strategy Score: ")
    run_label.bold = True
    
    run_score = p_score.add_run(f"{audit['score_breakdown']['score']}/10")
    run_score.bold = True
    run_score.font.color.rgb = RGBColor(111, 78, 55) # Coffee Brown
    
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
    p_footer = doc.add_paragraph("Report generated by AI Coffee Consultant.")
    p_footer.style = 'Quote'

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- 4. THE UI LAYOUT ---

st.title("☕ Coffee Brand Auditor")
st.markdown("### Specialized Analysis for Coffee Roasters")
st.markdown("Enter your Shopify URL to get a **Senior Consultant Grade** report on your branding, packaging appeal, and sales flow.")

url_input = st.text_input("Store URL", placeholder="coffeeroaster.com")

if st.button("Generate Strategy Report", type="primary"):
    if not url_input:
        st.warning("Please enter a URL.")
    else:
        with st.spinner("Analyzing roast profiles, branding, and conversion flow..."):
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
                        
                        st.metric("Strategy Score", f"{audit['score_breakdown']['score']}/10")
                        
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
                        label="Download Professional Report (.docx)",
                        data=doc_file,
                        file_name=f"Coffee_Audit_{url_input}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
