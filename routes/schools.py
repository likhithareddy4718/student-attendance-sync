
from flask import Blueprint, render_template, request, redirect, url_for, flash

from models.school import get_all_connected_schools, add_school_connection

schools_bp = Blueprint('schools', __name__, url_prefix='/schools')
