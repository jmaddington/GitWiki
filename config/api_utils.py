"""
API utility functions for standardized error responses and common operations.

AIDEV-NOTE: api-utils; Standardized error handling for all API endpoints
"""

from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def error_response(message, error_code=None, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=None):
    """
    Create a standardized error response.

    Args:
        message: User-friendly error message
        error_code: Grepable error code for logging (e.g., "API-ERROR01")
        status_code: HTTP status code
        details: Optional dict with additional error details

    Returns:
        Response object with standardized error format

    Example:
        return error_response(
            "Failed to create branch",
            error_code="API-BRANCH-ERROR01",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"branch_name": "invalid-name"}
        )
    """
    response_data = {
        'success': False,
        'error': {
            'message': message,
        }
    }

    if error_code:
        response_data['error']['code'] = error_code

    if details:
        response_data['error']['details'] = details

    # Log the error
    log_msg = f'API Error: {message}'
    if error_code:
        log_msg += f' [{error_code}]'

    if status_code >= 500:
        logger.error(log_msg)
    else:
        logger.warning(log_msg)

    return Response(response_data, status=status_code)


def success_response(data, message=None, status_code=status.HTTP_200_OK):
    """
    Create a standardized success response.

    Args:
        data: Response data (dict)
        message: Optional success message
        status_code: HTTP status code (default 200)

    Returns:
        Response object with standardized success format

    Example:
        return success_response(
            data={'branch_name': 'draft-1-abc123'},
            message="Branch created successfully"
        )
    """
    response_data = {
        'success': True,
        'data': data
    }

    if message:
        response_data['message'] = message

    return Response(response_data, status=status_code)


def validation_error_response(errors, error_code="VALIDATION-ERROR"):
    """
    Create a standardized validation error response.

    Args:
        errors: Serializer errors or custom validation errors
        error_code: Grepable error code for logging

    Returns:
        Response object with validation errors

    Example:
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)
    """
    logger.warning(f'Validation error: {errors} [{error_code}]')

    return Response(
        {
            'success': False,
            'error': {
                'message': 'Validation failed',
                'code': error_code,
                'validation_errors': errors
            }
        },
        status=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


def handle_exception(e, operation_name, error_code, user_message=None):
    """
    Handle exceptions consistently across API endpoints.

    Args:
        e: Exception instance
        operation_name: Name of operation (e.g., "create branch")
        error_code: Grepable error code
        user_message: Optional user-friendly message (defaults to generic message)

    Returns:
        Tuple of (error_response, should_rollback)

    Example:
        try:
            repo.create_branch()
        except GitRepositoryError as e:
            response, _ = handle_exception(
                e, "create branch", "API-BRANCH-ERROR01",
                "Failed to create branch. Please try again."
            )
            return response
    """
    # Determine if this is a known exception type
    from git_service.git_operations import GitRepositoryError
    from django.core.exceptions import ValidationError, ObjectDoesNotExist

    should_rollback = True

    if isinstance(e, GitRepositoryError):
        # Git operation errors - usually 500
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = user_message or f"Failed to {operation_name}. Please try again."
        details = {'technical_error': str(e)}

    elif isinstance(e, ValidationError):
        # Validation errors - 400
        status_code = status.HTTP_400_BAD_REQUEST
        message = user_message or f"Invalid data for {operation_name}"
        details = {'validation_errors': e.message_dict if hasattr(e, 'message_dict') else str(e)}
        should_rollback = False

    elif isinstance(e, ObjectDoesNotExist):
        # Not found errors - 404
        status_code = status.HTTP_404_NOT_FOUND
        message = user_message or f"Resource not found for {operation_name}"
        details = {'error': str(e)}
        should_rollback = False

    elif isinstance(e, PermissionError):
        # Permission errors - 403
        status_code = status.HTTP_403_FORBIDDEN
        message = user_message or f"Permission denied for {operation_name}"
        details = {'error': str(e)}
        should_rollback = False

    else:
        # Unknown errors - 500
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = user_message or f"An unexpected error occurred during {operation_name}"
        details = {'error': str(e), 'type': type(e).__name__}

    logger.error(f'Exception in {operation_name}: {type(e).__name__}: {str(e)} [{error_code}]')

    response = error_response(
        message=message,
        error_code=error_code,
        status_code=status_code,
        details=details
    )

    return response, should_rollback


def require_fields(data, required_fields):
    """
    Validate that required fields are present in data.

    Args:
        data: Dict to validate
        required_fields: List of required field names

    Returns:
        Tuple of (is_valid: bool, missing_fields: list)

    Example:
        is_valid, missing = require_fields(data, ['branch_name', 'file_path'])
        if not is_valid:
            return validation_error_response({'missing_fields': missing})
    """
    missing = [field for field in required_fields if field not in data or data[field] is None]
    return len(missing) == 0, missing


# AIDEV-NOTE: user-attribution; Standardized user info for git commits across all API endpoints
def get_user_info_for_commit(user):
    """
    Get standardized user info for git commits.

    This is the SINGLE source of truth for user attribution in git commits.
    All git operations should use this function to ensure consistent authorship.

    Args:
        user: Django User instance

    Returns:
        dict: User info with 'name' and 'email' keys

    Example:
        # Direct from request
        user_info = get_user_info_for_commit(request.user)

        # From session
        user_info = get_user_info_for_commit(session.user)
    """
    return {
        'name': user.get_full_name() or user.username,
        'email': user.email or f'{user.username}@gitwiki.local'
    }
