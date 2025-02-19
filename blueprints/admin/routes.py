from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from pymongo import MongoClient
import os
from bson import ObjectId
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators
from flask_bcrypt import Bcrypt  # Import Bcrypt directly
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

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

# Create a new Bcrypt instance
bcrypt = Bcrypt()

def admin_check():
    if not current_user.is_authenticated or current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    admin_check()
    
    # Fetch statistics for the dashboard
    total_users = collection_login_credentials.count_documents({})
    total_jobs = collection_jobs.count_documents({})
    total_applications = collection_applications.count_documents({})  # Changed this line
    
    return render_template('admin/dashboard.html', 
                           total_users=total_users,
                           total_jobs=total_jobs,
                           total_applications=total_applications)

@admin_bp.route('/job_listings')
@login_required
def job_listings():
    
    admin_check()
    
    # Fetch all job listings from the database
    jobs = list(collection_jobs.find())
    
    # Fetch company names for each job
    for job in jobs:
        recruiter = collection_recruiter_registration.find_one({"user_id": job.get("recruiter_id")})
        if recruiter:
            job["company_name"] = recruiter.get("company_name", "N/A")
        else:
            job["company_name"] = "N/A"
    
    return render_template('admin/job_listings.html', jobs=jobs)

@admin_bp.route('/list_seekers')
@login_required
def list_seekers():
    admin_check()
    
    # Fetch all job seekers from the database
    seekers = list(collection_resume_details.find())
    
    return render_template('admin/list_seekers.html', seekers=seekers)

@admin_bp.route('/view_seeker/<seeker_id>')
@login_required
def view_seeker(seeker_id):
    admin_check()
    seeker = collection_resume_details.find_one({"user_id": ObjectId(seeker_id)})
    if not seeker:
        flash('Seeker not found', 'error')
        return redirect(url_for('admin.list_seekers'))
    
    # Fetch job applications for this seeker
    applications = list(collection_applications.find({"user_id": ObjectId(seeker_id)}))
    
    # Fetch job details for each application
    for app in applications:
        job = collection_jobs.find_one({"_id": app["job_id"]})
        if job:
            app["job_title"] = job.get("title", "N/A")
            
            # Fetch company name from recruiter registration
            recruiter = collection_recruiter_registration.find_one({"user_id": job.get("recruiter_id")})
            if recruiter:
                app["company_name"] = recruiter.get("company_name", "N/A")
            else:
                app["company_name"] = "N/A"
        else:
            app["job_title"] = "Job not found"
            app["company_name"] = "N/A"
        
        # Ensure status is present, set to 'Unknown' if not
        app["status"] = app.get("status", "Unknown")
    
    return render_template('admin/view_seeker.html', seeker=seeker, applications=applications)

@admin_bp.route('/manage_seeker/<seeker_id>', methods=['GET', 'POST'])
@login_required
def manage_seeker(seeker_id):
    admin_check()
    seeker = collection_login_credentials.find_one({"_id": ObjectId(seeker_id)})
    if not seeker:
        flash('Seeker not found', 'error')
        return redirect(url_for('admin.list_seekers'))
    
    if request.method == 'POST':
        # Handle form submission for account management
        action = request.form.get('action')
        if action == 'deactivate':
            collection_login_credentials.update_one(
                {"_id": ObjectId(seeker_id)},
                {"$set": {"is_active": False}}
            )
            flash('Seeker account deactivated', 'success')
        elif action == 'activate':
            collection_login_credentials.update_one(
                {"_id": ObjectId(seeker_id)},
                {"$set": {"is_active": True}}
            )
            flash('Seeker account activated', 'success')
        # Add other management actions as needed
        return redirect(url_for('admin.list_seekers'))
    
    return render_template('admin/manage_seeker.html', seeker=seeker)

@admin_bp.route('/list_recruiters')
@login_required
def list_recruiters():
    admin_check()
    
    # Fetch all recruiters from the recruiter registration collection
    recruiters = list(collection_recruiter_registration.find())
    
    # Fetch corresponding emails from login credentials collection
    for recruiter in recruiters:
        login_info = collection_login_credentials.find_one({"_id": recruiter["user_id"]})
        if login_info:
            recruiter["email"] = login_info.get("email")
        else:
            recruiter["email"] = "N/A"
    
    return render_template('admin/list_recruiters.html', recruiters=recruiters)

