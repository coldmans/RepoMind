from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def read_root():
    return {"message" : "Hello, RepoMind Backend!"}

@app.get("/health")
async def health_check():
    return{"status" : "ok"}