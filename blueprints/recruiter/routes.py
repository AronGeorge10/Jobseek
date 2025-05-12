from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response, jsonify, session
from flask_login import current_user, login_required
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from flask import current_app
import pdfkit
from bson.errors import InvalidId
import bleach
import json
from apscheduler.schedulers.background import BackgroundScheduler
import stripe
from bson import json_util
import re
import traceback

stripe.api_key = 'sk_test_51MiftOSIxs4ZUV5mMRwCJZPY6Sa5xxQjwNW7j3NZ7Z0uAMdOZpfkJ8z5PXEvGURVzOkilzvmrTPVpn8vkZT7embw00HJuQCUXf'

recruiter_bp = Blueprint('recruiter', __name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:4E1zkxYGeaWZQCL8@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_recruiter_registration = db.tbl_recruiter_registration
collection_jobs = db.tbl_jobs
collection_job_types = db.tbl_job_type
collection_experience_levels = db.tbl_experience_type
collection_applications = db.tbl_job_applications
collection_resume = db.tbl_resume_details
collection_notifications = db.tbl_notifications
collection_payment = db.tbl_payment
collection_interviews = db.tbl_interviews
collection_connections = db.tbl_connections
collection_talent_pool = db['tbl_talent_pool']
collection_conversations = db.tbl_conversations

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
    
    # Fetch job types and experience levels from the database
    job_types = list(collection_job_types.find())
    experience_levels = list(collection_experience_levels.find())
    
    if request.method == 'POST':
        errors = {}

        # Validate all fields
        title = request.form.get('title', '').strip()
        if not title:
            errors['title'] = 'Job title is required'

        description = request.form.get('description', '').strip()
        if not description:
            errors['description'] = 'Job description is required'

        responsibilities = json.loads(request.form.get('responsibilities', '[]'))
        if not responsibilities:
            errors['responsibilities'] = 'Job responsibilities are required'

        requirements = json.loads(request.form.get('requirements', '[]'))
        if not requirements:
            errors['requirements'] = 'Job requirements are required'

        recruitment_procedure = json.loads(request.form.get('recruitment_procedure', '[]'))
        if not recruitment_procedure:
            errors['recruitment_procedure'] = 'Recruitment procedure is required'

        soft_skills = request.form.getlist('soft_skills[]')
        if not soft_skills:
            errors['skills'] = 'At least one soft skill is required'

        technical_skills = request.form.getlist('technical_skills[]')
        if not technical_skills:
            errors['technical_skills'] = 'At least one technical skill is required'

        experience = request.form.get('experience', '')
        try:
            min_exp, max_exp = map(int, experience.split('-'))
            if min_exp >= max_exp:
                errors['experience'] = 'Invalid experience range'
        except ValueError:
            errors['experience'] = 'Invalid experience format'

        try:
            salary_min = float(request.form.get('salary_min', 0))
            salary_max = float(request.form.get('salary_max', 0))
            if salary_min >= salary_max:
                errors['salary'] = 'Invalid salary range'
        except ValueError:
            errors['salary'] = 'Invalid salary values'

        location = request.form.get('location', '').strip()
        if not location:
            errors['location'] = 'Job location is required'

        job_type = request.form.get('job_type')
        if not job_type:
            errors['job_type'] = 'Job type is required'

        experience_level = request.form.get('experience_level')
        if not experience_level:
            errors['experience_level'] = 'Experience level is required'

        education = request.form.get('education', '').strip()
        if not education:
            errors['education'] = 'Education requirement is required'

        try:
            application_deadline = datetime.strptime(request.form.get('application_deadline', ''), '%Y-%m-%d')
            if application_deadline <= datetime.now():
                errors['application_deadline'] = 'Application deadline must be a future date'
        except ValueError:
            errors['application_deadline'] = 'Invalid application deadline'

        if errors:
            for field, message in errors.items():
                flash(f'{field.capitalize()}: {message}', 'error')
            return render_template('recruiter/post_job.html', job_types=job_types, experience_levels=experience_levels)

        # Prepare job data
        job_data = {
            'title': title,
            'description': description,
            'responsibilities': responsibilities,
            'requirements': requirements,
            'recruitment_procedure': recruitment_procedure,
            'soft_skills': soft_skills,
            'technical_skills': technical_skills,
            'experience': experience,
            'salary_min': salary_min,
            'salary_max': salary_max,
            'location': location,
            'job_type': str(job_type),  # Convert ObjectId to string
            'experience_level': str(experience_level),  # Convert ObjectId to string
            'education': education,
            'application_deadline': application_deadline.isoformat(),  # Convert datetime to ISO format string
            'recruiter_id': str(current_user.id),  # Convert ObjectId to string
            'created_at': datetime.utcnow().isoformat(),  # Convert datetime to ISO format string
            'shortlist_notifications_sent': False
        }

        # Store serialized job data in session
        session['pending_job_data'] = json.dumps(job_data, default=json_util.default)

        # Create Stripe Checkout Session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'usd',
                            'unit_amount': 1000,  # $10.00
                            'product_data': {
                                'name': 'Job Posting',
                            },
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=url_for('recruiter.payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=url_for('recruiter.payment_cancel', _external=True),
            )
            return redirect(checkout_session.url, code=303)
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('recruiter.recruiter_index'))

    # Fetch existing skills from collection_jobs
    soft_skills = list(set(skill for job in collection_jobs.find() for skill in job.get('soft_skills', [])))
    technical_skills = list(set(skill for job in collection_jobs.find() for skill in job.get('technical_skills', [])))

    return render_template('recruiter/post_job.html', job_types=job_types, experience_levels=experience_levels, soft_skills=soft_skills, technical_skills=technical_skills)

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
    
    # Get filter parameters
    status = request.args.get('status')
    technical_skills = request.args.getlist('technical_skills')
    soft_skills = request.args.getlist('soft_skills')
    experience = request.args.get('experience')
    education = request.args.get('education')

    # Build query
    query = {'job_id': ObjectId(job_id)}
    if status:
        query['status'] = status

    # Fetch applications for this job, using ObjectId
    applications = list(collection_applications.find(query))
    
    # Filter applications based on resume details
    filtered_applications = []
    for app in applications:
        resume = collection_resume.find_one({'user_id': ObjectId(app['user_id'])})
        if resume:
            # Check technical skills (now in skills.technical)
            if technical_skills and not all(skill in resume.get('skills', {}).get('technical', []) for skill in technical_skills):
                continue
                
            # Check soft skills (now in skills.soft)
            if soft_skills and not all(skill in resume.get('skills', {}).get('soft', []) for skill in soft_skills):
                continue
                
            # Calculate total experience from work_experience entries
            total_experience = 0
            if 'work_experience' in resume:
                for exp in resume['work_experience']:
                    try:
                        start_date = datetime.strptime(exp.get('start_date', ''), '%Y-%m')
                        end_date = datetime.strptime(exp.get('end_date', ''), '%Y-%m') if exp.get('end_date') else datetime.now()
                        duration = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                        total_experience += duration / 12  # Convert months to years
                    except (ValueError, TypeError):
                        continue
            
            # Check experience filter
            if experience:
                if experience == '5+':
                    if total_experience < 5:
                        continue
                else:
                    try:
                        min_exp, max_exp = map(int, experience.split('-'))
                        if not (min_exp <= total_experience < max_exp):
                            continue
                    except ValueError:
                        pass
            
            # Check education (highest degree)
            if education and resume.get('education'):
                highest_education = resume['education'][0].get('degree', '') if resume.get('education') else ''
                if not any(edu.lower() in highest_education.lower() for edu in [education]):
                    continue
            
            # Get applicant info from personal_info
            personal_info = resume.get('personal_info', {})
            app['applicant_name'] = personal_info.get('full_name', 'Unknown')
            app['applicant_email'] = personal_info.get('email', 'N/A')
            app['id'] = str(app['_id'])
            app['user_id'] = str(app['user_id'])
            app['applied_at'] = app['applied_at'].strftime('%Y-%m-%d %H:%M:%S') if app.get('applied_at') else 'N/A'
            filtered_applications.append(app)

    for application in filtered_applications:
        interview = collection_interviews.find_one({
            'candidate_id': ObjectId(application['user_id']),
            'job_id': ObjectId(job_id)
        })
        if interview:
            # Add debugging log
            print(f"Found interview for application {application['_id']}: {interview['_id']}")
            application['interview'] = interview
            application['interview']['_id'] = str(interview['_id'])  # Convert ObjectId to string
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html_content = render_template('recruiter/_application_tabs.html', 
                                       applications=filtered_applications, 
                                       job=job,
                                       now=datetime.utcnow())
        response = make_response(html_content)
        response.headers['Content-Type'] = 'text/html'
        return response
    
    now = datetime.utcnow()
    return render_template('recruiter/view_applications.html', 
                           job=job, 
                           applications=filtered_applications, 
                           technical_skills=job.get('technical_skills', []),
                           soft_skills=job.get('soft_skills', []),
                           education_levels=['High School', 'Bachelor', 'Master', 'PhD'],
                           now=now)

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
    
    # Fetch job types and experience levels
    job_types = {str(jt['_id']): jt['type'] for jt in collection_job_types.find()}
    experience_levels = {str(el['_id']): el['type'] for el in collection_experience_levels.find()}
    
    # Update jobs with job type and experience level information
    for job in jobs:
        job['job_type'] = job_types.get(str(job['job_type']), 'Unknown')
        job['experience_level'] = experience_levels.get(str(job['experience_level']), 'Unknown')
    
    return render_template('recruiter/posted_jobs.html', jobs=jobs, company_name=company_name)

