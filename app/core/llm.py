from langchain_groq import ChatGroq
from ..utils.config import get_settings
from ..utils.exceptions import GroqInitializationError
from ..logs.logger import Logger


class LLMinitialize:
    """
    This will initialize the LLM
    """
    def __init__(self):
        self.settings = get_settings()
        self.logger = Logger().get_logger()
    
    def get_groq_llm(self):
        """
        Get Groq LLM
        """
        try:
            llm = ChatGroq(
                groq_api_key=self.settings.groq.groq_api,
                model=self.settings.groq.model_name,
                temperature=self.settings.groq.temperature,
                max_tokens=self.settings.groq.max_token
            )
            return llm
        except GroqInitializationError as e:
            raise GroqInitializationError(
                error_code=500,
                message=f"Error while initializing the LLM {str(e)}"
            ) from e