from app.core.llm import LLMinitialize
from app.services.workflow import WorkflowOrchestrator
from app.logs.logger import Logger
from app.core.tools import AVAILABLE_TOOLS
from app.models.state import QueryResponses
from langchain_core.messages import ToolMessage, HumanMessage
import uuid
import os
import json
from datetime import datetime

import json
import os
from datetime import datetime

class ChatHistoryManager:
    def __init__(self, history_file="data/chat_history.txt"):
        self.history_file = history_file
        self.max_history = 5
        
    def save_query(self, user_message: str, bot_response: str):
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_message,
            "bot": bot_response
        }
        
        history.append(new_entry)
        
        if len(history) > self.max_history:
            history = history[-self.max_history:]
        
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def get_context_text(self) -> str:
        if not os.path.exists(self.history_file):
            return ""
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            if history:
                queries = [entry["user"] for entry in history[-3:]]
                return f"\nRecent conversation context: {' | '.join(queries)}"
            return ""
        except:
            return ""
    
    def clear_history(self):
        if os.path.exists(self.history_file):
            os.remove(self.history_file)


class CashifyChatbotService:
    def __init__(self):
        self.logger = Logger().get_logger()
        self.history_manager = ChatHistoryManager()  
        self._initialize_components()
    
    def _initialize_components(self):
        try:
            llm_init = LLMinitialize()
            self.llm = llm_init.get_groq_llm()
            self.tools = AVAILABLE_TOOLS
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            self.workflow = WorkflowOrchestrator(self.llm, self.llm_with_tools, self.tools)
            
            tool_names = [tool.name for tool in self.tools]
            self.logger.info(f"Chatbot initialized with {len(self.tools)} tools: {tool_names}")
        except Exception as e:
            self.logger.error(f"Failed to initialize: {str(e)}")
            raise
    
    def process_query(self, user_input: str) -> QueryResponses:
        try:
            context_text = self.history_manager.get_context_text()
            
            response = self.workflow.process_query_with_context(user_input, context_text)
            
            if hasattr(response, 'final_response'):
                final_response = response.final_response
            else:
                final_response = str(response)
            
            if not final_response or final_response == "None" or final_response.strip() == "":
                final_response = "I couldn't process your request. Please try again."
            
            self.history_manager.save_query(user_input, final_response)
            
            return response
            
        except Exception as e:
            error_id = str(uuid.uuid4())
            error_response = f"Error processing query: {str(e)}"
            
            self.history_manager.save_query(user_input, error_response)
            
            error_message = ToolMessage(
                content=f"Error: {str(e)}",
                tool_call_id=error_id
            )
            return QueryResponses(
                final_response=error_response,
                messages=[error_message]
            )

    def get_chat_history(self) -> list: 
        try:
            with open(self.history_manager.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def chat(self, message: str) -> QueryResponses:
        return self.process_query(message)
    
    def clear_chat_history(self):
        self.history_manager.clear_history()