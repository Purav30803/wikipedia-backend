from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from config.env import Env
from controller import wikipedia_controller
from middleware.auth_middleware import CustomMiddleware


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.add(
    "logs/app.log",
    rotation="30 MB",           # Rotate logs when they reach 30 MB
    retention="30 days",        # Keep logs for 30 days
    compression="zip",          # Compress old log files
    level="INFO",               # Minimum log level
    format="{time} - {level} - {message}"  # Log format    
)

app.add_middleware(CustomMiddleware)



@app.get("/api")
def read_root():
    database_url = Env.DATABASE_URL
    logger.info("API was accessed.")
    return {"message": "Welcome to the API"}


app.include_router(wikipedia_controller.wikipedia_router, prefix="/api/wikipedia", tags=["wiki"])


@app.on_event("startup")
async def startup_event():
    print("App is starting.")

@app.on_event("shutdown")
async def shutdown_event():
    print("App is shutting down.")
