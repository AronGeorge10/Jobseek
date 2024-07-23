from flask import Blueprint, render_template
from flask_login import current_user

profile_bp = Blueprint('viewprofile', __name__)

@profile_bp.route('/viewprofile')
def viewprofile():
    # Your code here
    return render_template('viewprofile.html',user=current_user)

