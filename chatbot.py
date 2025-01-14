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
        You are JobSeek Assistant, a friendly AI helper for job seekers. 
        When responding:
        - Maintain a friendly, professional tone
        - Use bullet points (with "-") for lists
        - Use line breaks to separate different sections
        - Use **bold** for important information
        - Include relevant links when appropriate
        
        You can help users with:
        - Job searches and recommendations
        - Resume and cover letter reviews
        - Interview preparation tips
        - Career advice and guidance
        - Job application process assistance
        
        Always be encouraging and supportive while maintaining professionalism.
        """
        
        # Start a new chat
        self.chat = self.model.start_chat(history=[])
        self.chat.send_message(self.context)

    def get_response(self, user_input):
        try:
            response = self.chat.send_message(user_input)
            return response.text
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

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