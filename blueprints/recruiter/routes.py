from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response, jsonify
from flask_login import current_user, login_required
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import current_app
import pdfkit
from bson.errors import InvalidId

recruiter_bp = Blueprint('recruiter', __name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_recruiter_registration = db.tbl_recruiter_registration
collection_jobs = db.tbl_jobs
collection_applications = db.tbl_job_applications
collection_resume = db.tbl_resume_details
collection_notifications = db.tbl_notifications

@recruiter_bp.route('/index')
@login_required
def recruiter_index():
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Fetch jobs posted by this recruiter
    jobs = collection_jobs.find({'recruiter_id': ObjectId(current_user.id)})
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
            'job_type': request.form['job_type'],
            'experience_level': request.form['experience_level'],
            'recruiter_id': ObjectId(current_user.id),
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
    
    # Fetch the job with recruiter_id filter
    job = collection_jobs.find_one({'_id': ObjectId(job_id), 'recruiter_id': ObjectId(current_user.id)})
    if not job:
        flash('Job not found or access denied.', 'error')
        return redirect(url_for('recruiter.recruiter_index'))
    
    # Fetch applications for this job, using ObjectId
    applications = list(collection_applications.find({'job_id': ObjectId(job_id)}))
    
    for app in applications:
        app['id'] = str(app['_id'])
        app['user_id'] = str(app['user_id'])
        app['applied_at'] = app['applied_at'].strftime('%Y-%m-%d %H:%M:%S') if app.get('applied_at') else 'N/A'
        
        # Fetch user details for each application
        user = collection_resume.find_one({'user_id': ObjectId(app['user_id'])})
        if user:
            app['applicant_name'] = user.get('full_name', 'Unknown')
            app['applicant_email'] = user.get('email', 'N/A')
        else:
            app['applicant_name'] = 'Unknown'
            app['applicant_email'] = 'N/A'
    
    return render_template('recruiter/view_applications.html', job=job, app=applications)

@recruiter_bp.route('/posted_jobs')
@login_required
def posted_jobs():
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Fetch recruiter details to get the company name
    recruiter = collection_recruiter_registration.find_one({'user_id': ObjectId(current_user.id)})
    company_name = recruiter.get('company_name', 'Unknown Company') if recruiter else 'Unknown Company'
    
    # Fetch jobs posted by this recruiter
    jobs = list(collection_jobs.find({'recruiter_id': ObjectId(current_user.id)}).sort('created_at', -1))
    
    return render_template('recruiter/posted_jobs.html', jobs=jobs, company_name=company_name)

path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

@recruiter_bp.route('/view_applicant_resume/<applicant_id>')
@login_required
def view_applicant_resume(applicant_id):
    # Check if the current user is a recruiter
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))

    # Retrieve resume document for the applicant
    resume_document = collection_resume.find_one({"user_id": ObjectId(applicant_id)})

    if not resume_document:
        flash('No resume found for the applicant.', 'danger')
        return redirect(url_for('recruiter.posted_jobs'))

    # Render the HTML template for the resume
    html = render_template('recruiter/view_applicant_resume.html', resume=resume_document)
    
    try:
        # Generate PDF from the HTML content
        pdf = pdfkit.from_string(html, False, configuration=config)
    except Exception as e:
        flash(f'An error occurred while generating the PDF: {e}', 'danger')
        return redirect(url_for('recruiter.posted_jobs'))

    # Prepare the response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=applicant_resume.pdf'

    return response

