from app.core.llm import LLMinitialize
from app.services.workflow import WorkflowOrchestrator
from app.logs.logger import Logger
from app.core.tools import AVAILABLE_TOOLS
from app.models.state import QueryResponses
from langchain_core.messages import ToolMessage
import uuid

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
    
    def process_query(self, user_input: str) -> QueryResponses:
        """Process user query and return QueryResponses object"""
        try:
            return self.workflow.process_query(user_input)
        except Exception as e:
            # Create ToolMessage with proper tool_call_id
            error_id = str(uuid.uuid4())
            error_message = ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=error_id
            )
            return QueryResponses(
                final_response=f"Error processing query: {str(e)}",
                messages=[error_message]
            )
    
    def chat(self, message: str) -> QueryResponses:
        """Main chat interface that returns QueryResponses object"""
        try:
            return self.process_query(message)
        except Exception as e:
            # Create ToolMessage with proper tool_call_id
            error_id = str(uuid.uuid4())
            error_message = ToolMessage(
                content=f"Chat error: {str(e)}",
                tool_call_id=error_id
            )
            return QueryResponses(
                final_response="Sorry, I encountered an error. Please try again.",
                messages=[error_message]
            )