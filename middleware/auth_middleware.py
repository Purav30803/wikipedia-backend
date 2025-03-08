from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import time
import uuid


class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Restrict middleware processing to specific routes
        if not (request.url.path.startswith("/api") or request.url.path.startswith("/docs")):
            return JSONResponse(
                status_code=404,
                content={"message": "ACCESS DENIED"}
            )

        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id  # Attach it to the request state

        # Add request ID to the logger's context
        with logger.contextualize(request_id=request_id):
            # Log the incoming request details
            logger.info(f"Incoming request: {request.method} {request.url} | Client: {request.client.host}")
            start_time = time.time()

            # Process the request
            response = await call_next(request)

            # Log the response details
            process_time = time.time() - start_time
            logger.info(
                f"Completed request: {request.method} {request.url} | "
                f"Status: {response.status_code} | Time: {process_time:.2f}s"
            )

        return response