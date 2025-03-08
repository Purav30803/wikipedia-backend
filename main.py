from fastapi import FastAPI

app = FastAPI()

@app.get("/api")
def read_root():
    return {"message": "Welcome to the API"}



@app.on_event("startup")
async def startup_event():
    print("App is starting.")

@app.on_event("shutdown")
async def shutdown_event():
    print("App is shutting down.")
