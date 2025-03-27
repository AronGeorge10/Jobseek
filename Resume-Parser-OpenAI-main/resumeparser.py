# import libraries
import os
import yaml
import google.generativeai as genai

# Get API key from environment variable or config file
CONFIG_PATH = r"config.yaml"

with open(CONFIG_PATH) as file:
    data = yaml.load(file, Loader=yaml.FullLoader)
    api_key = data.get('GEMINI_API_KEY')

def ats_extractor(resume_data):
    # Configure the Gemini API
    genai.configure(api_key=api_key)

    prompt = '''
    You are an AI bot designed to act as a professional for parsing resumes. You are given with resume and your job is to extract the following information from the resume:
    
    1. full_name: The person's full name
    2. email_id: Email address
    3. github_portfolio: GitHub profile URL (if available)
    4. linkedin_id: LinkedIn profile URL (if available)
    5. summary: Look for any professional summary, profile, objective, or career statement. This might be labeled as "Summary", "Profile", "Professional Profile", "Career Objective", "About Me", etc.
    6. employment_details: Array of job experiences with these fields:
       - title: Job title
       - company: Company name
       - duration or dates: Employment period
       - responsibilities: Array of job duties or accomplishments
    7. education_details: Array of educational background with these fields:
       - degree: Degree or certification name
       - institution: School, college or university name
       - graduation_year: Year of graduation
       - gpa: GPA if available
    8. technical_skills: Array of technical or hard skills
    9. soft_skills: Array of soft or interpersonal skills
    
    Give the extracted information in JSON format only. Make sure to use the exact field names specified above.
    '''

    try:
        # Create a model instance with the correct model name
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Combine the prompt and resume data
        full_prompt = f"{prompt}\n\nResume content:\n{resume_data}"
        
        # Generate content
        response = model.generate_content(full_prompt)
        
        # Extract the text from the response
        data = response.text
        
        return data
    except Exception as e:
        print(f"Error generating content: {str(e)}")
        raise Exception(f"Failed to generate content: {str(e)}")