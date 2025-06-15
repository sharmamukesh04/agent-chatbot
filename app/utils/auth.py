from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from .config import get_settings
from ..logs.logger import Logger


logger = Logger()

settings = get_settings()

api_key_header = APIKeyHeader(
    name=settings.api_key_name or "X-API-Key",
    auto_error=False
)


async def verify_api_key(
    api_key: str = Security(api_key_header),
) -> str:
    """
    Verify that the provided API key matches the expected value.

    Raises:
        HTTPException: If the API key is missing or invalid.

    Returns:
        str: The valid API key if verification passes.
    """
    expected_api_key = str(settings.api_key)

    if not expected_api_key:
        logger.error("API Key is not configured in settings.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key configuration error"
        )

    if not api_key:
        logger.warning("Missing API Key in request headers.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key"
        )

    if api_key.strip() != expected_api_key.strip():
        logger.warning("Invalid API Key attempt.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )

    logger.debug("API Key successfully validated.")
    return api_key
