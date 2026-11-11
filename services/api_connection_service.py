
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import logging

logger = logging.getLogger(__name__)


class APIConnectionService:
    """Tests and validates connections to school attendance APIs."""

    @staticmethod
    def test_connection(api_endpoint, api_key, api_token=None, timeout=5):
        """
        Test if we can reach the school's API with the given credentials.

        Args:
            api_endpoint (str): The school's API URL
            api_key (str): The API key for authentication
            api_token (str, optional): Additional API token
            timeout (int): Maximum waiting time in seconds

        Returns:
            dict: Success status, message and HTTP status code.
        """

        try:
            # Build the request headers
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            # Add extra token if provided
            if api_token:
                headers['X-API-Token'] = api_token

            # Send GET request to the API
            response = requests.get(
                api_endpoint,
                headers=headers,
                timeout=timeout
            )

            # Successful response
            if 200 <= response.status_code < 300:
                logger.info(f"API connection successful to {api_endpoint}")

                return {
                    'success': True,
                    'message': 'Connection successful. API is reachable and credentials are valid.',
                    'status_code': response.status_code
                }

            # Authentication failed
            elif response.status_code in [401, 403]:
                logger.warning(f"API authentication failed for {api_endpoint}")

                return {
                    'success': False,
                    'message': 'Authentication failed. Please check your API key and token.',
                    'status_code': response.status_code
                }

            # Other HTTP errors
            else:
                logger.warning(
                    f"API returned status {response.status_code} for {api_endpoint}"
                )

                return {
                    'success': False,
                    'message': f'Connection failed. The API returned status {response.status_code}.',
                    'status_code': response.status_code
                }

        except Timeout:
            logger.error(f"API connection timeout for {api_endpoint}")

            return {
                'success': False,
                'message': 'Connection timed out. The API took too long to respond. Check the address and try again.',
                'status_code': None
            }

        except ConnectionError:
            logger.error(f"API connection error for {api_endpoint}")

            return {
                'success': False,
                'message': 'Could not reach the API. Check the address and your internet connection.',
                'status_code': None
            }

        except RequestException as e:
            logger.error(
                f"API request failed for {api_endpoint}: {str(e)}"
            )

            return {
                'success': False,
                'message': f'An error occurred: {str(e)}',
                'status_code': None
            }
