from langchain_core.messages import SystemMessage, AIMessage, ToolMessage, HumanMessage
from app.models.state import AgentState
from app.services.validators import QueryValidator
import re

class ResponseProcessor:
    """Processes and cleans LLM responses"""
    
    @staticmethod
    def clean_response(content: str) -> str:
        """Remove ReAct formatting and clean response"""
        if not content:
            return "I couldn't generate a response. Please try again."
        
        # Remove ReAct patterns
        content = re.sub(r'(Thought:|Action:|Observation:|Final Answer:)', '', content)
        
        # Clean whitespace
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        cleaned = ' '.join(lines)
        
        return cleaned if cleaned else "I couldn't generate a response. Please try again."
    
    @staticmethod
    def get_last_tool_result(messages) -> str:
        """Extract last tool result from messages"""
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                return msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        return ""


class ChatProcessor:
    """Main chat processing logic"""
    
    def __init__(self, llm, llm_with_tools, validator: QueryValidator):
        self.llm = llm
        self.llm_with_tools = llm_with_tools
        self.validator = validator
        self.processor = ResponseProcessor()
        self.max_tool_iterations = 2
    
    def process_with_llm(self, state: AgentState) -> AgentState:
        """Main LLM processing with tools"""
        
        iteration = state.get('iteration_count', 0)
        
        # Force answer if too many iterations
        if iteration > self.max_tool_iterations:
            last_tool_result = self.processor.get_last_tool_result(state['messages'])
            content = f"Based on available information: {last_tool_result}" if last_tool_result else "Information processed."
            
            return {**state, "messages": [AIMessage(content=content)], "iteration_count": iteration}
        
        # System prompt
        prompt = SystemMessage(content="""You are a Cashify customer service agent.

TOOLS AVAILABLE:
- get_personal_profile: user coins, profile, gift cards
- get_order_tracking: order status, delivery info
- get_last_purchases: purchase history
- get_trending_product: available products
- about_cashify: company information
- get_real_time_search: external searches

INSTRUCTIONS:
- Use appropriate tools for user queries
- Provide helpful responses after tool use
- Focus only on Cashify services
- Be conversational and professional""")
        
        try:
            response = self.llm_with_tools.invoke([prompt] + state['messages'])
            
            # Clean response content
            if hasattr(response, 'content') and response.content:
                response.content = self.processor.clean_response(response.content)
                
                # Safety check
                if not self.validator.is_response_safe(response.content):
                    response.content = "I can only provide Cashify-related information. How can I help?"
            
            return {**state, "messages": [response], "iteration_count": iteration + 1}
            
        except Exception:
            return {**state, 
                    "messages": [AIMessage(content="I can only provide Cashify-related information. How can I help?")],
                    "iteration_count": iteration}
    
    def check_answer_quality(self, state: AgentState) -> AgentState:
        """Check if answer satisfies user query"""
        
        user_query = state["user_query"]
        last_msg = state['messages'][-1]
        answer = getattr(last_msg, 'content', '')
        
        # Handle empty responses
        if not answer or "couldn't generate" in answer:
            tool_result = self.processor.get_last_tool_result(state['messages'])
            if tool_result and "trending" in user_query.lower():
                fixed_answer = f"Here are the trending products:\n\n{tool_result}"
                updated_state = {**state}
                updated_state["messages"] = state["messages"][:-1] + [AIMessage(content=fixed_answer)]
                updated_state["answer_satisfied"] = True
                return updated_state
            
            return {**state, "answer_satisfied": False}
        
        # Quality check with LLM
        try:
            prompt = SystemMessage(content="""Check if the answer addresses the question properly.
            
Respond ONLY: "SATISFIED" or "UNSATISFIED" """)
            
            check_msg = HumanMessage(content=f"Question: {user_query}\nAnswer: {answer}")
            response = self.llm.invoke([prompt, check_msg])
            
            satisfied = "SATISFIED" in response.content.upper()
            return {**state, "answer_satisfied": satisfied}
            
        except:
            return {**state, "answer_satisfied": True}