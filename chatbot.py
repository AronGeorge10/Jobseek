import google.generativeai as genai
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, session
from pymongo import MongoClient
from flask_login import current_user
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# MongoDB connection - use the same connection as in app.py
mongo_uri = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(mongo_uri)
db = client.job_portal

class JobPortalChatbot:
    def __init__(self):
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Set up initial context
        self.context = """
        You are JobSy Assistant, a friendly AI helper for job seekers. You provide helpful, detailed responses while maintaining a professional tone.
        
        When responding:
        - Be conversational and empathetic
        - Use bullet points for lists
        - Keep responses concise but informative
        - Include relevant action buttons when appropriate
        
        You can help users with:
        - Job searches and recommendations
        - Resume and cover letter advice
        - Interview preparation tips
        - Career guidance
        - Application process assistance
        
        For navigation actions, use the following format:
        [[Button Text|URL]]

        Available navigation actions:
        - Browse Jobs: [[Browse Jobs|/recruiter/jobs/browse]]
        - Post Job: [[Post a Job|/recruiter/jobs/post]]
        - View Profile: [[My Profile|/recruiter/profile]]
        - View Applications: [[View Applications|/recruiter/applications]]
        - Dashboard: [[Company Dashboard|/recruiter/dashboard]]
        """
        
        # Start a new chat
        self.chat = self.model.start_chat(history=[])
        self.chat.send_message(self.context)

    def get_user_applications(self, user_id):
        """Retrieve user's job applications from MongoDB"""
        try:
            # Ensure user_id is an ObjectId
            from bson.objectid import ObjectId
            if not isinstance(user_id, ObjectId):
                user_id = ObjectId(user_id)
            
            print(f"Querying applications with user_id: {user_id}")
            
            # Debug: Print all collections in the database
            print(f"Available collections: {db.list_collection_names()}")
            
            # Debug: Check if the collection exists
            if "tbl_job_applications" not in db.list_collection_names():
                print("WARNING: tbl_job_applications collection not found!")
            
            # Debug: Print a sample document from the collection
            sample = db.tbl_job_applications.find_one()
            if sample:
                print(f"Sample application document: {sample}")
            else:
                print("No sample application found in collection")
            
            # Query the database with explicit filter
            filter_query = {"user_id": user_id}
            print(f"Using filter query: {filter_query}")
            
            applications = list(db.tbl_job_applications.find(filter_query))
            print(f"Found {len(applications)} applications")
            
            # If no applications found, try a different approach
            if not applications:
                print("No applications found with exact match, trying string comparison")
                str_user_id = str(user_id)
                applications = list(db.tbl_job_applications.find())
                print(f"Total applications in collection: {len(applications)}")
                
                # Debug: Print all user_ids in the collection
                all_user_ids = [str(app.get("user_id")) for app in applications]
                print(f"All user_ids in collection: {all_user_ids}")
                
                # Filter manually
                applications = [app for app in applications if str(app.get("user_id")) == str_user_id]
                print(f"After manual filtering: {len(applications)} applications")
            
            # Join with job details
            job_details = []
            for app in applications:
                job_id = app.get("job_id")
                print(f"Looking up job with ID: {job_id}")
                
                job = db.tbl_jobs.find_one({"_id": job_id})
                if job:
                    # Get company name from recruiter registration using recruiter_id
                    recruiter_id = job.get("recruiter_id")
                    company_name = "Unknown Company"
                    
                    if recruiter_id:
                        recruiter = db.tbl_recruiter_registration.find_one({"user_id": recruiter_id})
                        if recruiter and "company_name" in recruiter:
                            company_name = recruiter.get("company_name")
                            print(f"Found company name: {company_name}")
                        else:
                            print(f"Recruiter not found or missing company_name for ID: {recruiter_id}")
                    
                    job_details.append({
                        "job_title": job.get("title", "Unknown Position"),
                        "company": company_name,
                        "status": app.get("status", "Pending"),
                        "applied_date": app.get("applied_at").strftime("%Y-%m-%d") if app.get("applied_at") else "Unknown",
                        "job_id": str(job.get("_id"))
                    })
                else:
                    print(f"Job not found for ID: {job_id}")
            
            print(f"Processed {len(job_details)} job details")
            return job_details
        except Exception as e:
            print(f"Database error in get_user_applications: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def get_recruiter_posted_jobs(self, recruiter_id):
        """Retrieve jobs posted by a recruiter from MongoDB"""
        try:
            jobs = list(db.tbl_jobs.find({"recruiter_id": recruiter_id}))
            job_details = []
            
            for job in jobs:
                # Count applications for this job
                application_count = db.tbl_job_applications.count_documents({"job_id": job.get("_id")})
                
                job_details.append({
                    "job_title": job.get("title"),
                    "company": job.get("company_name"),
                    "applications": application_count,
                    "posted_date": job.get("created_at").strftime("%Y-%m-%d") if job.get("created_at") else "Unknown",
                    "status": job.get("status", "Active"),
                    "job_id": str(job.get("_id"))
                })
            
            return job_details
        except Exception as e:
            print(f"Database error: {str(e)}")
            return []

    def get_response(self, user_input, user_id=None, user_type=None):
        try:
            # Check for specific user-related queries
            input_lower = user_input.lower()
            
            # Debug logging
            print(f"User ID: {user_id}, User Type: {user_type}, Query: {input_lower}")
            
            # Handle user-specific queries
            if user_id:
                # Check for application-related queries
                if any(keyword in input_lower for keyword in ["applied", "my application", "jobs i applied", "what are the jobs", "show me my application"]):
                    
                    # If user is a recruiter, provide an appropriate response
                    if user_type == 'recruiter':
                        return """As a recruiter, you don't apply to jobs. You post and manage job listings.
                        
Would you like to:
- [[View Posted Jobs|/recruiter/jobs/manage]]
- [[Post a New Job|/recruiter/jobs/post]]
- [[View Applications Received|/recruiter/applications]]"""
                    
                    # For job seekers, show their applications
                    print(f"Detected application query, fetching applications for user {user_id}")
                    applications = self.get_user_applications(user_id)
                    
                    if not applications:
                        return "You haven't applied to any jobs yet. Start exploring opportunities!\n\n[[Browse Jobs|/seeker/job_postings]]"
                    
                    response = "Here are the jobs you've applied to:\n\n"
                    for app in applications:
                        response += f"• {app['job_title']} at {app['company']}\n"
                        response += f"  Status: {app['status']} | Applied on: {app['applied_date']}\n"
                    
                    response += "\n[[View All Applications|/seeker/applications]]"
                    print(f"Returning application response: {response}")
                    return response
                
                # For recruiters - check for job posting queries
                if any(keyword in input_lower for keyword in ["posted", "my job", "jobs i posted"]):
                    if user_type != 'recruiter':
                        return """As a job seeker, you don't post jobs. You can browse and apply to job listings.
                        
Would you like to:
- [[Browse Jobs|/seeker/job_postings]]
- [[View Your Applications|/seeker/applications]]
- [[Update Your Profile|/seeker/profile]]"""
                    
                    print(f"Detected job posting query, fetching posted jobs for recruiter {user_id}")
                    jobs = self.get_recruiter_posted_jobs(user_id)
                    
                    if not jobs:
                        return "You haven't posted any jobs yet. Create your first job listing!\n\n[[Post a Job|/recruiter/jobs/post]]"
                    
                    response = "Here are the jobs you've posted:\n\n"
                    for job in jobs:
                        response += f"• {job['job_title']} at {job['company']}\n"
                        response += f"  Applications: {job['applications']} | Posted on: {job['posted_date']} | Status: {job['status']}\n"
                    
                    response += "\n[[Manage Jobs|/recruiter/jobs/manage]]"
                    return response
            
            # Get AI response for general queries
            print("No specific query detected, using AI response")
            response = self.chat.send_message(f"""
            User Query: {user_input}
            
            Provide a helpful response. If the query relates to specific actions like posting jobs, 
            viewing profiles, or accessing applications, include relevant navigation buttons using 
            the [[Button Text|URL]] format.
            
            Keep the response natural and conversational while being informative.
            """)
            
            # If no response from AI, use fallback
            if not response.text:
                return """I can help you with:
                - Posting and managing jobs
                - Viewing applications
                - Managing your profile
                - Accessing dashboard

                [[Browse Jobs|/recruiter/jobs/browse]]
                [[Post a Job|/recruiter/jobs/post]]
                [[My Profile|/recruiter/profile]]
                [[Company Dashboard|/recruiter/dashboard]]"""
            
            return response.text

        except Exception as e:
            print(f"Error in get_response: {str(e)}")  # For debugging
            import traceback
            traceback.print_exc()
            return """I apologize, but I'm having trouble processing your request. 
            Here are some helpful links:

            [[Browse Jobs|/recruiter/jobs/browse]]
            [[Contact Support|/recruiter/support]]"""

# Example usage with Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')
chatbot = JobPortalChatbot()

@app.route('/recruiter')
def recruiter_index():
    return render_template('recruiter/recruiter_index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get user information if available
    user_id = None
    user_type = None
    
    if current_user and current_user.is_authenticated:
        user_id = str(current_user.id)  # Convert ObjectId to string if needed
        user_type = current_user.user_type
        print(f"Authenticated user: {user_id}, type: {user_type}")
    else:
        # For testing purposes, you can use a mock user ID
        # Uncomment for testing
        print("No authenticated user found, using test user")
        user_id = "66b992bcd73da8894fa07834"  # Use a valid test user ID from your database
        user_type = "seeker"
    
    response = chatbot.get_response(user_message, user_id, user_type)
    return jsonify({'response': response})

@app.route('/')
def home():
    return render_template('chat.html')

if __name__ == '__main__':
    app.run(debug=True)