# path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
# config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)

# @recruiter_bp.route('/view_applicant_resume/<applicant_id>')
# @login_required
# def view_applicant_resume(applicant_id):
#     # Check if the current user is a recruiter
#     if current_user.user_type != 'recruiter':
#         flash('Access denied. Recruiter privileges required.', 'error')
#         return redirect(url_for('index'))

#     # Retrieve resume document for the applicant
#     resume_document = collection_resume.find_one({"user_id": ObjectId(applicant_id)})

#     if not resume_document:
#         flash('No resume found for the applicant.', 'danger')
#         return redirect(url_for('recruiter.posted_jobs'))

#     # Render the HTML template for the resume
#     html = render_template('recruiter/view_applicant_resume.html', resume=resume_document)
    
#     try:
#         # Generate PDF from the HTML content
#         pdf = pdfkit.from_string(html, False, configuration=config)
#     except Exception as e:
#         flash(f'An error occurred while generating the PDF: {e}', 'danger')
#         return redirect(url_for('recruiter.posted_jobs'))

#     # Prepare the response
#     response = make_response(pdf)
#     response.headers['Content-Type'] = 'application/pdf'
#     response.headers['Content-Disposition'] = 'inline; filename=applicant_resume.pdf'

#     return response

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

    # Fetch job types and experience levels from the database
    job_types = list(collection_job_types.find())
    experience_levels = list(collection_experience_levels.find())

    if request.method == 'POST':
        print("POST request received")
        errors = {}

        # Validate all fields (similar to post_job route)
        title = request.form.get('title', '').strip()
        if not title:
            errors['title'] = 'Job title is required'

        description = request.form.get('description', '').strip()
        if not description:
            errors['description'] = 'Job description is required'

        responsibilities = json.loads(request.form.get('responsibilities', '[]'))
        if not responsibilities:
            errors['responsibilities'] = 'Job responsibilities are required'

        requirements = json.loads(request.form.get('requirements', '[]'))
        if not requirements:
            errors['requirements'] = 'Job requirements are required'

        recruitment_procedure = json.loads(request.form.get('recruitment_procedure', '[]'))
        if not recruitment_procedure:
            errors['recruitment_procedure'] = 'Recruitment procedure is required'

        skills = request.form.getlist('soft_skills[]')
        if not skills:
            errors['skills'] = 'At least one soft skill is required'

        technical_skills = request.form.getlist('technical_skills[]')
        if not technical_skills:
            errors['technical_skills'] = 'At least one technical skill is required'

        experience = request.form.get('experience', '')
        try:
            min_exp, max_exp = map(int, experience.split('-'))
            if min_exp >= max_exp:
                errors['experience'] = 'Invalid experience range'
        except ValueError:
            errors['experience'] = 'Invalid experience format'

        try:
            salary_min = float(request.form.get('salary_min', 0))
            salary_max = float(request.form.get('salary_max', 0))
            if salary_min >= salary_max:
                errors['salary'] = 'Invalid salary range'
        except ValueError:
            errors['salary'] = 'Invalid salary values'

        location = request.form.get('location', '').strip()
        if not location:
            errors['location'] = 'Job location is required'

        job_type = request.form.get('job_type')
        if not job_type:
            errors['job_type'] = 'Job type is required'

        experience_level = request.form.get('experience_level')
        if not experience_level:
            errors['experience_level'] = 'Experience level is required'

        education = request.form.get('education', '').strip()
        if not education:
            errors['education'] = 'Education requirement is required'

        try:
            application_deadline = datetime.strptime(request.form.get('application_deadline', ''), '%Y-%m-%d')
            if application_deadline <= datetime.now():
                errors['application_deadline'] = 'Application deadline must be a future date'
        except ValueError:
            errors['application_deadline'] = 'Invalid application deadline'

        if errors:
            for field, message in errors.items():
                flash(f'{field.capitalize()}: {message}', 'error')
            print("Validation errors:", errors)
            return render_template('recruiter/edit_job.html', job=job, job_types=job_types, experience_levels=experience_levels)

        try:
            updated_job = {
                'title': title,
                'description': description,
                'responsibilities': responsibilities,
                'requirements': requirements,
                'recruitment_procedure': recruitment_procedure,
                'soft_skills': skills,
                'technical_skills': technical_skills,
                'experience': experience,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'location': location,
                'job_type': ObjectId(job_type),
                'experience_level': ObjectId(experience_level),
                'education': education,
                'application_deadline': application_deadline,
                'updated_at': datetime.utcnow()
            }
            result = collection_jobs.update_one({'_id': ObjectId(job_id)}, {'$set': updated_job})
            print("Update result:", result.modified_count)
            if result.modified_count > 0:
                flash('Job updated successfully!', 'success')
                return redirect(url_for('recruiter.posted_jobs'))
            else:
                flash('No changes were made to the job.', 'info')
        except Exception as e:
            print("Error updating job:", str(e))
            flash('An error occurred while updating the job.', 'error')

    # Ensure recruitment_procedure exists in the job object
    if 'recruitment_procedure' not in job:
        job['recruitment_procedure'] = []

    soft_skills = list(set(skill for job in collection_jobs.find() for skill in job.get('soft_skills', [])))
    technical_skills = list(set(skill for job in collection_jobs.find() for skill in job.get('technical_skills', [])))

    return render_template('recruiter/edit_job.html', 
                           job=job,
                           job_types=job_types, 
                           experience_levels=experience_levels,
                           soft_skills=soft_skills,
                           technical_skills=technical_skills)

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
        'skills': job['soft_skills'],
        'technical_skills': job['technical_skills'],
        'experience': job['experience'],
        'salary_min': job['salary_min'],
        'salary_max': job['salary_max'],
        'location': job['location'],
        'job_type': job['job_type'],
        'experience_level': job['experience_level'],
        'education': job['education'],
        'application_deadline': job['application_deadline'].strftime('%Y-%m-%d')
    }
    return jsonify(job_data)

