"""Workflow orchestration"""

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.models.state import AgentState
from .processors import ChatProcessor
from .validators import QueryValidator
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage


class WorkflowOrchestrator:
    """Orchestrates the chatbot workflow"""
    
    def __init__(self, llm, llm_with_tools, tools):
        self.llm = llm
        self.llm_with_tools = llm_with_tools
        self.tools = tools
        self.validator = QueryValidator(llm)
        self.processor = ChatProcessor(llm, llm_with_tools, self.validator)
        self.max_global_iterations = 2
        self.workflow = self._create_workflow()
    
    def _judge_query(self, state: AgentState) -> AgentState:
        """Validate incoming query"""
        is_valid = self.validator.validate_query(state["user_query"])
        return {**state, "is_valid": is_valid}
    
    def _handle_invalid_query(self, state: AgentState) -> AgentState:
        """Handle invalid queries"""
        return {**state, 
                "messages": [AIMessage(content="I am a Cashify Chatbot. I can only provide information about Cashify. How can I help?")],
                "iteration_count": 0, "global_iteration": 0, "answer_satisfied": False}
    
    def _handle_max_retries(self, state: AgentState) -> AgentState:
        """Handle when max global iterations reached"""
        return {**state,
                "messages": [AIMessage(content="I don't have the answer you requested. How can I help with other queries?")],
                "answer_satisfied": False}
    
    def _retry_processing(self, state: AgentState) -> AgentState:
        """Reset for retry with incremented global iteration"""
        return {**state,
                "messages": state["messages"][:-1] if state["messages"] else [],
                "iteration_count": 0,
                "global_iteration": state.get("global_iteration", 0) + 1}
    
    def _should_continue_tools(self, state: AgentState) -> str:
        """Decide whether to continue with tools or check answer"""
        last_msg = state['messages'][-1]
        iteration = state.get('iteration_count', 0)
        
        if iteration > self.processor.max_tool_iterations:
            return "check_answer"
        
        has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
        return "continue" if has_tool_calls else "check_answer"
    
    def _route_after_judge(self, state: AgentState) -> str:
        """Route based on validation result"""
        return "process" if state["is_valid"] else "invalid"
    
    def _route_after_check(self, state: AgentState) -> str:
        """Route based on answer quality and global iterations"""
        global_iter = state.get("global_iteration", 0)
        
        if global_iter >= self.max_global_iterations:
            return "max_retries"
        
        return "end" if state["answer_satisfied"] else "retry"
    
    def _create_workflow(self):
        """Create the main workflow graph"""
        
        # Create graph
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("judge", self._judge_query)
        graph.add_node("process", self.processor.process_with_llm)
        graph.add_node("tools", ToolNode(tools=self.tools))
        graph.add_node("check_answer", self.processor.check_answer_quality)
        graph.add_node("invalid", self._handle_invalid_query)
        graph.add_node("retry", self._retry_processing)
        graph.add_node("max_retries", self._handle_max_retries)
        
        # Set entry point
        graph.set_entry_point("judge")
        
        # Add edges
        graph.add_conditional_edges("judge", self._route_after_judge, {"process": "process", "invalid": "invalid"})
        graph.add_conditional_edges("process", self._should_continue_tools, {"continue": "tools", "check_answer": "check_answer"})
        graph.add_edge("tools", "process")
        graph.add_conditional_edges("check_answer", self._route_after_check, {"end": END, "retry": "retry", "max_retries": "max_retries"})
        graph.add_edge("retry", "process")
        graph.add_edge("invalid", END)
        graph.add_edge("max_retries", END)
        
        return graph.compile()
    
    def process_query(self, user_input: str) -> str:
        """Process a single user query"""
        
        state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "is_valid": False,
            "iteration_count": 0,
            "global_iteration": 0,
            "answer_satisfied": False
        }
        
        try:
            result = self.workflow.invoke(state)
            final_msg = result['messages'][-1]
            return getattr(final_msg, 'content', 'No response generated')
            
        except Exception as e:
            return f"Error processing query: {str(e)}"
