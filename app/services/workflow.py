from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.models.state import AgentState
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from ..logs.logger import Logger
import re

class WorkflowOrchestrator:
    """Orchestrates the chatbot workflow - Fixed Version"""
    
    def __init__(self, llm, llm_with_tools, tools):
        self.llm = llm
        self.llm_with_tools = llm_with_tools
        self.tools = tools
        self.max_tool_iterations = 3
        self.max_global_iterations = 2
        self.workflow = self._create_workflow()
        self.logger = Logger().get_logger()

    def _judge_query(self, state: AgentState) -> AgentState:
        """LLM-based query validation with robust prompt"""
        user_query = state["user_query"]
        
        # Much better judge prompt - focuses on intent rather than exact words
        judge_prompt = SystemMessage(content="""You are a customer service query validator for Cashify (an Indian smartphone marketplace).

YOUR JOB: Determine if this is a reasonable customer service question.

ACCEPT these types of questions (even with typos/grammar errors):
• Order status, tracking, delivery questions
• Account/profile information requests  
• Purchase history inquiries
• Product availability, prices, specifications
• Company information requests
• Coins, points, rewards questions
• General help requests
• Greetings and casual conversation
• Any question a customer might reasonably ask

REJECT only these:
• Clearly harmful/dangerous content
• Obviously spam or gibberish
• Requests for illegal activities

REMEMBER: 
- Customers may have typos or poor grammar
- Be VERY generous - when in doubt, ACCEPT
- This is customer service - almost all questions are valid

Respond with exactly one word: ACCEPT or REJECT

Examples:
"what is the status of my current order?" → ACCEPT
"how many coins do i hav?" → ACCEPT (typo but valid)
"tell me about cashify" → ACCEPT  
"wher is my delivry?" → ACCEPT (typos but valid intent)
"hello" → ACCEPT
"i want to buy iphone" → ACCEPT
"how to hack phones?" → REJECT
"random gibberish xyz123" → REJECT""")
        
        try:
            judge_messages = [judge_prompt, HumanMessage(content=f"Customer query: {user_query}")]
            judge_response = self.llm.invoke(judge_messages)
            
            # Parse the response more robustly
            decision_text = judge_response.content.strip().upper()
            
            # Look for ACCEPT/REJECT in the response
            if "ACCEPT" in decision_text:
                is_valid = True
                decision = "ACCEPT"
            elif "REJECT" in decision_text:
                is_valid = False
                decision = "REJECT"
            else:
                # If unclear response, default to ACCEPT (customer service should be permissive)
                is_valid = True
                decision = "ACCEPT (unclear response, defaulting to accept)"
                self.logger.warning(f"Unclear judge response: {decision_text}")
            
            self.logger.info(f"Judge decision for '{user_query}': {decision} -> {is_valid}")
            return {**state, "is_valid": is_valid}
            
        except Exception as e:
            # If judge completely fails, default to ACCEPT
            self.logger.error(f"Judge error, defaulting to ACCEPT: {e}")
            return {**state, "is_valid": True}

    def _model_call(self, state: AgentState) -> AgentState:
        """Enhanced model call with better tool result handling"""
        
        current_iteration = state.get('iteration_count', 0)
        global_iteration = state.get('global_iteration', 0)
        
        # Check if we just got tool results
        has_tool_results = any(isinstance(msg, ToolMessage) for msg in state['messages'])
        
        if has_tool_results and current_iteration > 1:
            # We have tool results, generate final answer
            tool_results = []
            for msg in reversed(state['messages']):
                if isinstance(msg, ToolMessage):
                    tool_results.append(msg.content)
                    break  # Get the most recent tool result
            
            if tool_results:
                # Create final response using tool results
                final_response = AIMessage(content=f"Based on your request, here's the information:\n\n{tool_results[0]}")
                
                self.logger.info(f"Generated final response from tool results: {final_response.content[:50]}...")
                
                return {
                    **state,
                    "messages": [final_response],
                    "iteration_count": current_iteration + 1
                }
        
        # Enhanced system prompt
        system_prompt = SystemMessage(content="""You are a Cashify customer service chatbot.

AVAILABLE TOOLS - USE THEM:
- get_order_tracking: For order status questions
- get_personal_profile: For profile/coins questions  
- get_last_purchases: For purchase history
- get_trending_product: For available products
- about_cashify: For company information
- get_real_time_search: For general searches

IMPORTANT RULES:
1. For "order status" questions → CALL get_order_tracking tool
2. After calling tools, wait for results and provide a helpful response
3. Do NOT repeat the same response multiple times
4. If you already called a tool, use the results to answer

Current iteration: {current_iteration}""")
        
        messages_to_send = [system_prompt] + state['messages']
        
        try:
            response = self.llm_with_tools.invoke(messages_to_send)
            
            # Check if response is empty or problematic
            if not hasattr(response, 'content'):
                response.content = "Let me help you with that."
            elif not response.content:
                response.content = "Let me help you with that."
            else:
                response.content = self._clean_response(response.content)
            
            self.logger.info(f"Model response - Content: '{response.content[:50]}...', Tool calls: {bool(getattr(response, 'tool_calls', None))}, Iteration: {current_iteration}")
            
            return {
                **state,
                "messages": [response],
                "iteration_count": current_iteration + 1
            }
            
        except Exception as e:
            self.logger.error(f"Model call error: {e}")
            return {
                **state,
                "messages": [AIMessage(content="Let me help you with your Cashify query.")],
                "iteration_count": current_iteration + 1
            }

    def _clean_response(self, content: str) -> str:
        """Clean up response content"""
        if not content:
            return "I'll help you with that information."
        
        # Remove ReAct patterns
        content = re.sub(r'(Thought:|Action:|Action Input:|Observation:|Final Answer:)', '', content)
        content = ' '.join(content.split())  # Remove extra whitespace
        
        return content.strip() if content.strip() else "I'll help you with that information."

    def _check_answer_quality(self, state: AgentState) -> AgentState:
        """Check if the answer satisfies the user query"""
        
        user_query = state["user_query"]
        last_message = state['messages'][-1]
        answer = getattr(last_message, 'content', '')
        
        # Check if we have tool results in the conversation
        tool_results = []
        for msg in state['messages']:
            if isinstance(msg, ToolMessage):
                tool_results.append(msg.content)
        
        self.logger.info(f"Answer quality check - Tool results found: {len(tool_results)}, Answer length: {len(answer)}")
        
        # If we have tool results and a reasonable answer, consider it satisfied
        if tool_results and answer and len(answer.strip()) > 20:
            # Check if the answer actually uses the tool results
            if any(keyword in answer.lower() for keyword in ['order', 'status', 'tracking', 'delivery']):
                self.logger.info("Answer quality: SATISFIED (has tool results and relevant content)")
                return {**state, "answer_satisfied": True}
        
        # If we have tool results but poor answer, we should be satisfied anyway
        # (the tool was called successfully)
        if tool_results:
            self.logger.info("Answer quality: SATISFIED (tool results available)")
            return {**state, "answer_satisfied": True}
        
        # If no tool results and it's an order query, not satisfied
        if "order" in user_query.lower() and not tool_results:
            self.logger.info("Answer quality: NOT SATISFIED (order query without tool results)")
            return {**state, "answer_satisfied": False}
        
        # For other cases, use LLM to check
        check_prompt = SystemMessage(content="""Check if this answer properly addresses the user's question.

Respond with ONLY:
- "SATISFIED" if answer addresses the question reasonably well
- "UNSATISFIED" if answer is clearly inadequate""")
        
        try:
            check_messages = [
                check_prompt,
                HumanMessage(content=f"Question: {user_query}\nAnswer: {answer}")
            ]
            check_response = self.llm.invoke(check_messages)
            
            is_satisfied = "SATISFIED" in check_response.content.upper()
            result = "SATISFIED" if is_satisfied else "UNSATISFIED"
            self.logger.info(f"Answer quality check result: {result}")
            
            return {**state, "answer_satisfied": is_satisfied}
            
        except Exception as e:
            # Default to satisfied if check fails
            self.logger.warning(f"Answer quality check failed: {e}")
            return {**state, "answer_satisfied": True}

    def _handle_invalid_query(self, state: AgentState) -> AgentState:
        """Handle invalid queries"""
        return {
            **state,
            "messages": [AIMessage(content="I am a Cashify Chatbot. I can only provide information about Cashify. How can I help?")],
            "iteration_count": 0,
            "global_iteration": 0,
            "answer_satisfied": True  # End the flow
        }

    def _handle_max_retries(self, state: AgentState) -> AgentState:
        """Handle max retries reached"""
        return {
            **state,
            "messages": [AIMessage(content="I don't have the answer you requested. How can I help with other queries?")],
            "answer_satisfied": True  # End the flow
        }

    def _retry_processing(self, state: AgentState) -> AgentState:
        """Reset for retry"""
        return {
            **state,
            "messages": state["messages"][:-1] if state["messages"] else [],
            "iteration_count": 0,
            "global_iteration": state.get("global_iteration", 0) + 1
        }

    def _should_continue_tools(self, state: AgentState) -> str:
        """Decide whether to continue with tools"""
        last_msg = state['messages'][-1]
        iteration = state.get('iteration_count', 0)
        
        if iteration > self.max_tool_iterations:
            return "check_answer"
        
        # Check for tool calls
        has_tool_calls = hasattr(last_msg, 'tool_calls') and last_msg.tool_calls
        return "continue" if has_tool_calls else "check_answer"

    def _route_after_judge(self, state: AgentState) -> str:
        """Route after validation"""
        return "process" if state["is_valid"] else "invalid"

    def _route_after_check(self, state: AgentState) -> str:
        """Route after answer check"""
        global_iter = state.get("global_iteration", 0)
        
        if global_iter >= self.max_global_iterations:
            return "max_retries"
        
        return "end" if state["answer_satisfied"] else "retry"

    def _create_workflow(self):
        """Create the workflow graph"""
        
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("judge", self._judge_query)
        graph.add_node("process", self._model_call)
        graph.add_node("tools", ToolNode(tools=self.tools))
        graph.add_node("check_answer", self._check_answer_quality)
        graph.add_node("invalid", self._handle_invalid_query)
        graph.add_node("retry", self._retry_processing)
        graph.add_node("max_retries", self._handle_max_retries)
        
        # Set entry point
        graph.set_entry_point("judge")
        
        # Add edges
        graph.add_conditional_edges(
            "judge", 
            self._route_after_judge, 
            {"process": "process", "invalid": "invalid"}
        )
        
        graph.add_conditional_edges(
            "process", 
            self._should_continue_tools, 
            {"continue": "tools", "check_answer": "check_answer"}
        )
        
        graph.add_edge("tools", "process")
        
        graph.add_conditional_edges(
            "check_answer", 
            self._route_after_check, 
            {"end": END, "retry": "retry", "max_retries": "max_retries"}
        )
        
        graph.add_edge("retry", "process")
        graph.add_edge("invalid", END)
        graph.add_edge("max_retries", END)
        
        return graph.compile()

    def process_query(self, user_input: str) -> str:
        """Process user query"""
        
        state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "is_valid": False,
            "iteration_count": 0,
            "global_iteration": 0,
            "answer_satisfied": False
        }
        
        try:
            self.logger.info(f"Processing query: {user_input}")
            result = self.workflow.invoke(state)
            
            self.logger.info(f"Workflow result keys: {result.keys()}")
            self.logger.info(f"Total messages in result: {len(result.get('messages', []))}")
            
            # Get the final message
            if result.get('messages'):
                final_msg = result['messages'][-1]
                final_content = getattr(final_msg, 'content', '')
                
                # Check if content is empty or just whitespace
                if not final_content or not final_content.strip():
                    self.logger.warning("Empty final response detected")
                    
                    # Look for tool results in the conversation
                    for msg in reversed(result['messages']):
                        if isinstance(msg, ToolMessage) and msg.content:
                            final_content = f"Here's the information you requested:\n\n{msg.content}"
                            break
                    
                    # If still empty, provide a default response
                    if not final_content or not final_content.strip():
                        final_content = "I apologize, but I couldn't retrieve the information. Please try again or contact support."
                
                self.logger.info(f"Final response: {final_content[:100]}...")
                return final_content
            else:
                self.logger.error("No messages in workflow result")
                return "I encountered an issue processing your request. Please try again."
            
        except Exception as e:
            self.logger.error(f"Query processing error: {e}")
            return f"Error processing query: {str(e)}"