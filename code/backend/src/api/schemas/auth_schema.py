import re
from typing import Any, Dict, Optional

from src.core.exceptions import ValidationError


def validate_email(email: object) -> str:
    """
    Validate email address.

    Args:
        email: Email address to validate

    Returns:
        Validated email address

    Raises:
        ValidationError: If email is invalid
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email is required", "email", email)

    # Standard email validation regex
    email_regex = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email, re.IGNORECASE):
        raise ValidationError("Invalid email format", "email", email)

    return email


def validate_password(password: object) -> str:
    """
    Validate password.

    Args:
        password: Password to validate

    Returns:
        Validated password

    Raises:
        ValidationError: If password is invalid
    """
    if not password or not isinstance(password, str):
        raise ValidationError("Password is required", "password")

    # Enhanced password policy:
    # - Minimum 12 characters
    # - At least one digit
    # - At least one uppercase letter
    # - At least one lowercase letter
    # - At least one special character (e.g., !@#$%^&*()-_+=)
    if len(password) < 12:
        raise ValidationError(
            "Password must be at least 12 characters long", "password"
        )

    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit", "password")

    if not re.search(r"[A-Z]", password):
        raise ValidationError(
            "Password must contain at least one uppercase letter", "password"
        )

    if not re.search(r"[a-z]", password):
        raise ValidationError(
            "Password must contain at least one lowercase letter", "password"
        )

    if not re.search(r"[!@#$%^&*()-_+=]", password):
        raise ValidationError(
            "Password must contain at least one special character (!@#$%^&*()-_+=)",
            "password",
        )

    return password


def validate_username(username: str) -> str:
    """
    Validate username.

    Args:
        username: Username to validate

    Returns:
        Validated username

    Raises:
        ValidationError: If username is invalid
    """
    if not username or not isinstance(username, str):
        raise ValidationError("Username is required", "username", username)

    if len(username) < 3:
        raise ValidationError(
            "Username must be at least 3 characters long", "username", username
        )

    if len(username) > 30:
        raise ValidationError(
            "Username cannot exceed 30 characters", "username", username
        )

    # Check for valid characters (alphanumeric, underscore, hyphen)
    username_regex = r"^[a-zA-Z0-9_-]+$"
    if not re.match(username_regex, username):
        raise ValidationError(
            "Username can only contain letters, numbers, underscores, and hyphens",
            "username",
            username,
        )

    return username


def validate_wallet_address(wallet_address: str) -> Optional[str]:
    """
    Validate wallet address.

    Args:
        wallet_address: Wallet address to validate

    Returns:
        Validated wallet address

    Raises:
        ValidationError: If wallet address is invalid
    """
    if wallet_address is None:
        return None

    if not isinstance(wallet_address, str):
        raise ValidationError(
            "Wallet address must be a string", "wallet_address", wallet_address
        )

    if not wallet_address.strip():
        return None

    # Ethereum address validation (0x followed by 40 hex characters)
    eth_regex = r"^0x[a-fA-F0-9]{40}$"
    if not re.match(eth_regex, wallet_address):
        raise ValidationError(
            "Invalid Ethereum wallet address format", "wallet_address", wallet_address
        )

    return wallet_address


def validate_login_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate login request data.

    Args:
        data: Request data

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    # Check required fields
    if "email" not in data:
        raise ValidationError("Email is required", "email")

    if "password" not in data:
        raise ValidationError("Password is required", "password")

    # Validate fields
    email = validate_email(data["email"])
    password = data["password"]  # Don't validate password complexity for login

    if not password or not isinstance(password, str):
        raise ValidationError("Password is required", "password")

    return {"email": email, "password": password}


def validate_register_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate registration request data.

    Args:
        data: Request data

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    # Check required fields
    if "email" not in data:
        raise ValidationError("Email is required", "email")

    if "username" not in data:
        raise ValidationError("Username is required", "username")

    if "password" not in data:
        raise ValidationError("Password is required", "password")

    # Validate fields
    email = validate_email(data["email"])
    username = validate_username(data["username"])
    password = validate_password(data["password"])

    # Validate optional fields
    wallet_address = None
    if "wallet_address" in data:
        wallet_address = validate_wallet_address(data["wallet_address"])

    # Return validated data
    validated_data = {"email": email, "username": username, "password": password}

    if wallet_address:
        validated_data["wallet_address"] = wallet_address

    return validated_data


def validate_refresh_token_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate refresh token request data.

    Args:
        data: Request data

    Returns:
        Validated data

    Raises:
        ValidationError: If validation fails
    """
    # Check required fields
    if "refresh_token" not in data:
        raise ValidationError("Refresh token is required", "refresh_token")

    # Validate refresh token
    refresh_token = data["refresh_token"]
    if not refresh_token or not isinstance(refresh_token, str):
        raise ValidationError(
            "Refresh token must be a non-empty string", "refresh_token"
        )

    return {"refresh_token": refresh_token}
