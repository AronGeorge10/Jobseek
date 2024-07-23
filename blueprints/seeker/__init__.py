from flask import Blueprint

seeker_bp = Blueprint('seeker', __name__)

from . import routes  # Import routes at the end to avoid circular imports
