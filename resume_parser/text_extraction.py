import pdfplumber
from docx import Document

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

# Example usage
sample_pdf = "resume.pdf"
sample_docx = "resume.docx"

pdf_text = extract_text(sample_pdf)
docx_text = extract_text(sample_docx)

print("PDF Text:", pdf_text[:100])  # Print first 100 characters
print("DOCX Text:", docx_text[:100])  # Print first 100 characters