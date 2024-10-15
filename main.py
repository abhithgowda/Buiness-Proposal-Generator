from flask import Flask,render_template,request,jsonify,redirect
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain.utilities import DuckDuckGoSearchAPIWrapper
from langchain.chains.llm_math.base import LLMMathChain
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool, Tool
from IPython.display import Image, display
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
import re
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, send_file
import pdfkit
import re
import os
import json
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Set up the path to wkhtmltopdf manually
path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'  # Update with your path
pdfkit_config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

os.environ["GOOGLE_API_KEY"] = 'AIzaSyAMyP-dFmCiqaBpHgg5opdju555DI3beCI'
# Initialize the Gemini LLM model
# setup model - this is your handle to the LLM



llm = ChatGoogleGenerativeAI(
    model="gemini-pro",
    #convert_system_message_to_human=True,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    handle_parsing_errors=True,
    temperature=0.6,
    # safety_settings = {
    #     HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    #     HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    #     HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    #     HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    # },
)
# Tools for the agent
ddg_search = DuckDuckGoSearchAPIWrapper()

problem_chain = LLMMathChain.from_llm(llm=llm)

math_tool = Tool.from_function(name="Calculator",
                func=problem_chain.run,
                description="Useful for when you need to answer questions about math. This tool is only for math questions and nothing else. Only input math expressions.")

# @tool
# def multiply(a: int, b: int) -> int:
#     """Multiply two numbers."""
#     return a * b


@tool
def search(query: str) -> str:
    """searches the web for the provided query"""
    return ddg_search.run(query)

tools = [search, math_tool]
config = {"configurable": {"thread_id": "abc123"}}
# Memory store
memory = MemorySaver()

# Create the agent with tools and memory
agent = create_react_agent(llm, tools, checkpointer=memory)
# Initialize the Flask application

def format_content(content):
    # Replace '*' with bullets (•) after headers
    content = re.sub(r'\*\s', '• ', content)

    # Remove stray asterisks used as markup
    content = re.sub(r'\*+', '', content)

    return content

def generate_pdf(content):
    # Create a BytesIO object to store the PDF data
    pdf_stream = BytesIO()

    # Create a canvas object to draw the PDF content
    pdf = canvas.Canvas(pdf_stream, pagesize=letter)
    pdf.setTitle("Generated Proposal")

    # Set font and other styles
    pdf.setFont("Helvetica", 12)

    # Define where to start writing text (top of the page)
    y_position = 750

    # Split the content into lines and write each line to the PDF
    for line in content.split('\n'):
        pdf.drawString(72, y_position, line)  # (x, y) positions to start writing
        y_position -= 15  # Move the cursor down by 15 points for each line

    # Finalize the PDF and store it in the buffer
    pdf.save()

    # Move the buffer position to the beginning
    pdf_stream.seek(0)
    return pdf_stream

def generate_proposal_section(prompt):
    # Invoke LLM agent to generate text based on the prompt
    response = agent.invoke({"messages": [HumanMessage(content=prompt)]},config)
    return response["messages"][-1].content

def generate_proposal(client_data):
    # Executive Summary
    executive_summary_prompt = f"Write an executive summary for {client_data['client_name']} in the {client_data['industry']} industry, addressing their pain points: {client_data['pain_points']} and expected outcome: {client_data['expected_outcome']}."
    executive_summary = generate_proposal_section(executive_summary_prompt)

    # Solution Description
    solution_description_prompt = f"Describe the solution for {client_data['client_name']}'s project '{client_data['project_name']}', which involves {client_data['scope_of_work']}."
    solution_description = generate_proposal_section(solution_description_prompt)

    # Deliverables
    deliverables_prompt = f"List the deliverables for {client_data['project_name']} including: {', '.join(client_data['deliverables'])}."
    deliverables = generate_proposal_section(deliverables_prompt)

    # Conclusion/Call to Action
    conclusion_prompt = f"Write a professional closing statement for a proposal to {client_data['client_name']}, inviting them to discuss next steps and timeline."
    conclusion = generate_proposal_section(conclusion_prompt)

    # Compile the full proposal
    full_proposal = f"""

    {executive_summary}\n

    {solution_description}\n

    {deliverables}\n

    {conclusion}
    """

    return full_proposal
app = Flask(__name__)

# Define a route for the home page
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/submit', methods=['POST'])
def submit():
    # Get data from the form
    client_data = {
        "client_name": request.form.get('clientName'),
        "industry": request.form.get('industry'),
        "pain_points": request.form.get('painPoints'),
        "expected_outcome": request.form.get('expectedOutcome'),
        "project_name": request.form.get('projectName'),
        "scope_of_work": request.form.get('scopeOfWork'),
        "timeline": request.form.get('timeline'),
        "budget": request.form.get('budget'),
        "tone": request.form.get('tone'),
       "deliverables": request.form.get('deliverables').split(','),  
        "references": request.form.get('references').split(',')   
    }
    # client_data = {
    # "client_name": "Urban Properties Management Inc.",
    # "industry": "Real Estate",
    # "pain_points": "Disorganized property listings, manual tenant management, high vacancy rates, and time-consuming lease processes",
    # "expected_outcome": "Centralized property management system with automated lease tracking, streamlined tenant communication, and a reduction in vacancy rates by 25%",
    # "project_name": "Property Management Platform Development",
    # "scope_of_work": "Develop a cloud-based property management platform, integrate with property listing services, automate tenant management and lease processes, and provide analytics on rental performance",
    # "timeline": "9 months",
    # "budget": "$250,000",
    # "tone": "Professional and user-centric with a focus on efficiency and innovation",
    # "deliverables": [
    #     "Property Management System Audit and Requirements Gathering",
    #     "Cloud-Based Platform Development",
    #     "Integration with Property Listing Portals",
    #     "Tenant Management and Automated Lease Processing Features",
    #     "User Training and Onboarding",    
    #     "System Testing, Security Audits, and Data Compliance",
    #     "Deployment and Post-Deployment Support"
    # ],
    # "references": [
    #     "Automated tenant management system for Skyline Properties, reducing vacancy rates by 20%",
    #     "Developed a real estate listing platform for Horizon Realty, increasing property visibility by 40%"
    # ]
    # }
    proposal = generate_proposal(client_data)
    print(proposal) 
    formatted_content = format_content(proposal)
    pdf_stream = generate_pdf(formatted_content)
    # Return the PDF as a downloadable file
    return send_file(
        pdf_stream,
        as_attachment=True,
        download_name="proposal.pdf",  # The name of the file to be downloaded
        mimetype='application/pdf'
    )


# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)
