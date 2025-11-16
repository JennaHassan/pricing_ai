import os
import pandas as pd
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Initialize OpenAI client (will be None if API key not set)
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# Load materials CSV and handle BOM character
materials_df = pd.read_csv('/Users/jennamahdi/Desktop/pricingproject/pricing_materials.csv', encoding='utf-8-sig')
# Strip any whitespace and BOM from column names
materials_df.columns = materials_df.columns.str.strip()


# Function to estimate project materials using ChatGPT
def estimate_project(description):
    # Prepare materials list as context for ChatGPT
    materials_context = "Available materials and prices:\n"
    for _, row in materials_df.iterrows():
        # Handle both 'material_name' and 'ï»¿material_name' column names
        material_name_col = 'material_name' if 'material_name' in materials_df.columns else materials_df.columns[0]
        material_name = row[material_name_col]
        size = row.get('Size', 'N/A')
        unit_price = row.get('unit_price', 0)
        materials_context += f"- {material_name} ({size}): {unit_price} SAR per unit\n"
    
    # Create prompt for ChatGPT
    prompt = f"""You are a construction/material estimation expert. Based on the following project description, determine which materials are needed and estimate quantities.

{materials_context}

Project Description: {description}

Please analyze the project description and provide a clean list of materials with calculations.

Format your response EXACTLY as follows (one material per line with colon):
Material Name: Quantity × Unit Price SAR = Total Cost SAR
[Continue for each material]
---
Total Estimated Cost: [amount] SAR

Example format:
Interpipe: 2 × 50 SAR = 100 SAR
Mounting Bracket: 2 × 20 SAR = 40 SAR
Installation Labor: 3 × 200 SAR = 600 SAR
---
Total Estimated Cost: 740 SAR

Be realistic and consider the project requirements. Include Installation Labor, Site Visit Fee, and Consumables as standard items for most projects."""

    if client is None:
        return "Error: OPENAI_API_KEY environment variable is not set. Please set it to use the ChatGPT estimation feature."
    
    try:
        # Call ChatGPT API (using gpt-3.5-turbo which is more cost-effective)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional construction and fire safety equipment estimator. You provide accurate material estimates based on project descriptions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Extract the estimate from ChatGPT's response
        estimate = response.choices[0].message.content
        return estimate
    
    except Exception as e:
        error_str = str(e)
        # Check for specific error types and provide helpful messages
        if "insufficient_quota" in error_str or "429" in error_str:
            return f"""❌ **Quota Exceeded Error**

Your OpenAI account has exceeded its API quota. To fix this:

1. **Check your billing**: Visit https://platform.openai.com/account/billing
2. **Add payment method**: You may need to add a payment method to continue using the API
3. **Check usage limits**: Review your usage at https://platform.openai.com/usage
4. **Upgrade plan**: Consider upgrading if you've hit your tier limits

**Error details**: {error_str}"""
        elif "Invalid API key" in error_str or "401" in error_str:
            return f"❌ **API Key Error**: Invalid API key. Please check your OPENAI_API_KEY in the .env file.\n\n**Error**: {error_str}"
        else:
            return f"❌ **Error getting estimate from ChatGPT**: {error_str}\n\nPlease check your API key and billing status at https://platform.openai.com/account/billing"

# Streamlit Interface
st.title("Nafel Project Estimator")
st.write("Enter your project description to get estimated materials and cost.")

# Check if API key is set
if not api_key:
    st.error("⚠️ OPENAI_API_KEY environment variable is not set. Please set it to use the ChatGPT estimation feature.")

project_description = st.text_area("Project Description", "")

if st.button("Estimate"):
    if project_description.strip() == "":
        st.warning("Please enter a project description!")
    else:
        with st.spinner("Analyzing project description and generating estimate..."):
            result = estimate_project(project_description)
        
        # Style the result display with custom CSS
        st.markdown("### Estimation Result")
        
        # Add custom CSS for better formatting
        st.markdown("""
        <style>
        .estimate-container {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 14px;
            line-height: 1.8;
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #dee2e6;
            margin: 10px 0;
        }
        .estimate-line {
            margin: 8px 0;
            color: #333;
        }
        .estimate-divider {
            margin: 15px 0;
            border-top: 2px solid #ccc;
            padding-top: 15px;
        }
        .estimate-total {
            font-weight: 700;
            font-size: 16px;
            color: #0066cc;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 2px solid #0066cc;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Parse and format the result
        if result.startswith("❌") or result.startswith("Error"):
            st.error(result)
        else:
            # Split result into lines and format
            lines = result.split('\n')
            formatted_lines = []
            in_divider = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('---') or line == '---':
                    if not in_divider:
                        formatted_lines.append('<div class="estimate-divider"></div>')
                        in_divider = True
                elif 'Total Estimated Cost' in line:
                    formatted_lines.append(f'<div class="estimate-total">{line}</div>')
                else:
                    formatted_lines.append(f'<div class="estimate-line">{line}</div>')
            
            # Display formatted result
            formatted_html = f'<div class="estimate-container">{"".join(formatted_lines)}</div>'
            st.markdown(formatted_html, unsafe_allow_html=True)
