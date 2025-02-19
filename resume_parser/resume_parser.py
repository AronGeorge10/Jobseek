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
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    return phones[0] if phones else None

def extract_name(text):
    """Extract name (assumes the name is on the first line)."""
    return text.split("\n")[0].strip()

def extract_entities(text):
    """Extract skills, education, and experience using spaCy."""
    doc = nlp(text)
    entities = {
        "skills": [],
        "education": [],
        "experience": []
    }

    # Custom rules for extracting entities
    for ent in doc.ents:
        if ent.label_ == "ORG" and "university" in ent.text.lower():
            entities["education"].append(ent.text)
        elif ent.label_ == "ORG" and any(word in ent.text.lower() for word in ["inc", "corp", "llc"]):
            entities["experience"].append(ent.text)
        elif ent.label_ == "GPE":  # Geopolitical entity (e.g., locations)
            entities["experience"].append(ent.text)

    # Extract skills using a predefined list
    skills_list = ["Python", "Java", "SQL", "Machine Learning", "Data Analysis"]
    for skill in skills_list:
        if skill.lower() in text.lower():
            entities["skills"].append(skill)

    return entities

def parse_resume(file_path):
    """Parse a resume file and return structured data."""
    text = extract_text(file_path)  # Use Part 1 to extract text
    parsed_data = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        **extract_entities(text)
    }
    return parsed_data

# Example usage
# sample_pdf = "resume.pdf"
sample_docx = "E:/jobseek/resume_parser/resume.docx"

# pdf_data = parse_resume(sample_pdf)
docx_data = parse_resume(sample_docx)

# print("PDF Parsed Data:", pdf_data)
print("DOCX Parsed Data:", docx_data)