@recruiter_bp.route('/edit_job/<job_id>', methods=['GET', 'POST'])
@login_required
def edit_job(job_id):
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    try:
        job = collection_jobs.find_one({'_id': ObjectId(job_id), 'recruiter_id': ObjectId(current_user.id)})
    except InvalidId:
        flash('Invalid job ID.', 'error')
        return redirect(url_for('recruiter.recruiter_index'))
    
    if not job:
        flash('Job not found or access denied.', 'error')
        return redirect(url_for('recruiter.recruiter_index'))

    if request.method == 'POST':
        updated_job = {
            'title': request.form['title'],
            'description': request.form['description'],
            'requirements': request.form.getlist('requirements[]'),
            'responsibilities': request.form.getlist('responsibilities[]'),
            'salary': request.form['salary'],
            'location': request.form['location'],
            'company': request.form['company'],
            'job_type': request.form['job_type'],
            'experience_level': request.form['experience_level'],
            'updated_at': datetime.utcnow()
        }
        collection_jobs.update_one({'_id': ObjectId(job_id)}, {'$set': updated_job})
        flash('Job updated successfully!', 'success')
        return redirect(url_for('recruiter.posted_jobs'))
    
    return render_template('recruiter/edit_job.html', job=job)

@recruiter_bp.route('/get_job_data/<job_id>')
@login_required
def get_job_data(job_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        job = collection_jobs.find_one({'_id': ObjectId(job_id), 'recruiter_id': ObjectId(current_user.id)})
    except InvalidId:
        return jsonify({'error': 'Invalid job ID'}), 400
    
    if not job:
        return jsonify({'error': 'Job not found or access denied'}), 404
    
    job_data = {
        'title': job['title'],
        'description': job['description'],
        'requirements': job['requirements'],
        'responsibilities': job['responsibilities'],
        'salary': job['salary'],
        'location': job['location'],
        'company': job['company'],
        'job_type': job['job_type'],
        'experience_level': job['experience_level']
    }
    return jsonify(job_data)

@recruiter_bp.route('/search_jobs')
@login_required
def search_jobs():
    if current_user.user_type != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403

    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'error': 'No search query provided'}), 400

    # Search for jobs posted by the current recruiter
    search_results = collection_jobs.find({
        'recruiter_id': ObjectId(current_user.id),
        '$or': [
            {'title': {'$regex': query, '$options': 'i'}},
            {'description': {'$regex': query, '$options': 'i'}},
            {'location': {'$regex': query, '$options': 'i'}}
        ]
    }).sort('created_at', -1)

    # Convert the search results to a list of dictionaries
    results = []
    for job in search_results:
        results.append({
            'id': str(job['_id']),
            'title': job['title'],
            'location': job['location'],
            'job_type': job['job_type'],
            'salary': job['salary'],
            'experience_level': job['experience_level'],
            'created_at': job['created_at'].strftime('%Y-%m-%d')
        })

    return jsonify(results)

@recruiter_bp.route('/shortlist/<application_id>', methods=['POST'])
@login_required
def shortlist_application(application_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        application = collection_applications.find_one({'_id': ObjectId(application_id)})
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Check if the job belongs to the current recruiter
        job = collection_jobs.find_one({'_id': application['job_id'], 'recruiter_id': ObjectId(current_user.id)})
        if not job:
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Fetch recruiter details to get the company name
        recruiter = collection_recruiter_registration.find_one({'user_id': ObjectId(current_user.id)})
        company_name = recruiter.get('company_name', 'Unknown Company') if recruiter else 'Unknown Company'
        
        new_status = 'shortlisted' if application['status'] != 'shortlisted' else 'applied'
        result = collection_applications.update_one(
            {'_id': ObjectId(application_id)},
            {'$set': {'status': new_status}}
        )
        
        if result.modified_count > 0:
            # Add notification if the new status is 'shortlisted'
            if new_status == 'shortlisted':
                notification = {
                    'user_id': application['user_id'],
                    'job_id': job['_id'],
                    'message': f"You have been shortlisted for {job['title']} by {company_name}",
                    'created_at': datetime.utcnow(),
                    'is_read': False
                }
                collection_notifications.insert_one(notification)
            
            return jsonify({'success': True, 'new_status': new_status, 'message': 'Status updated successfully'})
        else:
            return jsonify({'success': True, 'new_status': application['status'], 'message': 'No changes were necessary'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in shortlisting application: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Add more routes as needed