from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from pymongo import MongoClient
import os
from bson import ObjectId

customer_care_bp = Blueprint('customer_care', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_login_credentials = db.tbl_login_credentials
collection_resume_details = db.tbl_resume_details
collection_recruiter_registration = db.tbl_recruiter_registration
collection_jobs = db.tbl_jobs
collection_applications = db.tbl_job_applications
collection_notifications = db.tbl_notifications
collection_industries = db.tbl_industries

@customer_care_bp.route('/', methods=['GET'])
@customer_care_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Landing page for customer support dashboard"""
    try:
        # Fetch FAQs from database and sort by category
        faqs = list(db.tbl_faq.find().sort([("category", 1), ("created_at", -1)]))
        print("Fetched FAQs:", faqs)  # Debug print 
        
        # Convert ObjectId to string for each FAQ
        for faq in faqs:
            faq['_id'] = str(faq['_id'])
        
        print("Number of FAQs:", len(faqs))  # Debug print
        print("Categories:", set(faq['category'] for faq in faqs))  # Debug print
            
    except Exception as e:
        print(f"Error fetching FAQs: {str(e)}")
        faqs = []
    
    return render_template('customer_care/dashboard.html', faqs=faqs)

@customer_care_bp.route('/tickets', methods=['GET'])
@login_required
def ticket_list():
    """List user's support tickets"""
    # Here you would typically fetch tickets from database
    tickets = []  # Replace with actual database query
    return render_template('customer_care/tickets.html', tickets=tickets)

@customer_care_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Handle contact form submissions"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('customer_care.support_landing'))
    
    return render_template('customer_care/contact.html')

@customer_care_bp.route('/live-chat', methods=['GET'])
@login_required
def live_chat():
    """Live chat interface"""
    return render_template('customer_care/live_chat.html')

@customer_care_bp.route('/faq', methods=['GET', 'POST'])
def faq():
    """FAQ Management page"""
    if request.method == 'POST' and current_user.is_authenticated and current_user.user_type == 'customer_care':
        category = request.form.get('category')
        question = request.form.get('question')
        answer = request.form.get('answer')
        
        if all([category, question, answer]):
            new_faq = {
                "category": category,
                "question": question,
                "answer": answer,
                "created_by": str(current_user.id),  # Convert to string
                "created_at": datetime.utcnow()
            }
            try:
                result = db.tbl_faq.insert_one(new_faq)
                print(f"New FAQ inserted with ID: {result.inserted_id}")  # Debug print
                flash('FAQ added successfully!', 'success')
            except Exception as e:
                print(f"Error inserting FAQ: {str(e)}")  # Debug print
                flash('Error adding FAQ!', 'error')
        else:
            flash('All fields are required!', 'error')
            
    # Get all FAQs for display
    try:
        faqs = list(db.tbl_faq.find().sort('created_at', -1))  # Sort by newest first
        for faq in faqs:
            faq['_id'] = str(faq['_id'])
            print(f"FAQ in list: {faq}")  # Debug print
    except Exception as e:
        print(f"Error fetching FAQs: {str(e)}")  # Debug print
        faqs = []
        
    return render_template('customer_care/faq.html', faqs=faqs)

@customer_care_bp.route('/tickets/new', methods=['GET', 'POST'])
@login_required
def create_ticket():
    """Create new support ticket"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority')
        
        # Here you would typically:
        # 1. Validate the input
        # 2. Create ticket in database
        # 3. Send confirmation email
        
        flash('Ticket created successfully!', 'success')
        return redirect(url_for('customer_care.ticket_list'))
    
    return render_template('customer_care/create_ticket.html')

@customer_care_bp.route('/tickets/<int:ticket_id>', methods=['GET'])
@login_required
def ticket_detail(ticket_id):
    """View specific ticket details"""
    # Here you would typically fetch ticket from database
    ticket = None  # Replace with actual database query
    if not ticket:
        flash('Ticket not found', 'error')
        return redirect(url_for('customer_care.ticket_list'))
    
    return render_template('customer_care/ticket_detail.html', ticket=ticket)

# API endpoints for AJAX requests
@customer_care_bp.route('/api/tickets/<int:ticket_id>/reply', methods=['POST'])
@login_required
def api_ticket_reply(ticket_id):
    """API endpoint for adding replies to tickets"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Here you would typically:
    # 1. Save reply to database
    # 2. Send notifications
    # 3. Handle any errors
    
    return jsonify({'status': 'success', 'message': 'Reply added successfully'})

# Optional: API endpoint for live chat
@customer_care_bp.route('/api/chat/send', methods=['POST'])
@login_required
def api_chat_send():
    """API endpoint for sending chat messages"""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Here you would typically:
    # 1. Save message to database
    # 2. Broadcast to relevant users
    # 3. Handle any errors
    
    return jsonify({'status': 'success', 'message': 'Message sent'})

@customer_care_bp.route('/faq/<faq_id>', methods=['GET'])
@login_required
def get_faq(faq_id):
    """Get FAQ details for editing"""
    print(f"Getting FAQ with ID: {faq_id}")  # Debug print
    
    if current_user.user_type != 'customer_care':
        return jsonify({'error': 'Unauthorized access'}), 403
    
    try:
        # Convert string ID to ObjectId
        faq_id = ObjectId(faq_id)
        print(f"Converted ObjectId: {faq_id}")  # Debug print
        
        faq = db.tbl_faq.find_one({'_id': faq_id})
        print(f"Found FAQ: {faq}")  # Debug print
        
        if faq:
            response_data = {
                'category': faq.get('category'),
                'question': faq.get('question'),
                'answer': faq.get('answer')
            }
            print(f"Sending response: {response_data}")  # Debug print
            return jsonify(response_data)
            
        print("FAQ not found")  # Debug print
        return jsonify({'error': 'FAQ not found'}), 404
        
    except Exception as e:
        print(f"Error in get_faq: {str(e)}")  # Debug print
        return jsonify({'error': str(e)}), 500

@customer_care_bp.route('/faq/<string:faq_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_faq(faq_id):
    if current_user.user_type != 'customer_care':
        return jsonify({'error': 'Unauthorized access'}), 403

    try:
        # Validate FAQ ID format
        if not ObjectId.is_valid(faq_id):
            return jsonify({'error': 'Invalid FAQ ID format'}), 400

        obj_id = ObjectId(faq_id)

        if request.method == 'DELETE':
            result = db.tbl_faq.delete_one({'_id': obj_id})
            if result.deleted_count:
                return jsonify({'status': 'success', 'message': 'FAQ deleted'})
            return jsonify({'status': 'error', 'message': 'FAQ not found'}), 404

        elif request.method == 'PUT':
            data = request.get_json()
            existing_faq = db.tbl_faq.find_one({'_id': obj_id})
            if not existing_faq:
                return jsonify({'status': 'error', 'message': 'FAQ not found'}), 404

            update_data = {
                'category': data.get('category'),
                'question': data.get('question'),
                'answer': data.get('answer'),
                'updated_at': datetime.utcnow(),
                'updated_by': str(current_user.id)
            }

            result = db.tbl_faq.update_one(
                {'_id': obj_id},
                {'$set': update_data}
            )

            if result.modified_count:
                return jsonify({'status': 'success', 'message': 'FAQ updated'})
            return jsonify({'status': 'error', 'message': 'No changes detected'}), 200

    except Exception as e:
        print(f"Error in manage_faq: {str(e)}")
        return jsonify({'error': str(e)}), 500

@customer_care_bp.context_processor
def utility_processor():
    return {
        'str': str
    }
