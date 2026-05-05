"""
Input sanitization utilities for Food Store backend.

These functions are meant to be used in Pydantic field validators
to clean user input before it reaches the database.
"""

import html
import re


def sanitize_string(value: str) -> str:
    """Strip whitespace and escape HTML entities.

    Use for: names, descriptions, addresses, any text field.
    """
    stripped = value.strip()
    return html.escape(stripped, quote=True)


def sanitize_email(value: str) -> str:
    """Strip whitespace and lowercase.

    Use for: email fields before validation.
    """
    return value.strip().lower()


def sanitize_phone(value: str) -> str:
    """Strip whitespace and keep only digits, +, -, (), and spaces.

    Use for: phone number fields.
    """
    stripped = value.strip()
    # Allow digits, +, -, (, ), and spaces
    return re.sub(r"[^\d\+\-\(\)\s]", "", stripped)