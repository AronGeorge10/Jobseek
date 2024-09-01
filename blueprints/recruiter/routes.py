from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response, jsonify, session
from flask_login import current_user, login_required
from pymongo import MongoClient
import os
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import current_app
import pdfkit
from bson.errors import InvalidId
import bleach
import json
from apscheduler.schedulers.background import BackgroundScheduler
import stripe
from bson import json_util

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
    
    # Fetch job types and experience levels
    job_types = {str(jt['_id']): jt['type'] for jt in collection_job_types.find()}
    experience_levels = {str(el['_id']): el['type'] for el in collection_experience_levels.find()}
    
    # Update jobs with job type and experience level information
    for job in jobs:
        job['job_type'] = job_types.get(str(job['job_type']), 'Unknown')
        job['experience_level'] = experience_levels.get(str(job['experience_level']), 'Unknown')
    
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
        
        new_status = 'shortlisted' if application['status'] != 'shortlisted' else 'applied'
        result = collection_applications.update_one(
            {'_id': ObjectId(application_id)},
            {'$set': {'status': new_status}}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'new_status': new_status, 'message': 'Status updated successfully'})
        else:
            return jsonify({'success': True, 'new_status': application['status'], 'message': 'No changes were necessary'}), 200
    except Exception as e:
        current_app.logger.error(f"Error in shortlisting application: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        'name': applicant.get('name'),
        'email': applicant.get('email'),
        'phone': applicant.get('phone'),
        'education': applicant.get('education', []),
        'experience': applicant.get('experience', []),
        'skills': applicant.get('skills', [])
    }

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If it's an AJAX request, return JSON
        return jsonify(applicant_data)
    else:
        # If it's a regular request, render the template
        return render_template('recruiter/view_applicant_profile.html', applicant=applicant_data)

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
