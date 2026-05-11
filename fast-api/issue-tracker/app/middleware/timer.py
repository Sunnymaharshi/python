import time
from fastapi import Request

async def timer_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = f"{time.time() - start_time:.4f}s"
    response.headers["X-Process-Time"] = str(process_time)
    return response