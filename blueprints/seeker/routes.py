import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response, jsonify, current_app, render_template_string
from flask_login import current_user, login_required
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import pdfkit
from datetime import datetime
import traceback
import json
import traceback
from src.components.job_recommender import get_job_recommendations
import pandas as pd

# Use environment variables for sensitive information
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_resume_details = db.tbl_resume_details
collection_login_credentials = db.tbl_login_credentials
collection_recruiter_registration = db.tbl_recruiter_registration
collection_jobs = db.tbl_jobs
collection_job_types = db.tbl_job_type
collection_experience_levels = db.tbl_experience_type
collection_notifications = db.tbl_notifications


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
        total_experience = request.form.get('total_experience')

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

        technical_skills = request.form.getlist('technical_skills[]')
        soft_skills = request.form.getlist('soft_skills[]')
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
            "total_experience": float(total_experience) if total_experience else None,
            "work_experience": work_experience,
            "education": education,
            "technical_skills": technical_skills,
            "soft_skills": soft_skills,
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

    # Fetch skill recommendations
    technical_skills_recommendations = get_skill_recommendations('technical_skills')
    soft_skills_recommendations = get_skill_recommendations('soft_skills')

    return render_template('seeker/viewprofile.html', 
                           user=current_user, 
                           resume=resume_document,
                           technical_skills_recommendations=technical_skills_recommendations,
                           soft_skills_recommendations=soft_skills_recommendations)

def get_skill_recommendations(skill_type):
    # Aggregate skills from jobs
    job_skills = collection_jobs.aggregate([
        {'$unwind': f'${skill_type}'},
        {'$group': {'_id': f'${skill_type}'}},
        {'$limit': 100}  # Limit to top 100 skills
    ])

    # Aggregate skills from resumes
    resume_skills = collection_resume_details.aggregate([
        {'$unwind': f'${skill_type}'},
        {'$group': {'_id': f'${skill_type}'}},
        {'$limit': 100}  # Limit to top 100 skills
    ])

    # Combine and deduplicate skills
    all_skills = set(doc['_id'] for doc in job_skills) | set(doc['_id'] for doc in resume_skills)
    return sorted(list(all_skills))

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

@seeker_bp.route('/job_postings', methods=['GET'])
@login_required
def job_postings():
    filter_options = get_filter_options()
    return render_template('seeker/job_postings.html', filter_options=filter_options)

