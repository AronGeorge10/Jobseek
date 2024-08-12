import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response, jsonify, current_app
from flask_login import current_user, login_required
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import pdfkit
from datetime import datetime
import traceback
import json

# Use environment variables for sensitive information
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_resume_details = db.tbl_resume_details
collection_login_credentials = db.tbl_login_credentials
collection_jobs = db.tbl_jobs
collection_notifications = db.tbl_notifications
collection_recruiter_registration = db.tbl_recruiter_registration

seeker_bp = Blueprint('seeker', __name__)

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

@seeker_bp.route('/viewprofile', methods=['GET', 'POST'])
@login_required
def viewprofile():
    if request.method == 'POST':
        print("Form submitted")  # Debug print
        # Retrieve form data
        full_name = request.form.get('fullname')
        job_title = request.form.get('job_title')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        linkedin = request.form.get('linkedin')
        summary = request.form.get('summary')

        # Retrieve dynamic form data
        work_experience = []
        for job, duration, company, responsibility in zip(request.form.getlist('job_title[]'), 
                                                                request.form.getlist('duration[]'), 
                                                                request.form.getlist('company[]'), 
                                                                request.form.getlist('responsibility[]')):
            work_experience.append({
                "job_title": job,
                "duration": duration,
                "company": company,
                "responsibility": responsibility
            })

        education = []
        for degree, university, graduation_year in zip(request.form.getlist('degree[]'), 
                                                       request.form.getlist('university[]'), 
                                                       request.form.getlist('graduation_year[]')):
            education.append({
                "degree": degree,
                "university": university,
                "graduation_year": graduation_year
            })

        skills = request.form.getlist('skills[]')
        certifications = request.form.getlist('certifications[]')
        
        projects = []
        for project, description in zip(request.form.getlist('projects[]'), 
                                        request.form.getlist('project_descriptions[]')):
            projects.append({
                "project_name": project,
                "description": description
            })

        # Prepare resume data
        resume = {
            "full_name": full_name,
            "job_title": job_title,
            "email": email,
            "phone": phone,
            "address": address,
            "linkedin": linkedin,
            "summary": summary,
            "work_experience": work_experience,
            "education": education,
            "skills": skills,
            "certifications": certifications,
            "projects": projects
        }

        # Improve file handling
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture.filename != '':
                if profile_picture.content_type.startswith('image/'):
                    filename = secure_filename(profile_picture.filename)
                    profile_picture_data = profile_picture.read()
                    if len(profile_picture_data) <= 5 * 1024 * 1024:  # 5MB limit
                        resume["profile_picture"] = profile_picture_data
                    else:
                        flash('Profile picture size should be less than 5MB.', 'error')
                else:
                    flash('Invalid file type. Please upload an image.', 'error')

        # Find the user's resume document in the collection
        resume_document = collection_resume_details.find_one({"user_id": ObjectId(current_user.id)})

        if resume_document:
            print("Updating existing resume")  # Debug print
            result = collection_resume_details.update_one(
                {"user_id": ObjectId(current_user.id)},
                {"$set": resume}
            )
            print(f"Update result: {result.modified_count}")  # Debug print
        else:
            print("Inserting new resume")  # Debug print
            resume["user_id"] = ObjectId(current_user.id)
            result = collection_resume_details.insert_one(resume)
            print(f"Insert result: {result.inserted_id}")  # Debug print

        print("Resume updated/inserted")  # Debug print
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('seeker.viewprofile'))

    # GET request handling
    print("GET request")  # Debug print
    login_credentials = collection_login_credentials.find_one({"_id": ObjectId(current_user.id)})
    user_id = login_credentials.get('_id')
    
    resume_document = collection_resume_details.find_one({"user_id": ObjectId(user_id)})
    print(f"Resume document: {resume_document}")  # Debug print

    return render_template('seeker/viewprofile.html', user=current_user, resume=resume_document)

@seeker_bp.route('/profile_picture/<user_id>')
@login_required
def profile_picture(user_id):
    resume_document = collection_resume_details.find_one({"user_id": ObjectId(user_id)})
    if resume_document and "profile_picture" in resume_document:
        return resume_document["profile_picture"]
    else:
        return "", 404

path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

@seeker_bp.route('/generate_pdf', methods=['GET'])
@login_required
def generate_pdf():
    # Retrieve resume document for the current user
    resume_document = collection_resume_details.find_one({"user_id": ObjectId(current_user.id)})

    if not resume_document:
        flash('No resume found for the current user.', 'danger')
        return redirect(url_for('seeker.viewprofile'))

    # Render the HTML template for the resume
    html = render_template('seeker/resume_template.html', resume=resume_document)
    
    try:
        # Generate PDF from the HTML content
        pdf = pdfkit.from_string(html, False, configuration=config)
    except Exception as e:
        flash(f'An error occurred while generating the PDF: {e}', 'danger')
        return redirect(url_for('seeker.viewprofile'))

    # Prepare the response
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=resume.pdf'

    return response

