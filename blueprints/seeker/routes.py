import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, make_response
from flask_login import current_user, login_required
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import pdfkit
from datetime import datetime

# Use environment variables for sensitive information
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:AronJain@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
client = MongoClient(MONGO_URI)
db = client['job_portal']
collection_resume_details = db.tbl_resume_details
collection_login_credentials = db.tbl_login_credentials
collection_user_registration = db.tbl_user_registration
collection_jobs = db.tbl_jobs

seeker_bp = Blueprint('seeker', __name__)

@seeker_bp.route('/viewprofile', methods=['GET', 'POST'])
@login_required
def viewprofile():
    if request.method == 'POST':
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

        # Add input validation
        if not all([full_name, job_title, email, phone]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('seeker.viewprofile'))

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
            # Update the existing document
            collection_resume_details.update_one(
                {"user_id": ObjectId(current_user.id)},
                {"$set": resume}
            )
        else:
            # Create a new resume document if none exists
            resume["user_id"] = current_user.id
            collection_resume_details.insert_one(resume)

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('seeker.viewprofile'))

    # Find registration_id in tbl_login_credentials
    login_credentials = collection_login_credentials.find_one({"_id": ObjectId(current_user.id)})
    user_id = login_credentials.get('_id')
    
    # Find user details in tbl_user_registration using registration_id
    resume_document = collection_resume_details.find_one({"user_id": ObjectId(user_id)})

    # Pass the current_user, full_name, and resume data to the template
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

def fetch_featured_jobs():
    # Assuming featured jobs have a 'featured' field set to True
    return list(collection_jobs.find({'featured': True}))

@seeker_bp.route('/job_postings', methods=['GET', 'POST'])
@login_required
def job_postings():
    # Fetch regular jobs
    jobs = list(collection_jobs.find())
    
    # Fetch featured jobs
    featured_jobs = fetch_featured_jobs()
    
    return render_template('seeker/job_postings.html', jobs=jobs, featured_jobs=featured_jobs)

@seeker_bp.route('/view_job/<job_id>')
@login_required
def view_job(job_id):
    job = collection_jobs.find_one({'_id': ObjectId(job_id)})
    if job:
        # Check if the user has already applied for this job
        has_applied = db.tbl_job_applications.find_one({
            'user_id': ObjectId(current_user.id),
            'job_id': ObjectId(job_id)
        }) is not None
        
        return render_template('seeker/view_job.html', job=job, has_applied=has_applied)
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