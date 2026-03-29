from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response


class StandardEnvelopeRenderer(JSONRenderer):
    """Wrap all responses in the standard {message,data,status} envelope."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get("response")

        # Non-HTTP response (e.g. streaming or form data) should pass through.
        if response is None:
            return super().render(data, accepted_media_type, renderer_context)

        status_code = response.status_code

        # If already wrapped, do not double wrap
        if isinstance(data, dict) and {"message", "data", "status"}.issubset(set(data.keys())):
            return super().render(data, accepted_media_type, renderer_context)

        if 200 <= status_code < 300:
            envelope = {
                "message": "Success",
                "data": data if data is not None else {},
                "status": status_code,
            }
        else:
            message = "Error"
            payload = {}
            if isinstance(data, dict):
                message = data.get("message") or data.get("detail") or message
                payload = {k: v for k, v in data.items() if k not in ["message", "detail"]}
            elif data is not None:
                message = str(data)

            envelope = {
                "message": message,
                "data": payload if payload else {},
                "status": status_code,
            }

        return super().render(envelope, accepted_media_type, renderer_context)