@seeker_bp.route('/job_postings', methods=['GET', 'POST'])
@login_required
def job_postings():
    try:
        # Debug: Print the total number of jobs and recruiters
        total_jobs = collection_jobs.count_documents({})
        total_recruiters = collection_recruiter_registration.count_documents({})
        print(f"Total jobs in collection: {total_jobs}")
        print(f"Total recruiters in collection: {total_recruiters}")

        # Debug: Print a sample job document
        sample_job = collection_jobs.find_one()
        print(f"Sample job document: {sample_job}")

        # Debug: Print a sample recruiter document
        sample_recruiter = collection_recruiter_registration.find_one()
        print(f"Sample recruiter document: {sample_recruiter}")

        # Updated aggregation pipeline with correct field for lookup
        jobs_with_company = list(collection_jobs.aggregate([
            {
                '$lookup': {
                    'from': 'tbl_recruiter_registration',
                    'localField': 'recruiter_id',
                    'foreignField': 'user_id',
                    'as': 'recruiter_info'
                }
            },
            {
                '$unwind': '$recruiter_info'
            },
            {
                '$project': {
                    '_id': 1,
                    'title': 1,
                    'location': 1,
                    'job_type': 1,
                    'description': 1,
                    'company': '$recruiter_info.company_name',
                    'recruiter_id': 1,
                    'recruiter_user_id': '$recruiter_info.user_id'
                }
            }
        ]))
        
        print(f"Number of jobs found (with lookup): {len(jobs_with_company)}")
        for job in jobs_with_company:
            print(f"Job: {job['title']}, Recruiter ID: {job['recruiter_id']}, Recruiter User ID: {job['recruiter_user_id']}")

        # Fetch applied jobs for the current user
        applied_jobs = list(db.tbl_job_applications.aggregate([
            {'$match': {'user_id': ObjectId(current_user.id)}},
            {'$lookup': {
                'from': 'tbl_jobs',
                'localField': 'job_id',
                'foreignField': '_id',
                'as': 'job_details'
            }},
            {'$unwind': '$job_details'},
            {'$lookup': {
                'from': 'tbl_recruiter_registration',
                'localField': 'job_details.recruiter_id',
                'foreignField': 'user_id',
                'as': 'recruiter_info'
            }},
            {'$unwind': '$recruiter_info'},
            {'$project': {
                '_id': '$job_details._id',
                'title': '$job_details.title',
                'company': '$recruiter_info.company_name',
                'location': '$job_details.location',
                'job_type': '$job_details.job_type',
                'description': '$job_details.description',
                'is_shortlisted': {'$eq': ['$status', 'shortlisted']}
            }}
        ]))
        
        print(f"Number of applied jobs: {len(applied_jobs)}")

        if not jobs_with_company and not applied_jobs:
            flash('No jobs found. The job database might be empty.', 'info')
        
        return render_template('seeker/job_postings.html', jobs=jobs_with_company, applied_jobs=applied_jobs)
    
    except Exception as e:
        print(f"Error in job_postings: {str(e)}")
        flash('An error occurred while fetching job postings. Please try again later.', 'error')
        return render_template('seeker/job_postings.html', jobs=[], applied_jobs=[])

@seeker_bp.route('/view_job/<job_id>')
@login_required
def view_job(job_id):
    job = collection_jobs.aggregate([
        {'$match': {'_id': ObjectId(job_id)}},
        {'$lookup': {
            'from': 'tbl_recruiter_registration',
            'localField': 'recruiter_id',
            'foreignField': 'user_id',
            'as': 'recruiter_info'
        }},
        {'$unwind': '$recruiter_info'},
        {'$project': {
            '_id': 1,
            'title': 1,
            'location': 1,
            'job_type': 1,
            'description': 1,
            'company': '$recruiter_info.company_name',
            'requirements': 1,
            'responsibilities': 1,
            'salary': 1
        }}
    ]).next()

    if job:
        # Check if the user has already applied for this job
        application = db.tbl_job_applications.find_one({
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id)
        })
        
        has_applied = application is not None
        is_shortlisted = application['status'] == 'shortlisted' if application else False
        
        return render_template('seeker/view_job.html', job=job, has_applied=has_applied, is_shortlisted=is_shortlisted)
    else:
        flash('Job not found', 'error')
        return redirect(url_for('seeker.job_postings'))

