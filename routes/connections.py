
from flask import Blueprint, request, jsonify, render_template
from types import SimpleNamespace
from datetime import datetime
import logging

from models import db, Schools, APICredentials
from services.api_connection_service import APIConnectionService
from services.credential_storage_service import CredentialStorageService

logger = logging.getLogger(__name__)

connections_bp = Blueprint(
    'connections',
    __name__,
    url_prefix='/connections'
)


# Display saved school connections
@connections_bp.route('/', methods=['GET'])
def show_connections():
    try:
        saved_connections = []

        schools = Schools.query.all()

        for school in schools:
            credentials = APICredentials.query.filter_by(
                school_id=school.id
            ).first()

            # Display only whether credentials exist.
            # Never send the actual secrets to the template.
            if credentials and credentials.api_key:
                saved_connections.append(
                    SimpleNamespace(
                        id=school.id,
                        school_name=school.name,
                        api_endpoint=school.api_endpoint,
                        api_token=bool(credentials.api_token),
                        created_at=credentials.created_at
                    )
                )

        return render_template(
            'school_connections.html',
            saved_connections=saved_connections
        )

    except Exception:
        logger.exception("Error loading connections page")
        return "Error loading connections page", 500


# Test a new connection
@connections_bp.route('/test', methods=['POST'])
def test_connection():
    try:
        data = request.get_json(silent=True) or {}

        api_endpoint = data.get('api_endpoint')
        api_key = data.get('api_key')
        api_token = data.get('api_token')

        if not api_endpoint or not api_key:
            return jsonify({
                'success': False,
                'message': 'Please enter both the API address and API key.'
            }), 400

        result = APIConnectionService.test_connection(
            api_endpoint=api_endpoint,
            api_key=api_key,
            api_token=api_token
        )

        return jsonify(result), (
            200 if result.get('success') else 400)

    except Exception:
        logger.exception("Error testing new connection")
        return jsonify({
            'success': False,
            'message': 'Something went wrong while testing the connection.'
        }), 500


# Save a new connection
@connections_bp.route('/save', methods=['POST'])
def save_connection():
    try:
        data = request.get_json(silent=True) or {}

        school_name = data.get('school_name')
        api_endpoint = data.get('api_endpoint')
        api_key = data.get('api_key')
        api_token = data.get('api_token')

        if not school_name or not api_endpoint or not api_key:
            return jsonify({
                'success': False,
                'message': 'School name, API address, and API key are required.'
            }), 400

        # Encrypt credentials before saving
        encrypted_key = CredentialStorageService.encrypt_credential(
            api_key
        )

        encrypted_token = (
            CredentialStorageService.encrypt_credential(api_token)
            if api_token else None
        )

        # Check whether school already exists
        school = Schools.query.filter_by(
            name=school_name
        ).first()

        if school:
            school.api_endpoint = api_endpoint
            school.is_connected = True
        else:
            school = Schools(
                name=school_name,
                api_endpoint=api_endpoint,
                is_connected=True
            )
            db.session.add(school)

        # Generate school ID without committing yet
        db.session.flush()

        # Check existing credentials
        credentials = APICredentials.query.filter_by(
            school_id=school.id
        ).first()

        if credentials:
            credentials.api_key = encrypted_key
            credentials.api_token = encrypted_token
            credentials.created_at = datetime.utcnow()
        else:
            credentials = APICredentials(
                school_id=school.id,
                api_key=encrypted_key,
                api_token=encrypted_token,
                created_at=datetime.utcnow()
            )
            db.session.add(credentials)

        db.session.commit()

        logger.info("Connection saved for school ID %s", school.id)

        return jsonify({
            'success': True,
            'message': 'Connection saved successfully.',
            'school_id': school.id
        }), 201

    except Exception:
        db.session.rollback()
        logger.exception("Error saving connection")

        return jsonify({
            'success': False,
            'message': 'Could not save the connection. Please try again.'
        }), 500


# Test an already saved connection
@connections_bp.route('/test-saved/<int:connection_id>', methods=['POST'])
def test_saved_connection(connection_id):
    try:
        school = db.session.get(Schools, connection_id)

        if not school:
            return jsonify({
                'success': False,
                'message': 'School connection not found.'
            }), 404

        credentials = CredentialStorageService.get_decrypted_credentials(
            connection_id
        )

        if not credentials or not credentials.get('api_key'):
            return jsonify({
                'success': False,
                'message': 'Saved API credentials were not found.'
            }), 404

        result = APIConnectionService.test_connection(
            api_endpoint=school.api_endpoint,
            api_key=credentials.get('api_key'),
            api_token=credentials.get('api_token')
        )

        return jsonify(result), (200 if result.get('success') else 400)

    except Exception:
        logger.exception("Error testing saved connection")
        return jsonify({
            'success': False,
            'message': 'Could not test the saved connection.'
        }), 500


# Delete a saved connection
@connections_bp.route('/delete/<int:connection_id>', methods=['DELETE'])
def delete_connection(connection_id):
    try:
        school = db.session.get(Schools, connection_id)

        if not school:
            return jsonify({
                'success': False,
                'message': 'School connection not found.'
            }), 404

        # Delete credentials first
        APICredentials.query.filter_by(
            school_id=connection_id
        ).delete()

        # Delete school
        db.session.delete(school)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Connection removed successfully.'
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("Error deleting connection")

        return jsonify({
            'success': False,
            'message': 'Could not remove the connection.'
        }), 500
