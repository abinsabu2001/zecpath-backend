from rest_framework.views import exception_handler
import logging

security_logger = logging.getLogger("django.security")

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:

        if response.status_code in (401, 403):
            request = context.get("request")

            security_logger.warning(
                f"Security event: HTTP {response.status_code} "
                f"at {request.path if request else 'unknown path'}"
            )

        response.data = {
            "success": False,
            "status": response.status_code,
            "errors": response.data,
        }

    return response