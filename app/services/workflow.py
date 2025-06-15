from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.models.state import AgentState, QueryResponses
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from ..logs.logger import Logger
import re
from typing import List
import uuid

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
        user_query = state["user_query"]
        
        judge_prompt = SystemMessage(content="""You are a strict Cashify customer service query validator. Handle queries in ANY language (English, Hindi, etc.).

    ACCEPT ONLY these Cashify-related topics:
    • Order status, tracking, delivery (ऑर्डर स्थिति, ट्रैकिंग, डिलीवरी)
    • Account/profile/coins (खाता, प्रोफाइल, सिक्के)
    • Purchase history (खरीदारी का इतिहास)
    • Product prices, availability (उत्पाद मूल्य, उपलब्धता)
    • Cashify company information
    • Gadgets, smartphones, laptops (गैजेट्स, स्मार्टफोन, लैपटॉप)
    • Simple greetings (hello, नमस्ते, hi)

    STRICTLY REJECT everything else including:
    • Suicide, self-harm, mental health (आत्महत्या, मानसिक स्वास्थ्य)
    • Personal advice, relationships (व्यक्तिगत सलाह)
    • Other companies/services
    • General knowledge questions
    • Health, medical advice (स्वास्थ्य सलाह)
    • Philosophy, religion, politics
    • Harmful/dangerous content

    Examples:
    "मेरा ऑर्डर कहाँ है?" → ACCEPT
    "iPhone की कीमत क्या है?" → ACCEPT  
    "मैं परेशान हूँ" → REJECT
    "how to commit suicide" → REJECT
    "what is the meaning of life" → REJECT

    Respond with exactly: ACCEPT or REJECT""")
        
        try:
            judge_messages = [judge_prompt, HumanMessage(content=f"Query: {user_query}")]
            judge_response = self.llm.invoke(judge_messages)
            decision_text = judge_response.content.strip().upper()
            
            is_valid = "ACCEPT" in decision_text
            decision = "ACCEPT" if is_valid else "REJECT"
            
            self.logger.info(f"Judge decision for '{user_query}': {decision} -> {is_valid}")
            return {**state, "is_valid": is_valid}
            
        except Exception as e:
            self.logger.error(f"Judge error, defaulting to REJECT: {e}")
            return {**state, "is_valid": False}

    def _handle_invalid_query(self, state: AgentState) -> AgentState:
        return {
            **state,
            "messages": [AIMessage(content="I am a Cashify Chatbot and I can help you on query related to gadgets or queries related to cashify only")],
            "iteration_count": 0,
            "global_iteration": 0,
            "answer_satisfied": True
        }

    def _model_call(self, state: AgentState) -> AgentState:
        current_iteration = state.get('iteration_count', 0)
        
        system_prompt = SystemMessage(content="""You are a Cashify customer service chatbot. Respond in the user's language (English/Hindi).

    ABSOLUTE RESTRICTIONS:
    - ONLY answer Cashify, gadgets, smartphones, laptops queries
    - NEVER provide advice on suicide, mental health, personal problems
    - For ANY restricted topic, respond EXACTLY: "I am a Cashify Chatbot and I can help you on query related to gadgets or queries related to cashify only"

    AVAILABLE TOOLS:
    - get_order_tracking: Order status
    - get_personal_profile: Profile/coins  
    - get_last_purchases: Purchase history
    - get_trending_product: Products
    - about_cashify: Company info
    - get_real_time_search: Gadget searches""")
        
        messages_to_send = [system_prompt] + state['messages']
        
        try:
            response = self.llm_with_tools.invoke(messages_to_send)
            
            if not hasattr(response, 'content') or not response.content:
                response.content = "I am a Cashify Chatbot and I can help you on query related to gadgets or queries related to cashify only"
            
            response_lower = response.content.lower()
            restricted_phrases = [
                'sorry to hear', 'mental health', 'helpline', 'crisis', 'professional',
                'therapy', 'counseling', 'suicide prevention', 'reach out', 'trusted person',
                'मानसिक स्वास्थ्य', 'सलाह', 'परेशान', 'दुखी'
            ]
            
            if any(phrase in response_lower for phrase in restricted_phrases):
                response.content = "I am a Cashify Chatbot and I can help you on query related to gadgets or queries related to cashify only"
            
            self.logger.info(f"Model response: {response.content[:50]}...")
            
            return {
                **state,
                "messages": [response],
                "iteration_count": current_iteration + 1
            }
            
        except Exception as e:
            self.logger.error(f"Model call error: {e}")
            return {
                **state,
                "messages": [AIMessage(content="I am a Cashify Chatbot and I can help you on query related to gadgets or queries related to cashify only")],
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
        
        tool_results = []
        for msg in state['messages']:
            if isinstance(msg, ToolMessage):
                tool_results.append(msg.content)
        
        self.logger.info(f"Answer quality check - Tool results found: {len(tool_results)}, Answer length: {len(answer)}")
        
        if tool_results and answer and len(answer.strip()) > 20:
            # Check if the answer actually uses the tool results
            if any(keyword in answer.lower() for keyword in ['order', 'status', 'tracking', 'delivery']):
                self.logger.info("Answer quality: SATISFIED (has tool results and relevant content)")
                return {**state, "answer_satisfied": True}
        
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
    
    def process_query(self, user_input: str) -> QueryResponses:
        """Process user query and return QueryResponses object"""
        state = {
            "messages": [HumanMessage(content=user_input)],
            "user_query": user_input,
            "is_valid": False,
            "iteration_count": 0,
            "global_iteration": 0,
            "answer_satisfied": False
        }
        
        try:
            logger_messages = [HumanMessage(content=user_input)]
            result = self.workflow.invoke(state)
            
            if result and result.get('messages'):
                for message in result['messages']:
                    if hasattr(message, 'content') and message.content:
                        logger_messages.append(message)
                    
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.get('name', 'unknown')
                            tool_args = tool_call.get('args', {})
                            # Create ToolMessage with proper tool_call_id
                            tool_call_id = tool_call.get('id', str(uuid.uuid4()))
                            tool_msg = ToolMessage(
                                content=f"Tool: {tool_name}, Args: {tool_args}",
                                tool_call_id=tool_call_id
                            )
                            logger_messages.append(tool_msg)
                    
                    if isinstance(message, ToolMessage):
                        logger_messages.append(message)
                
                final_msg = result['messages'][-1]
                final_response = getattr(final_msg, 'content', '')
                
                if not final_response or not final_response.strip():
                    for msg in reversed(result['messages']):
                        if isinstance(msg, ToolMessage) and msg.content:
                            final_response = f"Here's the information you requested:\n\n{msg.content}"
                            break
                    if not final_response:
                        final_response = "I couldn't retrieve the information. Please try again."
            else:
                final_response = "I encountered an issue processing your request."
                # Create ToolMessage with proper tool_call_id
                error_id = str(uuid.uuid4())
                logger_messages.append(ToolMessage(
                    content="No workflow result",
                    tool_call_id=error_id
                ))
            
            return QueryResponses(
                final_response=final_response,
                messages=logger_messages
            )
            
        except Exception as e:
            # Create ToolMessage with proper tool_call_id
            error_id = str(uuid.uuid4())
            return QueryResponses(
                final_response=f"Error processing query: {str(e)}",
                messages=[ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=error_id
                )]
            )