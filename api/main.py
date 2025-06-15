from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.chatbot import CashifyChatbotService
from app.logs.logger import Logger
import uuid

# Initialize FastAPI app
app = FastAPI(
    title="Cashify Chatbot API",
    description="AI-powered customer service chatbot for Cashify",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
logger = Logger().get_logger()
chatbot_service = None


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.on_event("startup")
async def startup_event():
    """Initialize chatbot service on startup"""
    global chatbot_service
    try:
        chatbot_service = CashifyChatbotService()
        logger.info("FastAPI application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Cashify Chatbot API is running"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Cashify Chatbot API"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint for processing user messages"""
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        response = chatbot_service.chat(request.message)
        
        return ChatResponse(
            response=response
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
