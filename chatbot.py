import google.generativeai as genai
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class JobPortalChatbot:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Configure Gemini API
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Initialize the model
        self.model = genai.GenerativeModel('gemini-pro')
        
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

    def get_response(self, user_input):
        try:
            # First, check for specific navigation-related queries
            input_lower = user_input.lower()
            
            # Get AI response
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
            return """I apologize, but I'm having trouble processing your request. 
            Here are some helpful links:

            [[Browse Jobs|/recruiter/jobs/browse]]
            [[Contact Support|/recruiter/support]]"""

# Example usage with Flask
app = Flask(__name__)
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
    
    response = chatbot.get_response(user_message)
    return jsonify({'response': response})

@app.route('/')
def home():
    return render_template('chat.html')

if __name__ == '__main__':
    app.run(debug=True)