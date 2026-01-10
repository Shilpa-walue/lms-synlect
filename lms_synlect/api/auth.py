"""
Authentication API for DreamsLMS React Frontend Integration
Provides login, register, logout, and user profile endpoints
"""

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
import secrets


def generate_api_token(user):
    """Generate a simple API token for the user session"""
    # Use Frappe's built-in token generation or create a custom one
    token = secrets.token_urlsafe(32)

    # Store token in cache with expiry (3600 seconds = 1 hour)
    cache_key = f"api_token:{token}"
    frappe.cache().set_value(cache_key, user, expires_in_sec=3600)

    return token


def validate_api_token(token):
    """Validate an API token and return the user"""
    if not token:
        return None

    cache_key = f"api_token:{token}"
    user = frappe.cache().get_value(cache_key)
    return user


def get_user_data(user):
    """Get user data in the format expected by React frontend"""
    user_doc = frappe.get_doc("User", user)

    # Determine role
    roles = frappe.get_roles(user)
    if "Course Creator" in roles or "Instructor" in roles:
        role = "instructor"
    elif "System Manager" in roles or "Administrator" in roles:
        role = "admin"
    else:
        role = "student"

    # Get LMS Member info if exists
    member_info = {}
    if frappe.db.exists("LMS Enrollment", {"member": user}):
        member_info = frappe.get_all(
            "LMS Enrollment",
            filters={"member": user},
            fields=["name"],
            limit=1
        )

    # Get instructor ID if user is instructor
    instructor_id = None
    student_id = None

    # Check if user has instructor profile in LMS
    if role == "instructor":
        # Frappe LMS uses User doctype directly, instructor_id is the user name
        instructor_id = user

    if role == "student":
        student_id = user

    # Parse full name
    full_name = user_doc.full_name or ""
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    return {
        "id": user_doc.name,
        "email": user_doc.email,
        "role": role,
        "firstName": first_name,
        "lastName": last_name,
        "fullName": full_name,
        "avatar": user_doc.user_image or "",
        "isActive": user_doc.enabled == 1,
        "isVerified": True,  # Frappe handles email verification
        "createdAt": str(user_doc.creation),
        "studentId": student_id,
        "instructorId": instructor_id,
    }


@frappe.whitelist(allow_guest=True)
def login(email=None, password=None, remember_me=False):
    """
    Login endpoint for React frontend

    Args:
        email: User email
        password: User password
        remember_me: Whether to extend session duration

    Returns:
        {
            "success": bool,
            "user": User object,
            "token": API token,
            "refreshToken": Refresh token,
            "expiresIn": Token expiry in seconds,
            "message": Status message
        }
    """
    try:
        # Parse JSON if data comes as string
        if not email and frappe.request.data:
            data = json.loads(frappe.request.data)
            email = data.get("email")
            password = data.get("password")
            remember_me = data.get("rememberMe", False)

        if not email or not password:
            return {
                "success": False,
                "message": _("Email and password are required")
            }

        # Authenticate user using Frappe's built-in method
        try:
            frappe.local.login_manager.authenticate(email, password)
            frappe.local.login_manager.post_login()
        except frappe.AuthenticationError:
            return {
                "success": False,
                "message": _("Invalid email or password")
            }

        user = frappe.session.user

        # Generate tokens
        token = generate_api_token(user)
        refresh_token = secrets.token_urlsafe(32)

        # Store refresh token with longer expiry
        refresh_expiry = 86400 * 7 if remember_me else 86400  # 7 days or 1 day
        frappe.cache().set_value(
            f"refresh_token:{refresh_token}",
            user,
            expires_in_sec=refresh_expiry
        )

        # Get user data
        user_data = get_user_data(user)

        frappe.db.commit()

        return {
            "success": True,
            "user": user_data,
            "token": token,
            "refreshToken": refresh_token,
            "expiresIn": 3600,
            "message": _("Login successful")
        }

    except Exception as e:
        frappe.log_error(f"Login error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": _("An error occurred during login")
        }


