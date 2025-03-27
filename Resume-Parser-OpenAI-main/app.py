# FLASK APP - Run the app using flask --app app.py run
import os
import json
from flask import Flask, render_template, request
from pypdf import PdfReader
from resumeparser import ats_extractor

app = Flask(__name__)

# Create upload folder if it doesn't exist
UPLOAD_PATH = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(UPLOAD_PATH):
    os.makedirs(UPLOAD_PATH)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/process", methods=["POST"])
def ats():
    doc = request.files['pdf_doc']
    doc.save(os.path.join(UPLOAD_PATH, "file.pdf"))
    doc_path = os.path.join(UPLOAD_PATH, "file.pdf")
    data = _read_file_from_path(doc_path)
    
    try:
        parsed_data = ats_extractor(data)
        
        # Clean up the response if it contains extra quotes or characters
        if parsed_data.startswith('```json') and parsed_data.endswith('```'):
            # Extract just the JSON part from markdown code block
            parsed_data = parsed_data[7:-3].strip()
        
        # Handle cases where the response might have extra quotes
        if parsed_data.startswith('"') and parsed_data.endswith('"'):
            parsed_data = parsed_data[1:-1].replace('\\"', '"')
        
        # Try to parse as JSON
        try:
            json_data = json.loads(parsed_data)
            return render_template('index.html', data=json_data)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {str(e)}")
            # If it's not valid JSON, try to clean it up further
            if parsed_data.startswith('json {') and parsed_data.endswith('}'):
                cleaned_data = parsed_data[5:].strip()
                try:
                    json_data = json.loads(cleaned_data)
                    return render_template('index.html', data=json_data)
                except:
                    pass
            
            # If all parsing attempts fail, just show the raw data
            return render_template('index.html', raw_data=parsed_data)
    except Exception as e:
        print(f"Error in ats_extractor: {str(e)}")
        return render_template('index.html', error=f"Error processing resume: {str(e)}")

def _read_file_from_path(path):
    reader = PdfReader(path)
    data = ""

    for page_no in range(len(reader.pages)):
        page = reader.pages[page_no] 
        data += page.extract_text()

    return data

if __name__ == "__main__":
    app.run(debug=True)

