from fastapi import FastAPI
from app.api.v1 import chat_routes

app = FastAPI(
    title="AI Chatbot API",
    description="Simple AI Chatbot API using FastAPI and DynamoDB",
    version="1.0.0",
)

# API 라우터 등록
app.include_router(chat_routes.router, prefix="/api/v1", tags=["Chatbot"])

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Chatbot API!"}
