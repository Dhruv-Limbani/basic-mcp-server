
import contextlib
from fastapi import FastAPI, Request, HTTPException, status
from echo_server import mcp as echo_mcp
from math_server import mcp as math_mcp
from dotenv import load_dotenv
import os
load_dotenv()
API_KEY = os.environ["API_KEY"]

# ASGI middleware for API key authentication
class APIKeyMiddleware:
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
            auth_header = headers.get("authorization")

            # Expecting format: "Bearer <API_KEY>"
            if not auth_header or not auth_header.startswith("Bearer "):
                from starlette.responses import JSONResponse
                response = JSONResponse({"detail": "Missing or invalid Authorization header"}, status_code=401)
                await response(scope, receive, send)
                return

            token = auth_header.split("Bearer ")[-1].strip()
            if token != API_KEY:
                from starlette.responses import JSONResponse
                response = JSONResponse({"detail": "Invalid API Key"}, status_code=401)
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)

# Create a combined lifespan to manage both session managers
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(echo_mcp.session_manager.run())
        await stack.enter_async_context(math_mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(APIKeyMiddleware)
app.mount("/echo", echo_mcp.streamable_http_app())
app.mount("/math", math_mcp.streamable_http_app())

PORT = os.environ.get("PORT", 10000)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)