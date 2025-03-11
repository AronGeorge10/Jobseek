from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request, current_app
from flask_login import current_user, login_required
from bson.objectid import ObjectId
from datetime import datetime
import traceback

from pymongo import MongoClient, DESCENDING
import os

# Database setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']

# Collections
collection_conversations = db['tbl_conversations']
collection_messages = db['tbl_messages']
collection_users = db['tbl_login_credentials']
collection_resume = db['tbl_resume_details']
collection_recruiter_registration = db['tbl_recruiter_registration']

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/messages')
@login_required
def messages_list():
    """Display list of all conversations for the current user"""
    try:
        # Find all conversations where the current user is a participant
        conversations = collection_conversations.find({
            '$or': [
                {'user1_id': ObjectId(current_user.id)},
                {'user2_id': ObjectId(current_user.id)}
            ]
        }).sort('last_message_at', DESCENDING)
        
        # Process conversations to include user details
        conversations_list = []
        for conv in conversations:
            # Determine the other user in the conversation
            other_user_id = conv['user2_id'] if str(conv['user1_id']) == current_user.id else conv['user1_id']
            
            # Get other user's details
            other_user = collection_users.find_one({'_id': other_user_id})
            if not other_user:
                continue  # Skip if user not found
                
            # Get additional details based on user type
            display_name = other_user.get('name', 'Unknown User')
            profile_pic = None
            
            if other_user.get('user_type') == 'seeker':
                # Get job seeker details
                seeker = collection_resume.find_one({'user_id': other_user_id})
                if seeker:
                    personal_info = seeker.get('personal_info', {})
                    display_name = personal_info.get('full_name', display_name)
                    profile_pic = seeker.get('profile_photo')
            elif other_user.get('user_type') == 'recruiter':
                # Get recruiter details
                recruiter = collection_recruiter_registration.find_one({'user_id': other_user_id})
                if recruiter:
                    display_name = recruiter.get('company_name', display_name)
                    profile_pic = recruiter.get('company_logo')
            
            # Get last message
            last_message = collection_messages.find_one(
                {'conversation_id': conv['_id']},
                sort=[('timestamp', DESCENDING)]
            )
            
            # Format last message preview
            last_message_text = last_message.get('content', 'No messages yet') if last_message else 'No messages yet'
            if len(last_message_text) > 30:
                last_message_text = last_message_text[:30] + '...'
                
            # Determine unread count for current user
            unread_count = conv.get('unread_count_user1', 0) if str(conv['user1_id']) == current_user.id else conv.get('unread_count_user2', 0)
            
            # Format timestamp
            last_message_time = last_message.get('timestamp') if last_message else conv.get('created_at')
            formatted_time = format_timestamp(last_message_time) if last_message_time else 'Never'
            
            conversations_list.append({
                'id': str(conv['_id']),
                'other_user_id': str(other_user_id),
                'display_name': display_name,
                'profile_pic': profile_pic,
                'last_message': last_message_text,
                'timestamp': formatted_time,
                'unread_count': unread_count
            })
        
        return render_template('messages/conversations.html', conversations=conversations_list)
        
    except Exception as e:
        current_app.logger.error(f"Error in messages_list: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        flash('An error occurred while loading your conversations', 'error')
        return redirect(url_for('index'))

@messages_bp.route('/messages/<conversation_id>')
@login_required
def view_conversation(conversation_id):
    """Display a specific conversation"""
    try:
        # Verify conversation exists and user is a participant
        conversation = collection_conversations.find_one({
            '_id': ObjectId(conversation_id),
            '$or': [
                {'user1_id': ObjectId(current_user.id)},
                {'user2_id': ObjectId(current_user.id)}
            ]
        })
        
        if not conversation:
            flash('Conversation not found or you do not have permission to view it', 'error')
            return redirect(url_for('messages.messages_list'))
        
        # Determine the other user in the conversation
        other_user_id = conversation['user2_id'] if str(conversation['user1_id']) == current_user.id else conversation['user1_id']
        
        # Get other user's details
        other_user = collection_users.find_one({'_id': other_user_id})
        if not other_user:
            flash('The other participant in this conversation could not be found', 'error')
            return redirect(url_for('messages.messages_list'))
            
        # Get additional details based on user type
        display_name = other_user.get('name', 'Unknown User')
        profile_pic = None
        user_type = other_user.get('user_type')
        
        if user_type == 'seeker':
            # Get job seeker details
            seeker = collection_resume.find_one({'user_id': other_user_id})
            if seeker:
                personal_info = seeker.get('personal_info', {})
                display_name = personal_info.get('full_name', display_name)
                profile_pic = seeker.get('profile_photo')
        elif user_type == 'recruiter':
            # Get recruiter details
            recruiter = collection_recruiter_registration.find_one({'user_id': other_user_id})
            if recruiter:
                display_name = recruiter.get('company_name', display_name)
                profile_pic = recruiter.get('company_logo')
        
        # Get messages for this conversation
        messages = collection_messages.find(
            {'conversation_id': ObjectId(conversation_id)}
        ).sort('timestamp', 1)  # Sort by timestamp ascending
        
        # Process messages
        messages_list = []
        for msg in messages:
            is_self = str(msg['sender_id']) == current_user.id
            messages_list.append({
                'id': str(msg['_id']),
                'content': msg['content'],
                'timestamp': format_timestamp(msg['timestamp']),
                'is_self': is_self
            })
        
        # Reset unread count for current user
        if str(conversation['user1_id']) == current_user.id:
            collection_conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$set': {'unread_count_user1': 0}}
            )
        else:
            collection_conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$set': {'unread_count_user2': 0}}
            )
        
        return render_template('messages/conversation.html', 
                              conversation_id=conversation_id,
                              other_user={
                                  'id': str(other_user_id),
                                  'name': display_name,
                                  'profile_pic': profile_pic,
                                  'user_type': user_type
                              },
                              messages=messages_list)
        
    except Exception as e:
        current_app.logger.error(f"Error in view_conversation: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        flash('An error occurred while loading the conversation', 'error')
        return redirect(url_for('messages.messages_list'))

@messages_bp.route('/messages/<conversation_id>/send', methods=['POST'])
@login_required
def send_message(conversation_id):
    """Send a new message in a conversation"""
    try:
        # Get message content
        content = request.form.get('message')
        if not content or content.strip() == '':
            return jsonify({'success': False, 'message': 'Message cannot be empty'}), 400
        
        # Verify conversation exists and user is a participant
        conversation = collection_conversations.find_one({
            '_id': ObjectId(conversation_id),
            '$or': [
                {'user1_id': ObjectId(current_user.id)},
                {'user2_id': ObjectId(current_user.id)}
            ]
        })
        
        if not conversation:
            return jsonify({'success': False, 'message': 'Conversation not found or access denied'}), 404
        
        # Determine the other user for unread count update
        is_user1 = str(conversation['user1_id']) == current_user.id
        other_user_id = conversation['user2_id'] if is_user1 else conversation['user1_id']
        
        # Create new message
        new_message = {
            'conversation_id': ObjectId(conversation_id),
            'sender_id': ObjectId(current_user.id),
            'content': content,
            'timestamp': datetime.now(),
            'is_read': False
        }
        
        # Insert message
        result = collection_messages.insert_one(new_message)
        
        # Update conversation last_message_at and increment unread count for other user
        update_data = {
            'last_message_at': datetime.now()
        }
        
        # Increment unread count for the recipient
        if is_user1:
            update_data['$inc'] = {'unread_count_user2': 1}
        else:
            update_data['$inc'] = {'unread_count_user1': 1}
        
        collection_conversations.update_one(
            {'_id': ObjectId(conversation_id)},
            {'$set': {'last_message_at': datetime.now()}}
        )
        
        # Increment the unread count in a separate operation to avoid issues with $set and $inc
        if is_user1:
            collection_conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$inc': {'unread_count_user2': 1}}
            )
        else:
            collection_conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$inc': {'unread_count_user1': 1}}
            )
        
        # Format timestamp for response
        formatted_time = format_timestamp(new_message['timestamp'])
        
        return jsonify({
            'success': True,
            'message_id': str(result.inserted_id),
            'timestamp': formatted_time
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in send_message: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': 'An error occurred while sending the message'}), 500

def format_timestamp(timestamp):
    """Format timestamp for display"""
    now = datetime.now()
    diff = now - timestamp
    
    if diff.days == 0:
        # Today
        return timestamp.strftime('%I:%M %p')
    elif diff.days == 1:
        # Yesterday
        return 'Yesterday'
    elif diff.days < 7:
        # This week
        return timestamp.strftime('%A')  # Day name
    else:
        # Older
        return timestamp.strftime('%b %d')  # Month day 