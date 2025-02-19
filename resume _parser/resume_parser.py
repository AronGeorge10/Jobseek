# Import libraries
import pdfplumber
from docx import Document
import re
import spacy

# Load spaCy's pre-trained model
nlp = spacy.load("en_core_web_sm")

# Part 1: Text Extraction
def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    with pdfplumber.open(pdf_path) as pdf:
        text = " ".join([page.extract_text() for page in pdf.pages])
    return text

def extract_text_from_docx(docx_path):
    """Extract text from a DOCX file."""
    doc = Document(docx_path)
    text = " ".join([para.text for para in doc.paragraphs])
    return text

def extract_text(file_path):
    """Extract text from a file (PDF, DOC, or DOCX)."""
    if file_path.endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith(".docx") or file_path.endswith(".doc"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Only PDF, DOC, and DOCX are supported.")

# Part 2: Resume Parsing
def extract_email(text):
    """Extract email using regex."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return emails[0] if emails else None

def extract_phone(text):
    """Extract phone number using regex."""
    phone_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'  # Matches (716) 555-0100
    phones = re.findall(phone_pattern, text)
    return phones[0] if phones else None

def extract_name(text):
    """Extract name using regex."""
    name_pattern = r"^([A-Z][a-z]+ [A-Z][a-z]+)"  # Matches "Janna Gardner"
    match = re.search(name_pattern, text)
    return match.group(1) if match else ""

def extract_skills(text):
    """Extract skills from the Skills section."""
    skills_section = re.search(r"Skills(.*?)Education", text, re.DOTALL | re.IGNORECASE)
    if skills_section:
        skills_text = skills_section.group(1).strip()
        skills = re.split(r"•|\|", skills_text)  # Split by bullets
        return [skill.strip() for skill in skills if skill.strip()]
    return []

def extract_education(text):
    """Extract education details using regex."""
    education_pattern = r"Education\s*([\s\S]*?)Activities"  # Extract section
    education_matches = re.search(education_pattern, text, re.DOTALL | re.IGNORECASE)
    if education_matches:
        return [education_matches.group(1).strip()]
    return []

def extract_experience(text):
    """Extract experience details using regex."""
    experience_pattern = r"(\d{4} -- PRESENT|JUNE \d{4} -- AUGUST \d{4})[\s\S]*?\|\s*(.*?)\s*\|\s*(.*?)\n"
    experience_matches = re.findall(experience_pattern, text)
    experience = []
    for match in experience_matches:
        experience.append({
            "duration": match[0],
            "role": "Human Resources Generalist" if "Generalist" in match[1] else "Intern",
            "company": match[1],
            "location": match[2]
        })
    return experience

def parse_resume(file_path):
    """Parse a resume file and return structured data."""
    text = extract_text(file_path)  # Use Part 1 to extract text
    parsed_data = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": extract_skills(text),
        "education": extract_education(text),
        "experience": extract_experience(text)
    }
    return parsed_data

# Example usage
sample_docx = "E:/jobseek/resume_parser/resume.docx"  # Replace with your DOCX file path

try:
    docx_data = parse_resume(sample_docx)
    print("DOCX Parsed Data:", docx_data)
except Exception as e:
    print(f"Error parsing DOCX: {e}")