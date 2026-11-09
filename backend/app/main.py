"""Compatibility HTTP factory and ASGI entry point."""

from app.entrypoints.http import create_app as create_app

app = create_app()