@admin_bp.route('/view_recruiter/<recruiter_id>')
@login_required
def view_recruiter(recruiter_id):
    admin_check()
    
    # Fetch recruiter details from recruiter registration collection
    recruiter = collection_recruiter_registration.find_one({"_id": ObjectId(recruiter_id)})
    if not recruiter:
        flash('Recruiter not found', 'error')
        return redirect(url_for('admin.list_recruiters'))
    
    # Fetch additional login details
    login_info = collection_login_credentials.find_one({"_id": recruiter["user_id"]})
    if login_info:
        recruiter.update(login_info)

    # Fetch jobs using user_id
    jobs = list(collection_jobs.find({"recruiter_id": recruiter["user_id"]}))
    
    # Add debug print
    print(f"Found {len(jobs)} jobs for recruiter {recruiter_id}")
    print(f"Recruiter user_id: {recruiter['user_id']}")
    
    # Count applications for each job
    for job in jobs:
        job['application_count'] = collection_applications.count_documents({"job_id": job["_id"]})
        
        # Ensure status is present, set to 'Active' if not
        job["status"] = job.get("status", "Active")
        
        # Convert ObjectId to string for the template
        job["_id"] = str(job["_id"])
        
        # Format the date using created_at instead of posted_date
        if "created_at" in job:
            if isinstance(job["created_at"], str):
                job["created_at"] = job["created_at"]
            else:
                job["created_at"] = job["created_at"].strftime('%Y-%m-%d')
    
    return render_template('admin/view_recruiter.html', recruiter=recruiter, jobs=jobs)

@admin_bp.route('/manage_recruiter/<recruiter_id>', methods=['GET', 'POST'])
@login_required
def manage_recruiter(recruiter_id):
    admin_check()
    recruiter = collection_login_credentials.find_one({"_id": ObjectId(recruiter_id)})
    if not recruiter:
        flash('Recruiter not found', 'error')
        return redirect(url_for('admin.list_recruiters'))
    
    if request.method == 'POST':
        # Handle form submission for account management
        action = request.form.get('action')
        if action == 'deactivate':
            collection_login_credentials.update_one(
                {"_id": ObjectId(recruiter_id)},
                {"$set": {"is_active": False}}
            )
            flash('Recruiter account deactivated', 'success')
        elif action == 'activate':
            collection_login_credentials.update_one(
                {"_id": ObjectId(recruiter_id)},
                {"$set": {"is_active": True}}
            )
            flash('Recruiter account activated', 'success')
        # Add other management actions as needed
        return redirect(url_for('admin.list_recruiters'))
    
    return render_template('admin/manage_recruiter.html', recruiter=recruiter)

@admin_bp.route('/add_industry', methods=['GET', 'POST'])
@login_required
def add_industry():
    admin_check()
    
    if request.method == 'POST':
        industry_name = request.form.get('industry_name')
        if industry_name:
            # Check if the industry already exists
            existing_industry = collection_industries.find_one({"name": industry_name})
            if existing_industry:
                flash('Industry already exists', 'warning')
            else:
                # Add the new industry to the database
                collection_industries.insert_one({"name": industry_name})
                flash('Industry added successfully', 'success')
        else:
            flash('Industry name is required', 'error')
        
        return redirect(url_for('admin.add_industry'))
    
    # Fetch all industries for display
    industries = list(collection_industries.find())
    
    return render_template('admin/add_industry.html', industries=industries)

class CustomerCareRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', [validators.Length(min=4, max=50)])
    email = StringField('Email', [validators.Email()])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.Length(min=6),
        validators.EqualTo('confirm_password', message='Passwords must match')
    ])
    confirm_password = PasswordField('Confirm Password')
    phone = StringField('Phone Number', [validators.Length(min=10, max=15)])

@admin_bp.route('/check-customer-care-email', methods=['POST'])
@login_required
def check_customer_care_email():
    email = request.form.get('email')
    existing_user = collection_login_credentials.find_one({"email": email})
    return jsonify(exists=bool(existing_user))

@admin_bp.route('/register-customer-care', methods=['GET', 'POST'])
@login_required
def register_customer_care():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Debug print
        print(f"Received registration request for email: {email}")
        
        # Server-side validation
        if not email or not password:
            flash('All fields are required', 'error')
            return redirect(url_for('admin.register_customer_care'))
            
        # Check if email already exists
        existing_user = collection_login_credentials.find_one({"email": email})
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('admin.register_customer_care'))
            
        try:
            # Use bcrypt for password hashing
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = {
                'email': email,
                'password': hashed_password,
                'user_type': 'customer_care',
                'created_at': datetime.utcnow(),
                'is_active': True
            }
            
            # Debug print
            print(f"Attempting to insert user: {new_user}")
            
            result = collection_login_credentials.insert_one(new_user)
            
            # Debug print
            print(f"Insert result: {result.inserted_id}")
            
            if result.inserted_id:
                flash('Customer Care user registered successfully!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash('Error registering user: Database insert failed', 'error')
                return redirect(url_for('admin.register_customer_care'))
            
        except Exception as e:
            print(f"Error during registration: {str(e)}")  # Debug print
            flash(f'Error registering user: {str(e)}', 'error')
            return redirect(url_for('admin.register_customer_care'))
    
    return render_template('admin/register_customer_care.html')

# Add more admin routes as needed