from fastapi import FastAPI

app = FastAPI(
    title="My FastAPI Project",
    description="A simple FastAPI starter",
    version="1.0.0"
)

@app.get("/")
async def home():
    return {"message": "Hello, World!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/about")
async def about():
    return {
        "app_name": "My FastAPI Project",
        "version": "1.0.0",
        "description": "A simple FastAPI starter"
    }
