from typing import List, Any
from app.core.llm import LLMinitialize
from app.core.tools import AvailableTools
from app.services.workflow import WorkflowOrchestrator
from app.logs.logger import Logger


class CashifyChatbotService:
    def __init__(self):
        self.logger = Logger().get_logger()
        self._initialize_components()
    
    def _initialize_components(self):
        try:
            # Initialize LLM
            llm_init = LLMinitialize()
            self.llm = llm_init.get_groq_llm()
           
            self.tools = AvailableTools().tools
            
            self.logger.info(f"Available tools are {self.tools}")
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            
            # Initialize workflow
            self.workflow = WorkflowOrchestrator(self.llm, self.llm_with_tools, self.tools)
            
            # Log successful initialization with proper tool names
            tool_names = []
            for tool in self.tools:
                if hasattr(tool, 'name'):
                    tool_names.append(tool.name)
                elif hasattr(tool, '__name__'):
                    tool_names.append(tool.__name__)
                else:
                    tool_names.append(str(type(tool).__name__))
            
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