import json
import os

from django.core.management.base import BaseCommand
from django.test import RequestFactory
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework.permissions import AllowAny

"""
Management command to export the OpenAPI schema to interfaces/openapi.json.

- Uses drf_yasg to generate the schema.
- Injects the proper server URL computed from environment or defaults.
- Ensures JWT Bearer security scheme appears in the spec by referencing default auth in settings.
"""

def _compute_server_url() -> str:
    """
    Compute a full server URL for the OpenAPI 'servers' (or host/schemes) based on env.
    Honors reverse proxy headers during docs serving, but here we approximate with environment:
    - API_SCHEME (default: https)
    - API_HOST (default: localhost)
    - API_PORT (optional; if set and not default for scheme, include).
    """
    scheme = os.getenv("API_SCHEME", "https")
    host = os.getenv("API_HOST", "localhost")
    port = os.getenv("API_PORT", "")
    if port and (scheme, port) not in {("http", "80"), ("https", "443")}:
        return f"{scheme}://{host}:{port}"
    return f"{scheme}://{host}"

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Build a request to the API root under /api/ so basePath is correct
        factory = RequestFactory()
        django_request = factory.get('/api/?format=openapi')

        # Build schema view with AllowAny so generation is not blocked.
        # The API itself uses JWT via REST_FRAMEWORK settings.
        schema_view = get_schema_view(
            openapi.Info(
                title="My API",
                default_version='v1',
                description="API for Expense Tracker with JWT authentication.",
            ),
            public=True,
            permission_classes=(AllowAny,),
        )

        # Render schema
        response = schema_view.without_ui(cache_timeout=0)(django_request)
        response.render()

        openapi_schema = json.loads(response.content.decode())

        # Attempt to inject server URL hints into swagger v2 fields
        # If 'host' or 'schemes' missing/placeholder, set them using env.
        server_url = _compute_server_url()
        try:
            # Parse back to host/scheme for Swagger 2.0 structure
            from urllib.parse import urlparse
            parsed = urlparse(server_url)
            openapi_schema["host"] = parsed.netloc
            openapi_schema["schemes"] = [parsed.scheme]
            # Ensure basePath is '/api'
            openapi_schema["basePath"] = "/api"
        except Exception:
            pass

        # Ensure securityDefinitions for JWT (Bearer) exist alongside any others
        security_definitions = openapi_schema.setdefault("securityDefinitions", {})
        if "Bearer" not in security_definitions:
            security_definitions["Bearer"] = {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: 'Authorization: Bearer {token}'",
            }
        # Default security for endpoints (can be overridden by AllowAny endpoints)
        openapi_schema.setdefault("security", [{"Bearer": []}])

        # Write to interfaces/openapi.json at project root of backend
        # When manage.py runs from expense_tracker_backend/, relative 'interfaces' is correct.
        output_dir = "interfaces"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "openapi.json")

        with open(output_path, "w") as f:
            json.dump(openapi_schema, f, indent=2)
