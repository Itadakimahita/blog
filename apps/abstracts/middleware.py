import logging


logger = logging.getLogger("debug_requests")


class DebugRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        user_identifier = "anonymous"
        if user is not None and getattr(user, "is_authenticated", False):
            user_identifier = getattr(user, "email", str(user))

        logger.info(
            "Incoming request %s %s user=%s ip=%s",
            request.method,
            request.get_full_path(),
            user_identifier,
            request.META.get("REMOTE_ADDR"),
        )
        return self.get_response(request)