@frappe.whitelist(allow_guest=True)
def register(full_name=None, email=None, password=None, confirm_password=None, role="student"):
    """
    Register a new user

    Args:
        full_name: User's full name
        email: User email
        password: User password
        confirm_password: Password confirmation
        role: User role (student/instructor)

    Returns:
        {
            "success": bool,
            "user": User object,
            "token": API token,
            "refreshToken": Refresh token,
            "expiresIn": Token expiry in seconds,
            "message": Status message
        }
    """
    try:
        # Parse JSON if data comes as string
        if not email and frappe.request.data:
            data = json.loads(frappe.request.data)
            full_name = data.get("fullName") or data.get("full_name")
            email = data.get("email")
            password = data.get("password")
            confirm_password = data.get("confirmPassword") or data.get("confirm_password")
            role = data.get("role", "student")

        # Validation
        if not all([full_name, email, password]):
            return {
                "success": False,
                "message": _("Full name, email, and password are required")
            }

        if password != confirm_password:
            return {
                "success": False,
                "message": _("Passwords do not match")
            }

        # Check password strength
        if len(password) < 8:
            return {
                "success": False,
                "message": _("Password must be at least 8 characters long")
            }

        # Check if user already exists
        if frappe.db.exists("User", email):
            return {
                "success": False,
                "message": _("An account with this email already exists")
            }

        # Parse name
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Create user
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "new_password": password,
            "send_welcome_email": 0,
            "user_type": "Website User"
        })

        user.insert(ignore_permissions=True)

        # Assign role based on selection
        if role == "instructor":
            user.add_roles("Course Creator")
        else:
            # Add LMS Student role if it exists
            if frappe.db.exists("Role", "LMS Student"):
                user.add_roles("LMS Student")

        frappe.db.commit()

        # Auto-login the user
        frappe.local.login_manager.login_as(email)

        # Generate tokens
        token = generate_api_token(email)
        refresh_token = secrets.token_urlsafe(32)

        frappe.cache().set_value(
            f"refresh_token:{refresh_token}",
            email,
            expires_in_sec=86400
        )

        # Get user data
        user_data = get_user_data(email)

        return {
            "success": True,
            "user": user_data,
            "token": token,
            "refreshToken": refresh_token,
            "expiresIn": 3600,
            "message": _("Registration successful")
        }

    except Exception as e:
        frappe.log_error(f"Registration error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": str(e) if frappe.conf.developer_mode else _("An error occurred during registration")
        }