@recruiter_bp.route('/search_jobs')
@login_required
def search_jobs():
    if current_user.user_type != 'recruiter':
        current_app.logger.error("Access denied: User is not a recruiter")
        return jsonify({'error': 'Access denied'}), 403

    query = request.args.get('query', '').strip()
    if not query:
        current_app.logger.error("No search query provided")
        return jsonify({'error': 'No search query provided'}), 400

    try:
        # Fetch job types and experience levels
        job_types = {str(jt['_id']): jt['type'] for jt in collection_job_types.find()}
        experience_levels = {str(el['_id']): el['type'] for el in collection_experience_levels.find()}

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
                'job_type': job_types.get(str(job['job_type']), 'Unknown'),
                'salary_min': job['salary_min'],
                'salary_max': job['salary_max'],
                'experience_level': experience_levels.get(str(job['experience_level']), 'Unknown'),
                'created_at': job['created_at'].strftime('%Y-%m-%d')
            })

        current_app.logger.info(f"Search query '{query}' returned {len(results)} results")
        return jsonify(results)
    except Exception as e:
        current_app.logger.error(f"Error in search_jobs: {str(e)}")
        return jsonify({'error': 'An error occurred during the search'}), 500

@recruiter_bp.route('/toggle_shortlist/<application_id>', methods=['POST'])
@login_required
def toggle_shortlist(application_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    job_id = request.form.get('job_id')
    if not job_id:
        return jsonify({'success': False, 'message': 'Job ID is required'}), 400

    # Verify that the job belongs to the current recruiter
    job = collection_jobs.find_one({'_id': ObjectId(job_id), 'recruiter_id': ObjectId(current_user.id)})
    if not job:
        return jsonify({'success': False, 'message': 'Job not found or access denied'}), 404

    # Find the application
    application = collection_applications.find_one({'_id': ObjectId(application_id), 'job_id': ObjectId(job_id)})
    if not application:
        return jsonify({'success': False, 'message': 'Application not found'}), 404

    # Toggle the shortlist status
    new_status = 'shortlisted' if application.get('status') != 'shortlisted' else 'applied'
    result = collection_applications.update_one(
        {'_id': ObjectId(application_id)},
        {'$set': {'status': new_status}}
    )

    if result.modified_count > 0:
        return jsonify({'success': True, 'shortlisted': new_status == 'shortlisted'})
    else:
        return jsonify({'success': False, 'message': 'Failed to update application status'}), 500

@recruiter_bp.route('/view_applicant_profile/<applicant_id>')
@login_required
def view_applicant_profile(applicant_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'error': 'Access denied. Recruiter privileges required.'}), 403

    try:
        applicant = collection_resume.find_one({'user_id': ObjectId(applicant_id)})
    except:
        return jsonify({'error': 'Invalid applicant ID.'}), 400

    if not applicant:
        return jsonify({'error': 'Applicant not found.'}), 404

    # Prepare applicant data for JSON response
    applicant_data = {
        'full_name': applicant.get('full_name'),
        'email': applicant.get('email'),
        'phone': applicant.get('phone'),
        'linkedin': applicant.get('linkedin'),
        'address': applicant.get('address'),
        'education': applicant.get('education', []),
        'work_experience': applicant.get('experience', []),
        'soft_skills': applicant.get('soft_skills', []),
        'technical_skills': applicant.get('technical_skills', [])
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If it's an AJAX request, return JSON
        return jsonify(applicant_data)
    else:
        # If it's a regular request, render the template
        return render_template('recruiter/view_applicant_profile.html', applicant=applicant_data, resume=applicant)

def send_shortlist_notifications():
    current_time = datetime.utcnow()
    current_app.logger.info(f"Starting shortlist notifications process at {current_time}")
    
    jobs_to_notify = collection_jobs.find({
        'application_deadline': {'$lte': current_time},
        'shortlist_notifications_sent': {'$ne': True}
    })
    
    jobs_count = 0
    for job in jobs_to_notify:
        jobs_count += 1
        current_app.logger.info(f"Processing job: {job['_id']} - {job['title']}")
        
        shortlisted_applications = collection_applications.find({
            'job_id': job['_id'],
            'status': 'shortlisted'
        })
        
        shortlisted_count = collection_applications.count_documents({
            'job_id': job['_id'],
            'status': 'shortlisted'
        })
        current_app.logger.info(f"Found {shortlisted_count} shortlisted applications for job {job['_id']}")
        
        notifications_sent = 0
        for application in shortlisted_applications:
            try:
                recruiter = collection_recruiter_registration.find_one({'user_id': job['recruiter_id']})
                company_name = recruiter.get('company_name', 'Unknown Company') if recruiter else 'Unknown Company'
                
                notification = {
                    'user_id': application['user_id'],
                    'job_id': job['_id'],
                    'message': f"You have been shortlisted for {job['title']} by {company_name}",
                    'created_at': current_time,
                    'is_read': False
                }
                result = collection_notifications.insert_one(notification)
                if result.inserted_id:
                    notifications_sent += 1
                    current_app.logger.info(f"Notification sent for application {application['_id']}")
                else:
                    current_app.logger.error(f"Failed to insert notification for application {application['_id']}")
            except Exception as e:
                current_app.logger.error(f"Error processing application {application['_id']}: {str(e)}")
        
        current_app.logger.info(f"Sent {notifications_sent} notifications for job {job['_id']}")
        
        try:
            update_result = collection_jobs.update_one(
                {'_id': job['_id']},
                {'$set': {'shortlist_notifications_sent': True}}
            )
            if update_result.modified_count == 0:
                current_app.logger.warning(f"Failed to update shortlist_notifications_sent for job {job['_id']}")
        except Exception as e:
            current_app.logger.error(f"Error updating job {job['_id']}: {str(e)}")
    
    current_app.logger.info(f"Shortlist notifications process completed. Processed {jobs_count} jobs.")
    return jobs_count

@recruiter_bp.route('/test_shortlist_notifications')
@login_required
def test_shortlist_notifications():
    if current_user.user_type != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    # Test notification insertion
    test_notification = {
        'user_id': ObjectId(current_user.id),
        'job_id': ObjectId(),
        'message': "Test notification",
        'created_at': datetime.utcnow(),
        'is_read': False
    }
    result = collection_notifications.insert_one(test_notification)
    if result.inserted_id:
        current_app.logger.info(f"Test notification inserted: {result.inserted_id}")
    else:
        current_app.logger.error("Failed to insert test notification")

    send_shortlist_notifications()
    return jsonify({'message': 'Test run completed. Check logs and database for results.'})

@recruiter_bp.route('/payment/success')
def payment_success():
    session_id = request.args.get('session_id')
    if session_id:
        # Update the payment status in the database
        payment = collection_payment.insert_one({
            'user_id': current_user.id,
            'amount': 10.00,  # Adjust if your price changes
            'context': 'job_posting',
            'date': datetime.utcnow(),
            'session_id': session_id,
            'status': 'completed'
        })
        
        if payment.inserted_id:
            # Retrieve job data from session
            job_data_str = session.pop('pending_job_data', None)
            
            if job_data_str:
                # Deserialize job data
                job_data = json.loads(job_data_str, object_hook=json_util.object_hook)
                
                # Convert string IDs back to ObjectId
                job_data['job_type'] = ObjectId(job_data['job_type'])
                job_data['experience_level'] = ObjectId(job_data['experience_level'])
                job_data['recruiter_id'] = ObjectId(job_data['recruiter_id'])
                
                # Convert ISO format strings back to datetime objects
                job_data['application_deadline'] = datetime.fromisoformat(job_data['application_deadline'])
                job_data['created_at'] = datetime.fromisoformat(job_data['created_at'])
                
                # Insert job data into the database
                job_id = collection_jobs.insert_one(job_data).inserted_id
                
                # Redirect to payment_success.html instead of posted_jobs
                return render_template('recruiter/payment_success.html')
            else:
                flash('Error: Job data not found. Please try posting the job again.', 'error')
        else:
            flash('Error: Payment not completed. Please try again.', 'error')
    else:
        flash('Error: Invalid payment session. Please try again.', 'error')
    
    return redirect(url_for('recruiter.recruiter_index'))

@recruiter_bp.route('/payment/cancel')
def payment_cancel():
    flash('Payment cancelled. Your job has not been posted.', 'warning')
    return redirect(url_for('recruiter.recruiter_index'))

@recruiter_bp.route('/video_interview/<job_id>', methods=['GET'])
@login_required
def video_interview(job_id):
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    print(job_id)
    interview = db.tbl_interviews.find_one({'job_id': ObjectId(job_id)})
    if not interview:
        flash('Interview not found', 'error')
        return redirect(url_for('recruiter.recruiter_index'))

    job = db.tbl_jobs.find_one({'_id': interview['job_id']})

    # Get existing notes, if any
    existing_notes = interview.get('recruiter_notes', '')

    return render_template('recruiter/video_interview.html', 
                           interview=interview, 
                           job=job, 
                           room_name=interview['room_name'],
                           existing_notes=existing_notes)

@recruiter_bp.route('/save-interview-notes', methods=['POST'])
@login_required
def save_interview_notes():
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    data = request.json
    interview_id = data.get('interviewId')
    notes = data.get('notes')

    if not interview_id:
        return jsonify({'success': False, 'message': 'Interview ID is required'}), 400

    try:
        # Find the interview document by _id
        interview = db.tbl_interviews.find_one({'_id': ObjectId(interview_id)})

        if interview:
            # Update the document with the recruiter's notes
            result = db.tbl_interviews.update_one(
                {'_id': ObjectId(interview_id)},
                {'$set': {'recruiter_notes': notes}}
            )

            if result.modified_count > 0:
                return jsonify({'success': True, 'message': 'Notes saved successfully'}), 200
            else:
                return jsonify({'success': False, 'message': 'No changes made'}), 400
        else:
            return jsonify({'success': False, 'message': 'Interview not found'}), 404

    except Exception as e:
        current_app.logger.error(f"Error in save_interview_notes: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while saving notes'}), 500

@recruiter_bp.route('/schedule_interview', methods=['GET', 'POST'])
@login_required
def schedule_interview():
    if request.method == 'GET':
        job_id = request.args.get('job_id')  # Get job_id from query parameters
        default_candidate_name = request.args.get('candidate_name')
        
        # Fetch the job details using job_id
        job = collection_jobs.find_one({'_id': ObjectId(job_id)})
        # Fetch shortlisted candidates from collection_applications
        shortlisted_candidates = collection_applications.find({'job_id': ObjectId(job_id), 'status': 'shortlisted'})
        candidates = []
        for candidate in shortlisted_candidates:
            # Use user_id to find the full_name in collection_resume
            user_id = candidate['user_id']
            resume = collection_resume.find_one({'user_id': ObjectId(user_id)})
            # Get full_name from personal_info object
            full_name = resume.get('personal_info', {}).get('full_name', 'Unknown') if resume else 'Unknown'
            candidates.append({'id': str(candidate['_id']), 'name': full_name})
        return render_template('recruiter/schedule_interview.html', candidates=candidates, job=job, default_candidate_name=default_candidate_name)

    # Handle POST request to schedule the interview
    data = request.json
    recruiter_id = current_user.id
    recruiter = collection_recruiter_registration.find_one({'user_id': ObjectId(recruiter_id)})
    candidate_id = data.get('candidate_id') 
    interview_time = data.get('interview_time')
    room_name = data.get('room_name')
    interview_duration = data.get('interview_duration')

    if not candidate_id or not interview_time or not room_name or not interview_duration:
        return jsonify({'error': 'All fields are required'}), 400

    # Validate interview duration
    try:
        interview_duration = int(interview_duration)
        if interview_duration < 15 or interview_duration > 180:
            return jsonify({'error': 'Interview duration must be between 15 and 180 minutes'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid duration value'}), 400

    application = collection_applications.find_one({'_id': ObjectId(candidate_id)})
    if not application:
        return jsonify({'error': 'Candidate not found'}), 404

    resume = collection_resume.find_one({'user_id': ObjectId(application['user_id'])})
    
    interview = {
        'recruiter_id': recruiter['user_id'],
        'candidate_id': resume['user_id'],
        'job_id': application['job_id'],
        'interview_time': datetime.strptime(interview_time, '%Y-%m-%dT%H:%M'),
        'room_name': room_name,
        'interview_duration': interview_duration,
        'created_at': datetime.utcnow()
    }

    interview_result = collection_interviews.insert_one(interview)

    if interview_result.inserted_id:
        update_result = collection_applications.update_one(
            {'_id': ObjectId(candidate_id)},
            {'$set': {'status': 'meeting scheduled'}}
        )
        
        job = collection_jobs.find_one({'_id': application['job_id']})
        notification = {
            'user_id': resume['user_id'],
            'job_id': application['job_id'],
            'message': f"An interview has been scheduled for the position of {job['title']} on {interview_time}. The interview will last for {interview_duration} minutes.",
            'created_at': datetime.utcnow(),
            'is_read': False
        }
        collection_notifications.insert_one(notification)

        if update_result.modified_count > 0:
            flash('Interview scheduled successfully, application status updated, and candidate notified', 'success')
        else:
            flash('Interview scheduled successfully and candidate notified, but failed to update application status', 'warning')
        
        return jsonify({
            'success': True,
            'redirect': url_for('recruiter.view_applications', job_id=str(application['job_id']))
        }), 201
    else:
        flash('Failed to schedule interview', 'error')
        return jsonify({
            'success': False,
            'redirect': url_for('recruiter.view_applications', job_id=str(application['job_id']))
        }), 500

@recruiter_bp.route('/edit_interview/<interview_id>', methods=['GET', 'POST'])
@login_required
def edit_interview(interview_id):
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))

    if request.method == 'GET':
        existing_interview = collection_interviews.find_one({'_id': ObjectId(interview_id)})
        if not existing_interview:
            flash('Interview not found', 'error')
            return redirect(url_for('recruiter.view_applications'))

        existing_interview['_id'] = str(existing_interview['_id'])
        existing_interview['recruiter_id'] = str(existing_interview['recruiter_id'])
        existing_interview['candidate_id'] = str(existing_interview['candidate_id'])
        existing_interview['job_id'] = str(existing_interview['job_id'])
        
        if isinstance(existing_interview['interview_time'], str):
            existing_interview['interview_time'] = existing_interview['interview_time']
        else:
            existing_interview['interview_time'] = existing_interview['interview_time'].strftime('%Y-%m-%dT%H:%M')

        candidate = collection_resume.find_one({'user_id': ObjectId(existing_interview['candidate_id'])})
        existing_interview['candidate_name'] = candidate['full_name'] if candidate else 'Unknown'
        return render_template('recruiter/edit_interview.html', 
                               existing_interview=existing_interview,
                               job=collection_jobs.find_one({'_id': ObjectId(existing_interview['job_id'])}))

    # Handle POST request to update the interview
    data = request.json
    new_interview_time = data.get('interview_time')
    new_room_name = data.get('room_name')
    new_duration = data.get('interview_duration')
    
    if not new_interview_time or not new_room_name or not new_duration:
        return jsonify({'error': 'All fields are required'}), 400

    try:
        new_duration = int(new_duration)
        if new_duration < 15 or new_duration > 180:
            return jsonify({'error': 'Interview duration must be between 15 and 180 minutes'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid duration value'}), 400

    existing_interview = collection_interviews.find_one({'_id': ObjectId(interview_id)})
    if not existing_interview:
        return jsonify({'error': 'Interview not found'}), 404

    time_changed = existing_interview['interview_time'] != datetime.strptime(new_interview_time, '%Y-%m-%dT%H:%M')

    update_result = collection_interviews.update_one(
        {'_id': ObjectId(interview_id)},
        {'$set': {
            'interview_time': datetime.strptime(new_interview_time, '%Y-%m-%dT%H:%M'),
            'room_name': new_room_name,
            'interview_duration': new_duration,
            'updated_at': datetime.utcnow()
        }}
    )

    if update_result.modified_count > 0:
        job = collection_jobs.find_one({'_id': existing_interview['job_id']})
        
        if time_changed:
            notification = {
                'user_id': existing_interview['candidate_id'],
                'job_id': existing_interview['job_id'],
                'message': f"Your interview for the position of {job['title']} has been rescheduled to {new_interview_time}. The interview will last for {new_duration} minutes.",
                'created_at': datetime.utcnow(),
                'is_read': False
            }
            collection_notifications.insert_one(notification)
            return jsonify({'message': 'Interview updated successfully and candidate notified of time change'}), 200
        else:
            return jsonify({'message': 'Interview updated successfully.'}), 200
    else:
        return jsonify({'error': 'Failed to update interview or no changes were made'}), 500

@recruiter_bp.route('/get_schedules', methods=['GET'])
@login_required
def get_schedules():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Date parameter is required'}), 400

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d')
        start_of_day = selected_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        recruiter_id = current_user.id
        schedules = collection_interviews.find({
            'recruiter_id': ObjectId(recruiter_id),
            'interview_time': {'$gte': start_of_day, '$lt': end_of_day}
        })

        schedules_list = []
        for schedule in schedules:
            start_time = schedule['interview_time']
            end_time = start_time + timedelta(minutes=schedule['interview_duration'])
            schedules_list.append({
                'time_range': f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}",
                'room_name': schedule['room_name']
            })

        return jsonify({'schedules': schedules_list}), 200
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

@recruiter_bp.route('/get-interview-notes/<interview_id>')
@login_required
def get_interview_notes(interview_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        interview = collection_interviews.find_one({
            '_id': ObjectId(interview_id),
            'recruiter_id': ObjectId(current_user.id)
        })
        
        if interview:
            return jsonify({
                'success': True,
                'notes': interview.get('recruiter_notes', 'No notes available.')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Interview not found or access denied'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error fetching interview notes: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching notes'
        }), 500

@recruiter_bp.route('/hire_candidate/<application_id>', methods=['POST'])
@login_required
def hire_candidate(application_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403

    job_id = request.form.get('job_id')
    if not job_id:
        return jsonify({'success': False, 'message': 'Job ID is required'}), 400

    # Verify that the job belongs to the current recruiter
    job = collection_jobs.find_one({
        '_id': ObjectId(job_id), 
        'recruiter_id': ObjectId(current_user.id)
    })
    if not job:
        return jsonify({'success': False, 'message': 'Job not found or access denied'}), 404

    # Find the application
    application = collection_applications.find_one({
        '_id': ObjectId(application_id), 
        'job_id': ObjectId(job_id)
    })
    if not application:
        return jsonify({'success': False, 'message': 'Application not found'}), 404

    # Update the application status to hired
    result = collection_applications.update_one(
        {'_id': ObjectId(application_id)},
        {'$set': {'status': 'hired'}}
    )

    if result.modified_count > 0:
        # Create notification for the candidate
        notification = {
            'user_id': application['user_id'],
            'job_id': ObjectId(job_id),
            'message': f"Congratulations! You have been hired for the position of {job['title']}.",
            'created_at': datetime.utcnow(),
            'is_read': False
        }
        collection_notifications.insert_one(notification)
        
        return jsonify({
            'success': True, 
            'message': 'Candidate hired successfully'
        })
    else:
        return jsonify({
            'success': False, 
            'message': 'Failed to update application status'
        }), 500

@recruiter_bp.route('/network', methods=['GET'])
@login_required
def network():
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get search parameters
    skills = request.args.get('skills', '')
    experience = request.args.get('experience', '')
    location = request.args.get('location', '')
    
    # Build query for job seekers
    query = {}
    if skills:
        skill_list = [skill.strip() for skill in skills.split(',')]
        skill_conditions = []
        for skill in skill_list:
            skill_conditions.append({'skills.technical': {'$regex': skill, '$options': 'i'}})
            skill_conditions.append({'skills.soft': {'$regex': skill, '$options': 'i'}})
        query['$or'] = skill_conditions
    
    if experience:
        # Note: You might need to add a total_experience field to your schema
        # or calculate it based on work_experience dates
        if experience == '5+':
            query['total_experience'] = {'$gte': 5}
        else:
            min_exp, max_exp = map(int, experience.split('-'))
            query['total_experience'] = {'$gte': min_exp, '$lt': max_exp}
    
    if location:
        query['personal_info.address'] = {'$regex': location, '$options': 'i'}
    
    # Fetch job seekers from resume collection and process them
    seekers_cursor = collection_resume.find(query)
    seekers = []
    
    for seeker in seekers_cursor:
        # Check if seeker is already in recruiter's pool
        in_pool = collection_talent_pool.find_one({
            'recruiter_id': ObjectId(current_user.id),
            'seeker_id': seeker['_id']
        }) is not None
        
        personal_info = seeker.get('personal_info', {})
        skills = seeker.get('skills', {})
        
        processed_seeker = {
            '_id': seeker.get('_id'),
            'full_name': personal_info.get('full_name', 'Anonymous'),
            'profile_photo': seeker.get('profile_photo'),
            'headline': personal_info.get('position', 'Professional'),
            'location': personal_info.get('address', 'Location not specified'),
            'technical_skills': skills.get('technical', []),
            'soft_skills': skills.get('soft', []),
            'tools': skills.get('tools', []),
            'experience': seeker.get('total_experience', 0),
            'about': seeker.get('professional_summary', 'No description available.')[:150] + '...' 
                    if seeker.get('professional_summary') 
                    else 'No description available.',
            'in_pool': in_pool  # Add this field
        }
        seekers.append(processed_seeker)
    
    return render_template('recruiter/network.html', seekers=seekers)

@recruiter_bp.route('/send-network-request', methods=['POST'])
@login_required
def send_network_request():
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    seeker_id = data.get('seeker_id')
    
    if not seeker_id:
        return jsonify({'success': False, 'message': 'Seeker ID is required'}), 400
    
    try:
        # Create network request
        network_request = {
            'recruiter_id': ObjectId(current_user.id),
            'seeker_id': ObjectId(seeker_id),
            'status': 'pending',
            'created_at': datetime.utcnow()
        }
        
        # Check if network request already exists
        existing_request = collection_connections.find_one({
            'recruiter_id': ObjectId(current_user.id),
            'seeker_id': ObjectId(seeker_id)
        })
        
        if existing_request:
            return jsonify({'success': False, 'message': 'Network request already sent'}), 400
        
        # Insert network request
        result = collection_connections.insert_one(network_request)
        
        if result.inserted_id:
            # Create notification for the seeker
            recruiter = collection_recruiter_registration.find_one({'user_id': ObjectId(current_user.id)})
            company_name = recruiter.get('company_name', 'A recruiter') if recruiter else 'A recruiter'
            
            notification = {
                'user_id': ObjectId(seeker_id),
                'type': 'network_request',
                'message': f"{company_name} wants to add you to their network",
                'created_at': datetime.utcnow(),
                'is_read': False
            }
            collection_notifications.insert_one(notification)
            
            return jsonify({'success': True, 'message': 'Network request sent successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to send network request'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in send_network_request: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while sending the request'}), 500

@recruiter_bp.route('/add-to-pool', methods=['POST'])
@login_required
def add_to_pool():
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    seeker_id = data.get('seeker_id')
    
    if not seeker_id:
        return jsonify({'success': False, 'message': 'Seeker ID is required'}), 400
    
    try:
        # Check if already in pool
        existing_entry = collection_talent_pool.find_one({
            'recruiter_id': ObjectId(current_user.id),
            'seeker_id': ObjectId(seeker_id)
        })
        
        if existing_entry:
            return jsonify({'success': False, 'message': 'Already in talent pool'}), 400
        
        # Add to talent pool
        pool_entry = {
            'recruiter_id': ObjectId(current_user.id),
            'seeker_id': ObjectId(seeker_id),
            'added_at': datetime.utcnow(),
            'notes': '',  # Optional field for recruiter's private notes
            'status': 'active'  # Could be used for categorizing candidates
        }
        
        result = collection_talent_pool.insert_one(pool_entry)
        
        if result.inserted_id:
            return jsonify({
                'success': True, 
                'message': 'Added to talent pool successfully'
            })
        else:
            return jsonify({
                'success': False, 
                'message': 'Failed to add to talent pool'
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in add_to_pool: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An error occurred while adding to pool'
        }), 500

@recruiter_bp.route('/talent-pool')
@login_required
def view_talent_pool():
    if current_user.user_type != 'recruiter':
        flash('Access denied. Recruiter privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Fetch all candidates in the recruiter's talent pool
    pool_entries = collection_talent_pool.find({
        'recruiter_id': ObjectId(current_user.id)
    }).sort('added_at', -1)  # Most recent first
    
    # Get detailed information for each candidate
    candidates = []
    for entry in pool_entries:
        seeker = collection_resume.find_one({'_id': entry['seeker_id']})
        if seeker:
            personal_info = seeker.get('personal_info', {})
            skills = seeker.get('skills', {})
            
            # Format the date before sending to template
            added_at = entry.get('added_at')
            formatted_date = added_at.strftime('%b %d, %Y') if added_at else 'Unknown date'
            
            candidate = {
                'pool_id': entry['_id'],
                'seeker_id': entry['seeker_id'],  # Add seeker_id for chat functionality
                'added_at_raw': added_at,  # Keep original for sorting
                'added_at': formatted_date,  # Formatted for display
                'notes': entry.get('notes', ''),
                'status': entry.get('status', 'active'),
                'full_name': personal_info.get('full_name', 'Anonymous'),
                'position': personal_info.get('position', 'Professional'),
                'location': personal_info.get('address', 'Location not specified'),
                'technical_skills': skills.get('technical', []),
                'soft_skills': skills.get('soft', []),
                'about': seeker.get('professional_summary', 'No description available.')
            }
            candidates.append(candidate)
    
    return render_template('recruiter/talent_pool.html', candidates=candidates)

@recruiter_bp.route('/update-candidate-notes', methods=['POST'])
@login_required
def update_candidate_notes():
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    notes = data.get('notes', '')
    
    if not candidate_id:
        return jsonify({'success': False, 'message': 'Candidate ID is required'}), 400
    
    try:
        # Verify the candidate belongs to this recruiter
        candidate = collection_talent_pool.find_one({
            '_id': ObjectId(candidate_id),
            'recruiter_id': ObjectId(current_user.id)
        })
        
        if not candidate:
            return jsonify({'success': False, 'message': 'Candidate not found in your pool'}), 404
        
        # Update the notes
        result = collection_talent_pool.update_one(
            {'_id': ObjectId(candidate_id)},
            {'$set': {'notes': notes}}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Notes updated successfully'})
        else:
            return jsonify({'success': True, 'message': 'No changes made'})
            
    except Exception as e:
        current_app.logger.error(f"Error in update_candidate_notes: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while updating notes'}), 500

@recruiter_bp.route('/update-candidate-status', methods=['POST'])
@login_required
def update_candidate_status():
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    status = data.get('status')
    
    valid_statuses = ['active', 'contacted', 'interviewing', 'shortlisted']
    
    if not candidate_id:
        return jsonify({'success': False, 'message': 'Candidate ID is required'}), 400
    
    if not status or status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    
    try:
        # Verify the candidate belongs to this recruiter
        candidate = collection_talent_pool.find_one({
            '_id': ObjectId(candidate_id),
            'recruiter_id': ObjectId(current_user.id)
        })
        
        if not candidate:
            return jsonify({'success': False, 'message': 'Candidate not found in your pool'}), 404
        
        # Update the status
        result = collection_talent_pool.update_one(
            {'_id': ObjectId(candidate_id)},
            {'$set': {'status': status}}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Status updated successfully'})
        else:
            return jsonify({'success': True, 'message': 'No changes made'})
            
    except Exception as e:
        current_app.logger.error(f"Error in update_candidate_status: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while updating status'}), 500

@recruiter_bp.route('/remove-from-pool', methods=['POST'])
@login_required
def remove_from_pool():
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    
    if not candidate_id:
        return jsonify({'success': False, 'message': 'Candidate ID is required'}), 400
    
    try:
        # Verify the candidate belongs to this recruiter
        candidate = collection_talent_pool.find_one({
            '_id': ObjectId(candidate_id),
            'recruiter_id': ObjectId(current_user.id)
        })
        
        if not candidate:
            return jsonify({'success': False, 'message': 'Candidate not found in your pool'}), 404
        
        # Remove from pool
        result = collection_talent_pool.delete_one({
            '_id': ObjectId(candidate_id),
            'recruiter_id': ObjectId(current_user.id)
        })
        
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Candidate removed from pool'})
        else:
            return jsonify({'success': False, 'message': 'Failed to remove candidate'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error in remove_from_pool: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while removing candidate'}), 500

@recruiter_bp.route('/initiate-chat/<seeker_id>', methods=['POST'])
@login_required
def initiate_chat(seeker_id):
    if current_user.user_type != 'recruiter':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        # Debug logging
        current_app.logger.info(f"Initiating chat with seeker ID: {seeker_id}")
        
        # Check if seeker exists
        seeker = collection_resume.find_one({'_id': ObjectId(seeker_id)})
        if not seeker:
            current_app.logger.error(f"Seeker not found with ID: {seeker_id}")
            return jsonify({'success': False, 'message': 'Candidate not found'}), 404
        
        # Get seeker's user ID
        seeker_user_id = seeker.get('user_id')
        if not seeker_user_id:
            current_app.logger.error(f"No user_id found for seeker: {seeker_id}")
            return jsonify({'success': False, 'message': 'Cannot identify candidate user account'}), 400
        
        current_app.logger.info(f"Found seeker user_id: {seeker_user_id}")
        
        # Get recruiter information
        recruiter_info = collection_recruiter_registration.find_one({'user_id': ObjectId(current_user.id)})
        recruiter_name = recruiter_info.get('company_name', 'Recruiter') if recruiter_info else 'Recruiter'
        
        # Check if a conversation already exists
        existing_conversation = collection_conversations.find_one({
            '$or': [
                {'user1_id': ObjectId(current_user.id), 'user2_id': ObjectId(seeker_user_id)},
                {'user1_id': ObjectId(seeker_user_id), 'user2_id': ObjectId(current_user.id)}
            ]
        })
        
        if existing_conversation:
            conversation_id = existing_conversation['_id']
            current_app.logger.info(f"Found existing conversation: {conversation_id}")
        else:
            # Create a new conversation
            conversation_data = {
                'user1_id': ObjectId(current_user.id),
                'user2_id': ObjectId(seeker_user_id),
                'created_at': datetime.now(),
                'last_message_at': datetime.now(),
                'unread_count_user1': 0,
                'unread_count_user2': 0
            }
            
            current_app.logger.info(f"Creating new conversation with data: {conversation_data}")
            
            conversation_result = collection_conversations.insert_one(conversation_data)
            conversation_id = conversation_result.inserted_id
            
            # Create a notification for the seeker
            notification_data = {
                'user_id': ObjectId(seeker_user_id),
                'type': 'chat',
                'message': f'Recruiter {recruiter_name} has started a conversation with you',
                'is_read': False,
                'created_at': datetime.now()
            }
            
            current_app.logger.info(f"Creating notification with data: {notification_data}")
            collection_notifications.insert_one(notification_data)
        
        # Check if messages blueprint exists and has the view_conversation endpoint
        if 'messages.view_conversation' in current_app.view_functions:
            redirect_url = url_for('messages.view_conversation', conversation_id=str(conversation_id))
        else:
            # Fallback to a generic messages URL
            redirect_url = f"/messages/{conversation_id}"
            current_app.logger.warning(f"messages.view_conversation endpoint not found, using fallback URL: {redirect_url}")
        
        return jsonify({
            'success': True, 
            'conversation_id': str(conversation_id),
            'redirect_url': redirect_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in initiate_chat: {str(e)}")
        current_app.logger.error(traceback.format_exc())  # Log the full traceback
        return jsonify({'success': False, 'message': f'An error occurred while initiating chat: {str(e)}'}), 500