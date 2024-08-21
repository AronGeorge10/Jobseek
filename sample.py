import nltk

# Download required NLTK data
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, FileField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_ckeditor import CKEditor
from werkzeug.utils import secure_filename
import os
from flask import jsonify
from pyresparser import ResumeParser

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobseeker.db'
app.config['UPLOAD_FOLDER'] = 'static/resumes'
app.config['CKEDITOR_PKG_TYPE'] = 'standard'
app.config['CKEDITOR_LANGUAGE'] = 'en'
app.config['CKEDITOR_HEIGHT'] = 300
app.config['CKEDITOR_WIDTH'] = 800

db = SQLAlchemy(app)
Bootstrap(app)
ckeditor = CKEditor(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    profile = db.relationship('Profile', backref='user', uselist=False)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    linkedin = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    resume = db.Column(db.String(100), nullable=True)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=20)])
    email = StringField('Email', validators=[InputRequired(), Length(min=4)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
    submit = SubmitField('Sign Up')

class ProfileForm(FlaskForm):
    fullname = StringField('Full Name', validators=[InputRequired(), Length(min=4)])
    job_title = StringField('Job Title', validators=[InputRequired(), Length(min=4)])
    email = StringField('Email', validators=[InputRequired(), Length(min=4)])
    phone = StringField('Phone', validators=[InputRequired(), Length(min=4)])
    address = StringField('Address', validators=[InputRequired(), Length(min=4)])
    linkedin = StringField('LinkedIn', validators=[InputRequired(), Length(min=4)])
    summary = TextAreaField('Summary', validators=[InputRequired()])
    resume = FileField('Resume', validators=[InputRequired()])
    submit = SubmitField('Save')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if user.check_password(form.password.data):
                login_user(user)
                return redirect(url_for('viewprofile'))
            else:
                flash('Invalid password.')
        else:
            flash('Invalid username.')
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/seeker/viewprofile', methods=['GET', 'POST'])
@login_required
def viewprofile():
    form = ProfileForm()
    if form.validate_on_submit():
        if form.resume.data:
            resume_file = form.resume.data
            filename = secure_filename(resume_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(filepath)
            resume_data = ResumeParser(filepath).get_extracted_data()
            os.remove(filepath)
            form.fullname.data = resume_data.get('name', '')
            form.job_title.data = resume_data.get('job_title', '')
            form.email.data = resume_data.get('email', '')
            form.phone.data = resume_data.get('mobile_number', '')
            form.address.data = resume_data.get('address', '')
            form.linkedin.data = resume_data.get('linkedin', '')
            form.summary.data = resume_data.get('summary', '')
        new_profile = Profile(fullname=form.fullname.data, job_title=form.job_title.data, email=form.email.data, phone=form.phone.data, address=form.address.data, linkedin=form.linkedin.data, summary=form.summary.data, user_id=current_user.id)
        db.session.add(new_profile)
        db.session.commit()
        return redirect(url_for('viewprofile'))
    return render_template('seeker/viewprofile.html', form=form)

@app.route('/seeker/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/seeker/extract_resume', methods=['POST'])
def extract_resume():
    if 'resume_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['resume_file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract resume data
        resume_data = ResumeParser(filepath).get_extracted_data()
        
        # Clean up the uploaded file
        os.remove(filepath)
        
        return jsonify({'success': True, 'resume_data': resume_data})
    
    return jsonify({'success': False, 'error': 'Invalid file type'})

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx'}

if __name__ == '__main__':
    app.run(debug=True)
