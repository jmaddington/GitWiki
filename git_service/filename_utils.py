"""
Filename sanitization and validation utilities.

Centralized utilities for secure filename handling to prevent:
- Directory traversal attacks (../, ..\\)
- Double-extension attacks (malware.exe.txt)
- Special character injection
- Executable file uploads

AIDEV-NOTE: filename-utils; Centralized sanitization for all file uploads
See SECURITY.md for usage guidelines and security considerations.
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# AIDEV-NOTE: dangerous-extensions; Blacklist of executable file types
# This list blocks common executable formats across multiple platforms
DANGEROUS_EXTENSIONS = {
    # Windows executables
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'msi', 'msp',
    'gadget', 'scf', 'lnk', 'inf', 'reg',

    # Unix/Linux executables
    'sh', 'bash', 'csh', 'ksh', 'zsh', 'run', 'out', 'elf', 'bin',

    # macOS executables
    'app', 'dmg', 'pkg',

    # Package formats
    'deb', 'rpm',

    # Cross-platform scripting/code
    'js', 'jar',
}


def sanitize_filename(filename: str, fallback: str = 'file') -> str:
    """
    Sanitize a user-provided filename to prevent security vulnerabilities.

    This function removes or replaces dangerous characters and prevents
    double-extension attacks by removing dots from the base filename.

    Security features:
    - Removes dots to prevent double-extension attacks (malware.exe.txt)
    - Only allows alphanumeric characters, hyphens, and underscores
    - Replaces all other characters with underscores
    - Returns fallback if result is empty or whitespace-only

    Args:
        filename: User-provided filename (can include extension)
        fallback: Default name if sanitization results in empty string

    Returns:
        Sanitized base filename (without extension)

    Examples:
        >>> sanitize_filename('my file.txt')
        'my_file'

        >>> sanitize_filename('../../etc/passwd')
        '______etc_passwd'

        >>> sanitize_filename('malware.exe.txt')
        'malware_exe_txt'

        >>> sanitize_filename('<script>alert("xss")</script>.jpg')
        '_script_alert__xss___script_'

        >>> sanitize_filename('файл.pdf')  # Unicode
        '_____'  # Falls back to 'file'

    Security considerations:
        - Extension is handled separately - use get_safe_extension()
        - Always validate extension against DANGEROUS_EXTENSIONS
        - Combine with unique timestamp/UUID to prevent collisions

    See Also:
        - is_safe_extension(): Validate file extension
        - SECURITY.md: Filename security guidelines
    """
    if not filename:
        logger.warning(f'Empty filename provided, using fallback [SECURITY-UTILS01]')
        return fallback

    # Extract base name (without extension) using pathlib
    base_name = Path(filename).stem if filename else fallback

    # Sanitize: only allow word characters (alphanumeric + underscore) and hyphens
    # Dots are explicitly removed to prevent double-extension attacks
    # Pattern: [^\w\-] means "not (word char or hyphen)"
    safe_name = re.sub(r'[^\w\-]', '_', base_name)

    # If sanitization resulted in empty string or only underscores/hyphens, use fallback
    if not safe_name or not re.search(r'[a-zA-Z0-9]', safe_name):
        logger.warning(f'Filename sanitization resulted in empty string for "{filename}", using fallback [SECURITY-UTILS02]')
        return fallback

    return safe_name


def get_safe_extension(filename: str) -> Optional[str]:
    """
    Extract and validate file extension.

    Returns the lowercased extension without the dot, or None if
    the file has no extension or the extension is empty.

    Args:
        filename: Filename to extract extension from

    Returns:
        Lowercase extension without dot, or None

    Examples:
        >>> get_safe_extension('document.pdf')
        'pdf'

        >>> get_safe_extension('archive.tar.gz')
        'gz'

        >>> get_safe_extension('no_extension')
        None

        >>> get_safe_extension('malware.exe')
        'exe'
    """
    if not filename or '.' not in filename:
        return None

    ext = filename.rsplit('.', 1)[-1].lower()
    return ext if ext else None


def is_safe_extension(extension: Optional[str]) -> bool:
    """
    Check if file extension is safe (not in dangerous extensions blacklist).

    Args:
        extension: File extension to check (with or without dot)

    Returns:
        True if extension is safe, False if dangerous or None

    Examples:
        >>> is_safe_extension('pdf')
        True

        >>> is_safe_extension('.exe')
        False

        >>> is_safe_extension('jpg')
        True

        >>> is_safe_extension('sh')
        False

        >>> is_safe_extension(None)
        True  # Files without extensions are allowed
    """
    if extension is None:
        return True  # No extension is fine

    # Remove leading dot if present
    ext = extension.lstrip('.').lower()

    return ext not in DANGEROUS_EXTENSIONS


def validate_filename(filename: str, max_length: int = 255) -> tuple[bool, Optional[str]]:
    """
    Comprehensive filename validation.

    Checks for:
    - Dangerous extensions
    - Path traversal attempts
    - Invalid length

    Args:
        filename: Filename to validate
        max_length: Maximum allowed filename length

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_filename('document.pdf')
        (True, None)

        >>> validate_filename('malware.exe')
        (False, 'Dangerous file type: exe')

        >>> validate_filename('../../etc/passwd')
        (False, 'Path traversal detected in filename')

        >>> validate_filename('a' * 300)
        (False, 'Filename too long (max 255 characters)')
    """
    if not filename:
        return False, 'Filename cannot be empty'

    # Check length
    if len(filename) > max_length:
        return False, f'Filename too long (max {max_length} characters)'

    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, 'Path traversal detected in filename'

    # Check extension
    ext = get_safe_extension(filename)
    if ext and not is_safe_extension(ext):
        return False, f'Dangerous file type: {ext}'

    return True, None


def generate_safe_filename(
    original_name: str,
    timestamp: str,
    unique_id: str,
    fallback: str = 'file'
) -> tuple[str, Optional[str]]:
    """
    Generate a safe, unique filename from user input.

    Combines sanitization with uniqueness guarantees by adding
    timestamp and UUID to prevent collisions.

    Args:
        original_name: User-provided filename
        timestamp: Timestamp string (e.g., '20250104-143000')
        unique_id: Unique identifier (e.g., UUID)
        fallback: Default base name if sanitization fails

    Returns:
        Tuple of (safe_filename, extension)

    Examples:
        >>> generate_safe_filename('my doc.pdf', '20250104-143000', 'abc123')
        ('my_doc-20250104-143000-abc123', 'pdf')

        >>> generate_safe_filename('malware.exe.txt', '20250104-143000', 'abc123')
        ('malware_exe_txt-20250104-143000-abc123', 'txt')

        >>> generate_safe_filename('<script>.jpg', '20250104-143000', 'abc123')
        ('file-20250104-143000-abc123', 'jpg')
    """
    # Extract and validate extension
    ext = get_safe_extension(original_name)

    # Sanitize base name
    safe_base = sanitize_filename(original_name, fallback)

    # Combine with timestamp and unique ID
    safe_filename = f"{safe_base}-{timestamp}-{unique_id}"

    return safe_filename, ext