@seeker_bp.route('/apply_job/<job_id>', methods=['POST'])
@login_required
def apply_job(job_id):
    try:
        # Check if the job exists
        job = collection_jobs.find_one({'_id': ObjectId(job_id)})
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('seeker.job_postings'))

        # Check if the user has already applied
        existing_application = db.tbl_job_applications.find_one({
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id)
        })

        if existing_application:
            flash('You have already applied for this job', 'info')
            return redirect(url_for('seeker.view_job', job_id=job_id))

        # Create a new application
        application = {
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id),
            'applied_at': datetime.utcnow(),
            'status': 'pending'
        }

        # Insert the application into the database
        db.tbl_job_applications.insert_one(application)

        flash('Your application has been submitted successfully!', 'success')
        return redirect(url_for('seeker.view_job', job_id=job_id))

    except Exception as e:
        flash(f'An error occurred while processing your application: {str(e)}', 'error')
        return redirect(url_for('seeker.view_job', job_id=job_id))

@seeker_bp.route('/cancel_application/<job_id>', methods=['POST'])
@login_required
def cancel_application(job_id):
    try:
        # Check if the job exists
        job = collection_jobs.find_one({'_id': ObjectId(job_id)})
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('seeker.job_postings'))

        # Find and delete the application
        result = db.tbl_job_applications.delete_one({
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id)
        })

        if result.deleted_count > 0:
            flash('Your application has been canceled successfully.', 'success')
        else:
            flash('No application found for this job.', 'info')

        return redirect(url_for('seeker.view_job', job_id=job_id))

    except Exception as e:
        flash(f'An error occurred while canceling your application: {str(e)}', 'error')
        return redirect(url_for('seeker.view_job', job_id=job_id))

@seeker_bp.route('/notifications')
@login_required
def get_notifications():
    try:
        notifications = list(collection_notifications.find(
            {'user_id': ObjectId(current_user.id)}
        ).sort('created_at', -1).limit(10))
        
        serializable_notifications = []
        for notification in notifications:
            serializable_notification = {
                '_id': str(notification['_id']),
                'user_id': str(notification['user_id']),
                'message': notification['message'],
                'created_at': notification['created_at'].isoformat(),
                'is_read': notification['is_read'],
                'job_id': str(notification['job_id']) if 'job_id' in notification else None
            }
            serializable_notifications.append(serializable_notification)

        return jsonify(serializable_notifications)
    except Exception as e:
        current_app.logger.error(f"Error in get_notifications: {str(e)}")
        return jsonify({'error': 'An internal server error occurred'}), 500

@seeker_bp.route('/mark_notification_read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        result = collection_notifications.update_one(
            {'_id': ObjectId(notification_id), 'user_id': ObjectId(current_user.id)},
            {'$set': {'is_read': True}}
        )

        if result.modified_count > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Notification not found or already read'}), 404
    except Exception as e:
        current_app.logger.error(f"Error in mark_notification_read: {str(e)}")
        return jsonify({'success': False, 'error': 'An internal server error occurred'}), 500

@seeker_bp.route('/search_jobs', methods=['GET'])
@login_required
def search_jobs():
    try:
        query = request.args.get('query', '')
        
        current_app.logger.info(f"Received search query: {query}")
        
        pipeline = [
            {
                '$lookup': {
                    'from': 'tbl_recruiter_registration',
                    'localField': 'recruiter_id',
                    'foreignField': 'user_id',
                    'as': 'recruiter_info'
                }
            },
            {
                '$unwind': {
                    'path': '$recruiter_info',
                    'preserveNullAndEmptyArrays': True
                }
            },
            {
                '$match': {
                    '$or': [
                        {'title': {'$regex': query, '$options': 'i'}},
                        {'description': {'$regex': query, '$options': 'i'}},
                        {'recruiter_info.company_name': {'$regex': query, '$options': 'i'}}
                    ]
                }
            },
            {
                '$project': {
                    'id': {'$toString': '$_id'},
                    'title': 1,
                    'location': 1,
                    'job_type': 1,
                    'description': 1,
                    'company': {'$ifNull': ['$recruiter_info.company_name', 'Unknown']},
                    'salary': 1,
                    'experience_level': 1,
                    'created_at': {
                        '$dateToString': {
                            'format': "%Y-%m-%d",
                            'date': {'$ifNull': ['$created_at', datetime.utcnow()]}
                        }
                    }
                }
            }
        ]
        
        current_app.logger.info(f"Aggregation pipeline: {pipeline}")
        
        jobs = list(collection_jobs.aggregate(pipeline))
        
        current_app.logger.info(f"Number of jobs found: {len(jobs)}")
        
        # Use the custom JSONEncoder to serialize the response
        return current_app.response_class(
            json.dumps(jobs, cls=JSONEncoder),
            mimetype='application/json'
        )
    except Exception as e:
        current_app.logger.error(f"Error in search_jobs: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred', 'details': str(e)}), 500