"""Checkout feature — atomic pay-first order creation.

This module provides endpoints for creating orders with integrated payment
validation. The order is only persisted if payment succeeds (online) or if
it's a pickup+cash order (no payment required).
"""
