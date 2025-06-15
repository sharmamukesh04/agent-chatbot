class GroqInitializationError(Exception):
    """Exception raised when Groq LLM initialization fails"""
    def __init__(self, error_code: int, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised for validation failures"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ProcessingError(Exception):
    """Exception raised during processing failures"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)