"""
Utility functions for GitWiki git service.

This module provides helper functions for SSH testing, validation,
and other git-related utilities.
"""

import subprocess
import logging
from typing import Dict
from pathlib import Path

logger = logging.getLogger(__name__)


def test_ssh_connection(remote_url: str, ssh_key_path: str = None) -> Dict:
    """
    Test SSH connection to GitHub or other Git remote.

    AIDEV-NOTE: ssh-test; Tests SSH authentication without modifying repository

    Args:
        remote_url: Git remote URL (e.g., git@github.com:user/repo.git)
        ssh_key_path: Optional path to SSH private key

    Returns:
        {
            "success": true/false,
            "message": "Connection successful" or error details,
            "host": "github.com" or other host
        }

    Examples:
        >>> test_ssh_connection("git@github.com:user/repo.git")
        {"success": True, "message": "SSH connection successful", "host": "github.com"}

        >>> test_ssh_connection("git@github.com:user/repo.git", "/path/to/key")
        {"success": True, "message": "SSH connection successful", "host": "github.com"}
    """
    try:
        # Extract host from git URL
        # git@github.com:user/repo.git -> github.com
        # https://github.com/user/repo.git -> github.com
        if '@' in remote_url:
            # SSH format: git@github.com:user/repo.git
            host = remote_url.split('@')[1].split(':')[0]
        elif '://' in remote_url:
            # HTTPS format: https://github.com/user/repo.git
            host = remote_url.split('://')[1].split('/')[0]
        else:
            logger.warning(f'Could not parse host from URL: {remote_url} [UTILS-SSH01]')
            return {
                "success": False,
                "message": f"Invalid remote URL format: {remote_url}",
                "host": None
            }

        # Build SSH command
        ssh_cmd = ['ssh', '-T', f'git@{host}', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=10']

        # Add SSH key if provided
        if ssh_key_path:
            ssh_key_path = Path(ssh_key_path)
            if not ssh_key_path.exists():
                logger.error(f'SSH key not found at {ssh_key_path} [UTILS-SSH02]')
                return {
                    "success": False,
                    "message": f"SSH key not found: {ssh_key_path}",
                    "host": host
                }
            ssh_cmd.insert(1, '-i')
            ssh_cmd.insert(2, str(ssh_key_path))

        logger.info(f'Testing SSH connection to {host} [UTILS-SSH03]')

        # Run SSH test command
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        # GitHub returns exit code 1 even on successful authentication
        # Check stderr for success message
        stderr_lower = result.stderr.lower()

        # Different hosts have different success messages
        success_indicators = [
            'successfully authenticated',  # GitHub
            'you\'ve successfully authenticated',  # GitHub alt
            'welcome',  # Some Git servers
            'hi',  # GitHub greeting
        ]

        is_success = any(indicator in stderr_lower for indicator in success_indicators)

        if is_success:
            logger.info(f'SSH connection to {host} successful [UTILS-SSH04]')
            return {
                "success": True,
                "message": "SSH connection successful",
                "host": host
            }
        else:
            # Check for specific error conditions
            if 'permission denied' in stderr_lower:
                error_msg = "SSH permission denied - check your SSH key"
            elif 'connection refused' in stderr_lower:
                error_msg = f"Connection refused by {host}"
            elif 'no route to host' in stderr_lower:
                error_msg = f"Cannot reach {host} - check network connection"
            elif 'could not resolve hostname' in stderr_lower:
                error_msg = f"Cannot resolve hostname: {host}"
            else:
                error_msg = result.stderr.strip() or "SSH connection failed"

            logger.warning(f'SSH connection to {host} failed: {error_msg} [UTILS-SSH05]')
            return {
                "success": False,
                "message": error_msg,
                "host": host
            }

    except subprocess.TimeoutExpired:
        error_msg = f"SSH connection timeout after 15 seconds"
        logger.error(f'{error_msg} [UTILS-SSH06]')
        return {
            "success": False,
            "message": error_msg,
            "host": host if 'host' in locals() else None
        }
    except Exception as e:
        error_msg = f"SSH connection error: {str(e)}"
        logger.error(f'{error_msg} [UTILS-SSH07]')
        return {
            "success": False,
            "message": error_msg,
            "host": host if 'host' in locals() else None
        }


def validate_remote_url(remote_url: str) -> bool:
    """
    Validate that a remote URL is in a valid Git format.

    Args:
        remote_url: Git remote URL to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_remote_url("git@github.com:user/repo.git")
        True
        >>> validate_remote_url("https://github.com/user/repo.git")
        True
        >>> validate_remote_url("invalid")
        False
    """
    if not remote_url:
        return False

    # Check for SSH format: git@host:path or user@host:path
    if '@' in remote_url and ':' in remote_url:
        return True

    # Check for HTTPS format: https://host/path
    if remote_url.startswith('https://') or remote_url.startswith('http://'):
        return True

    # Check for git:// protocol
    if remote_url.startswith('git://'):
        return True

    return False


def extract_repo_name(remote_url: str) -> str:
    """
    Extract repository name from remote URL.

    Args:
        remote_url: Git remote URL

    Returns:
        Repository name (e.g., "repo" from "git@github.com:user/repo.git")

    Examples:
        >>> extract_repo_name("git@github.com:user/repo.git")
        "repo"
        >>> extract_repo_name("https://github.com/user/repo.git")
        "repo"
    """
    if not remote_url:
        return ""

    # Remove .git suffix if present
    url = remote_url.rstrip('.git')

    # Extract last path component
    if '/' in url:
        return url.split('/')[-1]
    elif ':' in url:
        # SSH format: git@github.com:user/repo
        return url.split(':')[-1].split('/')[-1]

    return url
