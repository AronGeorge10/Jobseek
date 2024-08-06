from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from datetime import datetime

recruiter_bp = Blueprint('recruiter', __name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:AronJain@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_jobs = db.tbl_jobs
collection_applications = db.tbl_applications

@recruiter_bp.route('/index')
@login_required
def recruiter_index():
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Fetch jobs posted by this recruiter
    jobs = collection_jobs.find({'recruiter_id': current_user.id})
    return render_template('recruiter/recruiter_index.html', jobs=jobs)

@recruiter_bp.route('/post_job', methods=['GET', 'POST'])
@login_required
def post_job():
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        job_data = {
            'title': request.form['title'],
            'description': request.form['description'],
            'requirements': request.form.getlist('requirements[]'),
            'responsibilities': request.form.getlist('responsibilities[]'),  # Add this line
            'salary': request.form['salary'],
            'location': request.form['location'],
            'company': request.form['company'],
            'job_type': request.form['job_type'],
            'experience_level': request.form['experience_level'],
            'recruiter_id': current_user.id,
            'created_at': datetime.utcnow()
        }
        collection_jobs.insert_one(job_data)
        flash('Job posted successfully!', 'success')
        return redirect(url_for('recruiter.recruiter_index'))
    
    return render_template('recruiter/post_job.html')

@recruiter_bp.route('/view_applications/<job_id>')
@login_required
def view_applications(job_id):
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    job = collection_jobs.find_one({'_id': ObjectId(job_id), 'recruiter_id': current_user.id})
    if not job:
        flash('Job not found or access denied.', 'error')
        return redirect(url_for('recruiter.dashboard'))
    
    applications = collection_applications.find({'job_id': job_id})
    return render_template('recruiter/view_applications.html', job=job, applications=applications)

@recruiter_bp.route('/update_application_status/<application_id>', methods=['POST'])
@login_required
def update_application_status(application_id):
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    new_status = request.form['status']
    collection_applications.update_one(
        {'_id': ObjectId(application_id)},
        {'$set': {'status': new_status}}
    )
    flash('Application status updated successfully!', 'success')
    return redirect(url_for('recruiter.dashboard'))

# Add more routes as needed