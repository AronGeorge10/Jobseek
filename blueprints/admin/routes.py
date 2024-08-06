from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from . import admin_bp

admin_bp = Blueprint('admin', __name__)

# Ensure only admin users can access these routes
# def admin_required(func):
#     @login_required
#     def wrapper(*args, **kwargs):
#         if not current_user.is_admin:
#             flash('You do not have permission to access this page.', 'danger')
#             return redirect(url_for('main.index'))
#         return func(*args, **kwargs)
#     return wrapper

@admin_bp.route('/dashboard')
# @admin_required
def dashboard():
    return render_template('admin/dashboard.html')

# Add more admin routes as needed
