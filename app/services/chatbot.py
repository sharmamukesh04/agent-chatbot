# app/services/chatbot.py

from app.core.llm import LLMinitialize
from app.services.workflow import WorkflowOrchestrator
from app.logs.logger import Logger

# Import the tools from the tools module
from app.core.tools import AVAILABLE_TOOLS


class CashifyChatbotService:
    def __init__(self):
        self.logger = Logger().get_logger()
        self._initialize_components()
    
    def _initialize_components(self):
        try:
            # Initialize LLM
            llm_init = LLMinitialize()
            self.llm = llm_init.get_groq_llm()
            
            # Use the imported tools
            self.tools = AVAILABLE_TOOLS
            
            # Bind tools to LLM
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            
            # Initialize workflow
            self.workflow = WorkflowOrchestrator(self.llm, self.llm_with_tools, self.tools)
            
            # Log successful initialization
            tool_names = [tool.name for tool in self.tools]
            self.logger.info(f"Chatbot initialized with {len(self.tools)} tools: {tool_names}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize: {str(e)}")
            raise
    
    def chat(self, message: str) -> str:
        try:
            response = self.workflow.process_query(message)
            return response
        except Exception as e:
            self.logger.error(f"Chat error: {str(e)}")
            return "Sorry, I encountered an error. Please try again."