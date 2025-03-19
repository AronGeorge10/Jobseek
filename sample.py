import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file (if you have one)
load_dotenv()

# Get API token from environment variable or set it directly here
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN", "your_huggingface_token_here")
MODEL_URL = "https://api-inference.huggingface.co/models/batuhanmtl/job-skill-set"

def query_huggingface_model(skills):
    """Send a query to the Hugging Face model API"""
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
    
    # Format skills for the model
    skills_text = ", ".join(skills)
    
    # Prepare the payload
    payload = {
        "inputs": f"Skills: {skills_text}",
        "parameters": {
            "max_length": 100,
            "num_return_sequences": 5
        }
    }
    
    try:
        print(f"Sending request to Hugging Face API with skills: {skills_text}")
        response = requests.post(MODEL_URL, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        print(f"Error querying Hugging Face API: {str(e)}")
        return None

def parse_job_recommendations(model_response, skills_text):
    """Parse the model response to extract job recommendations"""
    if not model_response:
        return []
    
    recommended_job_titles = []
    
    print("\nRaw model response:")
    print(json.dumps(model_response, indent=2))
    
    for item in model_response:
        if isinstance(item, dict) and "generated_text" in item:
            # Extract job titles from generated text
            job_text = item["generated_text"].replace("Skills: " + skills_text, "").strip()
            print(f"\nExtracted job text: '{job_text}'")
            
            # Split by commas and clean up
            job_titles = [title.strip() for title in job_text.split(',') if title.strip()]
            recommended_job_titles.extend(job_titles)
    
    return recommended_job_titles

def main():
    print("=" * 50)
    print("Job Recommendation Tester")
    print("=" * 50)
    print("Enter skills separated by commas (e.g., Python, SQL, Machine Learning)")
    print("Type 'quit' to exit")
    print("-" * 50)
    
    while True:
        # Get skills input
        skills_input = input("\nEnter skills: ")
        
        if skills_input.lower() == 'quit':
            print("Exiting program. Goodbye!")
            break
        
        # Parse skills
        skills = [skill.strip() for skill in skills_input.split(',') if skill.strip()]
        
        if not skills:
            print("No valid skills entered. Please try again.")
            continue
        
        print(f"Processing {len(skills)} skills...")
        
        # Query the model
        model_response = query_huggingface_model(skills)
        
        if model_response:
            # Parse the response
            job_recommendations = parse_job_recommendations(model_response, ", ".join(skills))
            
            if job_recommendations:
                print("\n" + "=" * 30)
                print("Recommended Jobs:")
                print("=" * 30)
                for i, job in enumerate(job_recommendations, 1):
                    print(f"{i}. {job}")
            else:
                print("\nNo job recommendations found in the model response.")
        else:
            print("\nFailed to get recommendations from the model. Please check your API token and try again.")

if __name__ == "__main__":
    main()