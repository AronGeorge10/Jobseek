from flask import Flask, request, render_template, redirect, url_for, flash, session, make_response, jsonify
from pymongo import MongoClient
import os
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from bson.objectid import ObjectId
import jwt
from datetime import datetime, timedelta
import random
import logging

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for flashing messages

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# MongoDB connection URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://AronJain:AronJain@cluster0.qy4jgjm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

bcrypt = Bcrypt(app)
client = MongoClient(MONGO_URI)
db = client.job_portal
collection_user_registration = db.tbl_user_registration
collection_login_credentials = db.tbl_login_credentials

login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Configure Flask-Mail settings (replace placeholders with your actual SMTP server details)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'aronayikon10@gmail.com'
app.config['MAIL_PASSWORD'] = 'gbbn izcn iuxy sdne'
app.config['MAIL_DEFAULT_SENDER'] = 'aronayikon10@gmail.com'
# Initialize Flask-Mail
mail = Mail(app)

class User(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password

    @staticmethod
    def get(user_id):
        user_data = collection_login_credentials.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(str(user_data['_id']), user_data['email'], user_data['password'])
        return None

    @staticmethod
    def get_by_email(email):
        user_data = collection_login_credentials.find_one({'email': email})
        if user_data:
            return User(str(user_data['_id']), user_data['email'], user_data['password'])
        return None

@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.form.get('email')
    user = collection_login_credentials.find_one({'email': email})
    if user:
        return 'exists'
    else:
        return 'not exists'
    
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('fullname')
        user_type = request.form.get('type')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert user registration data
        user_registration = {
            "full_name": full_name,
            "user_type": user_type  # Example user type, adjust as per your schema
        }
        result = collection_user_registration.insert_one(user_registration)
        registration_id = result.inserted_id

        # Insert login credentials with hashed password and reference to registration_id
        user_login_credentials = {
            "email": email,
            "password": hashed_password,
            "registration_id": registration_id
        }
        result = collection_login_credentials.insert_one(user_login_credentials)

        # Send verification email
        send_verification_email(email)

        flash('Registration successful. Please check your email for verification instructions.', 'success')

    return render_template('register.html')

def send_verification_email(email):
    token = generate_verification_token(email)
    verification_url = url_for('verify_email', token=token, _external=True)
    msg = Message('Verify Your Email', recipients=[email])
    msg.body = f'Please click the following link to verify your email: {verification_url}'
    mail.send(msg)

def generate_verification_token(email):
    expiration = datetime.utcnow() + timedelta(hours=24)  # Token valid for 24 hours
    payload = {"email": email, "exp": expiration}
    token = jwt.encode(payload, app.secret_key, algorithm="HS256")
    return token

@app.route('/verify-email/<token>')
def verify_email(token):
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=["HS256"])
        email = payload['email']
        # Perform the email verification logic here, such as updating the user's status in the database
        flash('Email verified successfully.', 'success')
        return redirect(url_for('login'))
    except jwt.ExpiredSignatureError:
        flash('The verification link has expired.', 'error')
        return redirect(url_for('register'))
    except jwt.InvalidTokenError:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('register'))
    
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route("/", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.get_by_email(email)

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route('/index')
@login_required
def index():
    response = make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear the session
    response = make_response(redirect(url_for('login')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Mock function to send email
def send_otp_email(email, otp):
    msg = Message('Password Reset', recipients=[email])
    msg.body = f'Your OTP code is {otp}. Please do not share it with anyone'
    mail.send(msg)

# Endpoint to generate and send OTP
# Endpoint to generate and send OTP
@app.route('/generate_otp', methods=['POST'])
def generate_otp():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400

    otp = random.randint(100000, 999999)
    session['otp'] = str(otp)  # Ensure OTP is stored as a string
    session['email'] = email
    send_otp_email(email, otp)
    logging.debug(f"Generated OTP: {otp} for email: {email}")
    return jsonify({'status': 'success', 'message': 'OTP sent to email'})

# Endpoint to verify OTP
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    logging.debug(f"Received OTP: {otp} for email: {email}")
    logging.debug(f"Session OTP: {session.get('otp')} for email: {session.get('email')}")

    # Check if email and OTP are in session and if they match
    if 'otp' in session and 'email' in session:
        if email == session['email'] and otp == session['otp']:
            logging.debug("OTP verified successfully")
            session.pop('otp', None)
            return jsonify({'status': 'success', 'message': 'OTP verified successfully'})
        else:
            logging.debug("Invalid OTP or email")
            return jsonify({'status': 'error', 'message': 'Invalid OTP or email'}), 400
    else:
        logging.debug("OTP not found or expired")
        return jsonify({'status': 'error', 'message': 'OTP not found or expired'}), 400



@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        # Filter to match the document where email matches session['email']
        filter = {"email": session['email']}

        # Update operation to set the new hashed password
        update = {"$set": {"password": hashed_password}}

        # Perform the update operation
        result = collection_login_credentials.update_one(filter, update)
        
        if result.modified_count > 0:
            flash('Password updated successfully.', 'success')
        else:
            flash('Error updating password.', 'error')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')


if __name__ == '__main__':
    app.run(debug=True)