@frappe.whitelist()
def logout():
    """
    Logout the current user

    Returns:
        {
            "success": bool,
            "message": Status message
        }
    """
    try:
        # Get token from header
        auth_header = frappe.get_request_header("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Remove token from cache
            frappe.cache().delete_value(f"api_token:{token}")

        frappe.local.login_manager.logout()
        frappe.db.commit()

        return {
            "success": True,
            "message": _("Logged out successfully")
        }

    except Exception as e:
        frappe.log_error(f"Logout error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": _("An error occurred during logout")
        }


@frappe.whitelist()
def me():
    """
    Get current user profile

    Returns:
        {
            "success": bool,
            "user": User object
        }
    """
    try:
        user = frappe.session.user

        if user == "Guest":
            return {
                "success": False,
                "message": _("Not authenticated")
            }

        user_data = get_user_data(user)

        return {
            "success": True,
            "user": user_data
        }

    except Exception as e:
        frappe.log_error(f"Get user error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": _("An error occurred while fetching user data")
        }


@frappe.whitelist(allow_guest=True)
def refresh_token(refresh_token=None):
    """
    Refresh the API token using a refresh token

    Args:
        refresh_token: The refresh token

    Returns:
        {
            "success": bool,
            "token": New API token,
            "refreshToken": New refresh token,
            "expiresIn": Token expiry in seconds,
            "message": Status message
        }
    """
    try:
        # Parse JSON if data comes as string
        if not refresh_token and frappe.request.data:
            data = json.loads(frappe.request.data)
            refresh_token = data.get("refreshToken") or data.get("refresh_token")

        if not refresh_token:
            return {
                "success": False,
                "message": _("Refresh token is required")
            }

        # Validate refresh token
        cache_key = f"refresh_token:{refresh_token}"
        user = frappe.cache().get_value(cache_key)

        if not user:
            return {
                "success": False,
                "message": _("Invalid or expired refresh token")
            }

        # Delete old refresh token
        frappe.cache().delete_value(cache_key)

        # Generate new tokens
        new_token = generate_api_token(user)
        new_refresh_token = secrets.token_urlsafe(32)

        frappe.cache().set_value(
            f"refresh_token:{new_refresh_token}",
            user,
            expires_in_sec=86400
        )

        return {
            "success": True,
            "token": new_token,
            "refreshToken": new_refresh_token,
            "expiresIn": 3600,
            "message": _("Token refreshed successfully")
        }

    except Exception as e:
        frappe.log_error(f"Token refresh error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": _("An error occurred while refreshing token")
        }


@frappe.whitelist(allow_guest=True)
def forgot_password(email=None):
    """
    Send password reset email

    Args:
        email: User email

    Returns:
        {
            "success": bool,
            "message": Status message
        }
    """
    try:
        # Parse JSON if data comes as string
        if not email and frappe.request.data:
            data = json.loads(frappe.request.data)
            email = data.get("email")

        if not email:
            return {
                "success": False,
                "message": _("Email is required")
            }

        if not frappe.db.exists("User", email):
            # Don't reveal if user exists or not for security
            return {
                "success": True,
                "message": _("If an account with this email exists, you will receive a password reset link")
            }

        # Use Frappe's built-in password reset
        from frappe.core.doctype.user.user import reset_password
        reset_password(email)

        return {
            "success": True,
            "message": _("If an account with this email exists, you will receive a password reset link")
        }

    except Exception as e:
        frappe.log_error(f"Forgot password error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": _("An error occurred while processing your request")
        }


@frappe.whitelist()
def change_password(current_password=None, new_password=None, confirm_password=None):
    """
    Change user password

    Args:
        current_password: Current password
        new_password: New password
        confirm_password: Confirm new password

    Returns:
        {
            "success": bool,
            "message": Status message
        }
    """
    try:
        # Parse JSON if data comes as string
        if not current_password and frappe.request.data:
            data = json.loads(frappe.request.data)
            current_password = data.get("currentPassword") or data.get("current_password")
            new_password = data.get("newPassword") or data.get("new_password")
            confirm_password = data.get("confirmPassword") or data.get("confirm_password")

        user = frappe.session.user

        if user == "Guest":
            return {
                "success": False,
                "message": _("Not authenticated")
            }

        if not all([current_password, new_password]):
            return {
                "success": False,
                "message": _("Current password and new password are required")
            }

        if new_password != confirm_password:
            return {
                "success": False,
                "message": _("New passwords do not match")
            }

        if len(new_password) < 8:
            return {
                "success": False,
                "message": _("Password must be at least 8 characters long")
            }

        # Verify current password
        from frappe.utils.password import check_password
        try:
            check_password(user, current_password)
        except frappe.AuthenticationError:
            return {
                "success": False,
                "message": _("Current password is incorrect")
            }

        # Update password
        from frappe.utils.password import update_password
        update_password(user, new_password)

        frappe.db.commit()

        return {
            "success": True,
            "message": _("Password changed successfully")
        }

    except Exception as e:
        frappe.log_error(f"Change password error: {str(e)}", "Auth API")
        return {
            "success": False,
            "message": _("An error occurred while changing password")
        }