@seeker_bp.route('/get_filtered_jobs', methods=['GET'])
@login_required
def get_filtered_jobs():
    try:
        locations = request.args.getlist('location')
        job_types = request.args.getlist('job_type')
        experience_levels = request.args.getlist('experience_level')
        salary_min = request.args.get('salary_min')
        salary_max = request.args.get('salary_max')

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
                '$unwind': {'path': '$recruiter_info', 'preserveNullAndEmptyArrays': True}
            },
            {
                '$lookup': {
                    'from': 'tbl_job_type',
                    'localField': 'job_type',
                    'foreignField': '_id',
                    'as': 'job_type_info'
                }
            },
            {
                '$unwind': {'path': '$job_type_info', 'preserveNullAndEmptyArrays': True}
            },
            {
                '$lookup': {
                    'from': 'tbl_experience_type',
                    'localField': 'experience_level',
                    'foreignField': '_id',
                    'as': 'experience_level_info'
                }
            },
            {
                '$unwind': {'path': '$experience_level_info', 'preserveNullAndEmptyArrays': True}
            }
        ]

        match_conditions = {}
        if locations:
            match_conditions['location'] = {'$in': locations}
        if job_types:
            match_conditions['job_type_info.type'] = {'$in': job_types}
        if experience_levels:
            match_conditions['experience_level_info.type'] = {'$in': experience_levels}
        if salary_min and salary_max:
            salary_min = float(salary_min)
            salary_max = float(salary_max)
            match_conditions['$or'] = [
                {'$and': [{'salary_min': {'$gte': salary_min}}, {'salary_min': {'$lte': salary_max}}]},
                {'$and': [{'salary_max': {'$gte': salary_min}}, {'salary_max': {'$lte': salary_max}}]},
                {'$and': [{'salary_min': {'$lte': salary_min}}, {'salary_max': {'$gte': salary_max}}]}
            ]

        if match_conditions:
            pipeline.append({'$match': match_conditions})

        pipeline.append({
            '$project': {
                '_id': {'$toString': '$_id'},
                'title': 1,
                'location': 1,
                'job_type': '$job_type_info.type',
                'experience_level': '$experience_level_info.type',
                'description': 1,
                'company': {'$ifNull': ['$recruiter_info.company_name', 'Unknown']},
                'salary_min': 1,
                'salary_max': 1,
                'created_at': 1
            }
        })

        current_app.logger.info(f"Aggregation pipeline: {pipeline}")
        
        jobs = list(collection_jobs.aggregate(pipeline))
        current_app.logger.info(f"Number of jobs found: {len(jobs)}")
        
        return jsonify(jobs)
    except Exception as e:
        current_app.logger.error(f"Error in get_filtered_jobs: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': 'An error occurred while fetching jobs'}), 500

def get_filter_options():
    try:
        pipeline = [
            {
                '$lookup': {
                    'from': 'tbl_job_type',
                    'localField': 'job_type',
                    'foreignField': '_id',
                    'as': 'job_type_info'
                }
            },
            {
                '$unwind': {'path': '$job_type_info', 'preserveNullAndEmptyArrays': True}
            },
            {
                '$lookup': {
                    'from': 'tbl_experience_type',
                    'localField': 'experience_level',
                    'foreignField': '_id',
                    'as': 'experience_level_info'
                }
            },
            {
                '$unwind': {'path': '$experience_level_info', 'preserveNullAndEmptyArrays': True}
            },
            {
                '$group': {
                    '_id': None,
                    'locations': {'$addToSet': '$location'},
                    'job_types': {'$addToSet': '$job_type_info.type'},
                    'experience_levels': {'$addToSet': '$experience_level_info.type'},
                    'min_salary': {'$min': '$salary_min'},
                    'max_salary': {'$max': '$salary_max'}
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'locations': 1,
                    'job_types': 1,
                    'experience_levels': 1,
                    'salary_range': {
                        'min': {'$ifNull': ['$min_salary', 0]},
                        'max': {'$ifNull': ['$max_salary', 100]}
                    }
                }
            }
        ]

        result = list(collection_jobs.aggregate(pipeline))
        
        if result:
            filter_options = result[0]
        else:
            filter_options = {
                'locations': [],
                'job_types': [],
                'experience_levels': [],
                'salary_range': {'min': 0, 'max': 100}
            }

        current_app.logger.info(f"Filter options: {filter_options}")
        return filter_options
    except Exception as e:
        current_app.logger.error(f"Error in get_filter_options: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return {
            'locations': [],
            'job_types': [],
            'experience_levels': [],
            'salary_range': {'min': 0, 'max': 100}
        }

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
        {'$lookup': {
            'from': 'tbl_job_type',
            'localField': 'job_type',
            'foreignField': '_id',
            'as': 'job_type_info'
        }},
        {'$unwind': '$job_type_info'},
        {'$lookup': {
            'from': 'tbl_experience_type',
            'localField': 'experience_level',
            'foreignField': '_id',
            'as': 'experience_level_info'
        }},
        {'$unwind': '$experience_level_info'},
        {'$project': {
            '_id': 1,
            'title': 1,
            'location': 1,
            'job_type': '$job_type_info.type',
            'description': 1,
            'company': '$recruiter_info.company_name',
            'requirements': 1,
            'responsibilities': 1,
            'salary_min': 1,
            'salary_max': 1,
            'experience': 1,
            'education': 1,
            'soft_skills': 1,
            'technical_skills': 1,
            'application_deadline': 1,
            'experience_level': '$experience_level_info.type'
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
        
        # Convert application_deadline to a readable format
        if 'application_deadline' in job and job['application_deadline']:
            job['application_deadline'] = job['application_deadline'].strftime('%Y-%m-%d')
        
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
            return jsonify({'success': False, 'message': 'Job not found'})

        # Check if the user has already applied
        existing_application = db.tbl_job_applications.find_one({
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id)
        })

        if existing_application:
            return jsonify({'success': False, 'message': 'You have already applied for this job'})

        # Create a new application
        application = {
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id),
            'applied_at': datetime.utcnow(),
            'status': 'pending'
        }

        # Insert the application into the database
        db.tbl_job_applications.insert_one(application)

        # Prepare the HTML for the updated application status
        html = render_template_string('''
            <button class="btn btn-secondary mt-4" disabled>Applied</button>
            <button id="cancel-application" class="btn btn-danger mt-4">Cancel Application</button>
        ''')

        return jsonify({
            'success': True,
            'message': 'Your application has been submitted successfully!',
            'html': html
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred while processing your application: {str(e)}'
        })

@seeker_bp.route('/cancel_application/<job_id>', methods=['POST'])
@login_required
def cancel_application(job_id):
    try:
        # Check if the job exists
        job = collection_jobs.find_one({'_id': ObjectId(job_id)})
        if not job:
            return jsonify({'success': False, 'message': 'Job not found'})

        # Find and delete the application
        result = db.tbl_job_applications.delete_one({
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id)
        })

        if result.deleted_count > 0:
            # Prepare the HTML for the updated application status
            html = render_template_string('''
                <button id="apply-job" class="btn btn-primary mt-4">Apply Now</button>
            ''')

            return jsonify({
                'success': True,
                'message': 'Your application has been canceled successfully.',
                'html': html
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No application found for this job.'
            })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'An error occurred while canceling your application: {str(e)}'
        })

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
        job_type = request.args.get('job_type')
        location = request.args.get('location')
        experience_level = request.args.get('experience_level')
        salary_min = request.args.get('salary_min')
        salary_max = request.args.get('salary_max')
        
        current_app.logger.info(f"Received search query: {query}, filters: job_type={job_type}, location={location}, experience_level={experience_level}, salary_min={salary_min}, salary_max={salary_max}")
        
        match_conditions = [
            {'$or': [
                {'title': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}},
                {'recruiter_info.company_name': {'$regex': query, '$options': 'i'}}
            ]}
        ]

        if job_type:
            match_conditions.append({'job_type': job_type})
        if location:
            match_conditions.append({'location': {'$regex': location, '$options': 'i'}})
        if experience_level:
            match_conditions.append({'experience_level': experience_level})
        if salary_min:
            match_conditions.append({'salary_min': {'$gte': int(salary_min)}})
        if salary_max:
            match_conditions.append({'salary_max': {'$lte': int(salary_max)}})

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
                '$match': {'$and': match_conditions}
            },
            {
                '$project': {
                    'id': {'$toString': '$_id'},
                    'title': 1,
                    'location': 1,
                    'job_type': 1,
                    'description': 1,
                    'company': {'$ifNull': ['$recruiter_info.company_name', 'Unknown']},
                    'salary_min': 1,
                    'salary_max': 1,
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
        
        return current_app.response_class(
            json.dumps(jobs, cls=JSONEncoder),
            mimetype='application/json'
        )
    except Exception as e:
        current_app.logger.error(f"Error in search_jobs: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({'error': 'An internal server error occurred', 'details': str(e)}), 500

@seeker_bp.route('/recommendations', methods=['GET', 'POST'])
@login_required
def recommendations():
    recommended_jobs = []  # Initialize as an empty list
    if request.method == 'POST':
        skills_string = request.form.get('skills', '').strip()
        if skills_string:
            recommended_jobs = get_job_recommendations(skills_string)
            if not recommended_jobs:
                flash('No job recommendations found based on your skills. Try different skills.', 'info')
        else:
            flash('Please enter at least one skill.', 'warning')
    else:  # GET request
        resume = collection_resume_details.find_one({"user_id": ObjectId(current_user.id)})
        if resume:
            user_skills = resume.get('technical_skills', []) + resume.get('soft_skills', [])
            if user_skills:
                skills_string = ', '.join(user_skills)
                recommended_jobs = get_job_recommendations(skills_string)
                if not recommended_jobs:
                    flash('No job recommendations found based on your profile skills. Try updating your skills.', 'info')
            else:
                flash('No skills found in your profile. Please update your profile with your skills.', 'warning')
        else:
            flash('Please complete your profile to get job recommendations.', 'warning')

    # Limit to top 3 recommendations
    recommended_jobs = recommended_jobs[:3] if recommended_jobs else []

    return render_template('seeker/recommendations.html', recommended_jobs=recommended_jobs)