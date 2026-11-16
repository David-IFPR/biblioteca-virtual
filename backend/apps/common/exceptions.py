from rest_framework.views import exception_handler


class BusinessError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def api_exception_handler(exc, context):
    if isinstance(exc, BusinessError):
        from rest_framework.response import Response

        return Response({"detail": exc.message}, status=exc.status_code)

    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and "detail" not in data:
        messages = []
        for value in data.values():
            if isinstance(value, list):
                messages.extend(str(item) for item in value)
            elif isinstance(value, dict):
                for nested in value.values():
                    if isinstance(nested, list):
                        messages.extend(str(item) for item in nested)
                    else:
                        messages.append(str(nested))
            else:
                messages.append(str(value))
        if messages:
            response.data = {"detail": " ".join(messages), "errors": data}
    return response
