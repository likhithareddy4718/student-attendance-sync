from cryptography.fernet import Fernet
import os
import logging
from datetime import datetime
from models import db, APICredentials

logger = logging.getLogger(__name__)
class CredentialStorageService:
    """
    Encrypts API credentials before saving them, and decrypts them when we need to use them.
    This keeps secrets safe even if someone gets into the database.
    """

    @staticmethod
    def _get_cipher():
        """
        Get the encryption key from the environment.
        This key is like the master password that locks and unlocks all secrets.
        """
        encryption_key = os.getenv('ENCRYPTION_KEY')

        if not encryption_key:
            raise ValueError(
                'ENCRYPTION_KEY environment variable is not set. '
                'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )

        return Fernet(encryption_key.encode())
    @staticmethod
    def encrypt_credential(credential_value):
        """
        Lock up a single secret (like an API key) so it can't be read in the database.

        Args:
            credential_value (str): The secret to lock up (e.g., 'abc123xyz')

        Returns:
            str: The locked-up version, safe to store in the database
        """
        if not credential_value:
            return None

        try:
            cipher = CredentialStorageService._get_cipher()
            encrypted = cipher.encrypt(credential_value.encode())
            return encrypted.decode()

        except Exception as e:
            logger.error(f"Error encrypting credential: {str(e)}")
            raise
    @staticmethod
    def decrypt_credential(encrypted_value):
        """
        Unlock a secret so we can actually use it to call the school's API.

        Args:
            encrypted_value (str): The locked-up version from the database

        Returns:
            str: The original secret, ready to use
        """
        if not encrypted_value:
            return None

        try:
            cipher = CredentialStorageService._get_cipher()
            decrypted = cipher.decrypt(encrypted_value.encode())
            return decrypted.decode()

        except Exception as e:
            logger.error(f"Error decrypting credential: {str(e)}")
            raise
    @staticmethod
    def save_connection(school_id, api_key, api_token=None):
        """
        Save the admin's API credentials to the database, locked up.
        If credentials already exist for this school, we update them.

        Args:
            school_id (int): Which school these credentials belong to
            api_key (str): The API key the admin entered
            api_token (str, optional): Any extra token the API needs

        Returns:
            dict: A result object with 'success' (True/False) and 'message'
        """
        try:
            # Encrypt both secrets before we touch the database
            encrypted_key = CredentialStorageService.encrypt_credential(api_key)
            encrypted_token = CredentialStorageService.encrypt_credential(api_token) if api_token else None

            # Check if we already have credentials for this school
            existing = APICredentials.query.filter_by(school_id=school_id).first()

            if existing:
                # Update the old ones with the new locked-up secrets
                existing.api_key = encrypted_key
                existing.api_token = encrypted_token
                existing.created_at = datetime.utcnow()
                logger.info(f"Updated credentials for school {school_id}")
            else:
                # Create a brand new row for this school's secrets
                new_credentials = APICredentials(
                    school_id=school_id,
                    api_key=encrypted_key,
                    api_token=encrypted_token,
                    created_at=datetime.utcnow()
                )
                db.session.add(new_credentials)
                logger.info(f"Saved new credentials for school {school_id}")

            # Write everything to the database
            db.session.commit()

            return {
                'success': True,
                'message': 'Connection details saved securely.'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving credentials for school {school_id}: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to save connection details. Please try again.'
            }
    @staticmethod
    def get_decrypted_credentials(school_id):
        """
        Fetch a school's credentials from the database and unlock them.
        Use this when you need to actually call the school's API.

        Args:
            school_id (int): Which school's credentials to fetch

        Returns:
            dict: A dict with 'api_key' and 'api_token' (both unlocked), or None if not found
        """
        try:
            credentials = APICredentials.query.filter_by(school_id=school_id).first()

            if not credentials:
                return None

            # Unlock both secrets
            return {
                'api_key': CredentialStorageService.decrypt_credential(credentials.api_key),
                'api_token': CredentialStorageService.decrypt_credential(credentials.api_token)
            }

        except Exception as e:
            logger.error(f"Error retrieving credentials for school {school_id}: {str(e)}")
            return None