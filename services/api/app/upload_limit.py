"""Reject oversized /orders/extract bodies before Starlette parses (and spools) the multipart."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.errors import envelope
from app.services.documents import MAX_BYTES

PATH = "/orders/extract"
SLACK = 1024 * 1024  # multipart framing around the file
_TOO_LARGE = ("file_too_large", "The PDF is larger than 20 MB.")


class UploadSizeLimit:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != PATH:
            await self.app(scope, receive, send)
            return

        limit = MAX_BYTES + SLACK
        length = dict(scope["headers"]).get(b"content-length", b"")
        if length.isdigit() and int(length) > limit:
            await envelope(413, *_TOO_LARGE)(scope, receive, send)
            return

        seen = 0
        too_large = False

        async def counting_receive() -> Message:
            nonlocal seen, too_large
            if too_large:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    # The app's own parse error (400) is discarded below in favour of the 413.
                    too_large = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            if not too_large:
                await send(message)

        try:
            await self.app(scope, counting_receive, guarded_send)
        finally:
            if too_large:
                await envelope(413, *_TOO_LARGE)(scope, receive, send)
