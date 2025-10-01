from fastapi import FastAPI

app = FastAPI(
    title="Sortify",
    description="Organizes and answers from my pdf files",
    version="1.0.0"
)

@app.get("/")
async def home():
    return {"message": "Hello, World!"}

@app.get("/login")
async def login():
    return {"login": "logged in"}

@app.get("/register")
async def register():
    return {"register": "registered"}

@app.get("/about")
async def about():
    return {
        "app_name": "Sortify",
        "version": "1.0.0",
        "description": "Organizes and answers from my pdf files"
    }
