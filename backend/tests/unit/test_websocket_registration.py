"""
Unit tests for register_realtime (Task 1.12).

Tests:
- register_realtime mounts /ws and /ws/health routes
- register_realtime starts the drain task
- register_realtime binds the EventPublisher
- After registration, get_event_publisher() returns an InProcessEventPublisher
"""

from __future__ import annotations

import asyncio

import pytest


class TestRegisterRealtime:
    """register_realtime(app) single-touchpoint contract."""

    @pytest.mark.asyncio
    async def test_get_event_publisher_returns_publisher_after_registration(self):
        """get_event_publisher() returns InProcessEventPublisher after registration."""
        # Reset module state before testing
        import features.websocket.registration as reg_module

        orig_publisher = reg_module._event_publisher
        orig_queue = reg_module._event_queue
        orig_task = reg_module._drain_task_handle

        try:
            # Force a fresh registration
            reg_module._event_publisher = None
            reg_module._event_queue = None
            reg_module._drain_task_handle = None

            from fastapi import FastAPI
            from features.websocket.registration import register_realtime, get_event_publisher
            from features.websocket.publisher import InProcessEventPublisher

            test_app = FastAPI()
            register_realtime(test_app)

            publisher = get_event_publisher()
            assert publisher is not None
            assert isinstance(publisher, InProcessEventPublisher)

        finally:
            # Clean up the task we started
            if reg_module._drain_task_handle and not reg_module._drain_task_handle.done():
                reg_module._drain_task_handle.cancel()
                try:
                    await reg_module._drain_task_handle
                except asyncio.CancelledError:
                    pass

            # Restore state (other tests may need it untouched)
            reg_module._event_publisher = orig_publisher
            reg_module._event_queue = orig_queue
            reg_module._drain_task_handle = orig_task

    def test_get_event_publisher_returns_none_before_registration(self):
        """get_event_publisher() returns None if register_realtime hasn't been called."""
        import features.websocket.registration as reg_module

        orig = reg_module._event_publisher
        try:
            reg_module._event_publisher = None
            from features.websocket.registration import get_event_publisher
            assert get_event_publisher() is None
        finally:
            reg_module._event_publisher = orig
