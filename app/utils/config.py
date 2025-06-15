"""Configuration settings for Cashify Chatbot"""
from functools import lru_cache
import os
from pydantic_settings import BaseSettings
from pydantic import Field, BaseModel
from dotenv import load_dotenv


class GROQConfig(BaseModel):
    """GROQ configuration for LLM"""
    groq_api: str = Field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    model_name: str = Field(default_factory=lambda: os.getenv("MODEL_NAME", "deepseek-r1-distill-llama-70b"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("TEMPERATURE", "0.1")))
    max_token: int = Field(default_factory=lambda: int(os.getenv("MAX_TOKENS", "4000")))

    class Config:
        extra = "allow"


class LocalData(BaseModel):
    """Local Data file paths for JSON files"""
    trending_products: str = Field(default="trending_products.json")
    order_status: str = Field(default="order_tracking.json")
    about_info: str = Field(default="about.txt")
    last_purchase: str = Field(default="last_purchase.json")
    personal_info: str = Field(default="points.json")

    class Config:
        extra = "allow"


class Settings(BaseSettings):
    """Main application settings"""
    # Application metadata
    app_name: str = "Cashify Chatbot"
    app_description: str = "AI Agentic Chatbot for Cashify's Customers"
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "False").lower() == "true")
    api_key_name: str = "x-api-key"
    api_key: str = Field(default_factory=lambda: os.getenv("API_AUTH_KEY", ""))
    
    groq: GROQConfig = Field(default_factory=GROQConfig)
    local_data: LocalData = Field(default_factory=LocalData)
    
    class Config:
        extra = "allow"
        env_file = ".env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Create and return settings instance
        settings = Settings()
        return settings
        
    except Exception as e:
        raise RuntimeError(
            f"Failed to load application settings: {str(e)}"
        ) from e


def get_groq_config() -> GROQConfig:
    """Get GROQ configuration"""
    return get_settings().groq


def get_local_data_config() -> LocalData:
    """Get local data configuration"""
    return get_settings().local_data

