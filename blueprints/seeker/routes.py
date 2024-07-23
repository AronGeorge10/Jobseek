from flask import render_template
from . import seeker_bp

@seeker_bp.route('/viewprofile')
def viewprofile():
    return render_template('seeker/viewprofile.html')
