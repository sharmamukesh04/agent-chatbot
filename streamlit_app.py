import sys
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

import streamlit as st
import io
from contextlib import redirect_stdout
import time
import traceback
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from app.services.chatbot import CashifyChatbotService
    from app.models.state import QueryResponses
    import_strategy = "Direct import successful"
except ImportError as e:
    import requests
    CashifyChatbotService = None
    QueryResponses = None
    import_strategy = f"Using FastAPI fallback: {e}"

st.set_page_config(page_title="Cashify AI Assistant", page_icon="🤖", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []

if "processing" not in st.session_state:
    st.session_state.processing = False

if "log_container" not in st.session_state:
    st.session_state.log_container = None

if "chatbot" not in st.session_state:
    try:
        if CashifyChatbotService:
            st.session_state.chatbot = CashifyChatbotService()
            logger.info("✅ Streamlit chatbot initialized successfully")
        else:
            st.session_state.chatbot = None
    except Exception as e:
        logger.error(f"❌ Failed to initialize chatbot: {str(e)}")
        st.session_state.chatbot = None

class ThreadSafeLogCapture:
    def __init__(self, log_container):
        self.logs = []
        self.log_container = log_container
        self._lock = threading.Lock()
        
    def write(self, message):
        if message.strip():
            with self._lock:
                self.logs.append(message.strip())
            
    def flush(self):
        pass
    
    def update_display_safe(self):
        try:
            if self.log_container and self.logs:
                with self.log_container.container():
                    for log in self.logs[-20:]:
                        log = str(log).strip()
                        if not log:
                            continue
                        
                        if "🤖 Processing query" in log:
                            st.info(f"📝 {log}")
                        elif "🔄 AI thinking" in log:
                            st.success(f"🚀 {log}")
                        elif "🔧 Calling tool" in log:
                            st.warning(f"🛠️ {log}")
                        elif "Step" in log:
                            st.code(log, language=None)
                        elif "❌ ERROR" in log:
                            st.error(f"⚠️ {log}")
                        else:
                            st.text(log)
        except Exception as e:
            logger.error(f"Display update error: {e}")

def format_message_for_display(message) -> str:
    if isinstance(message, str):
        return message
    
    if hasattr(message, 'content'):
        message_type = type(message).__name__
        content = getattr(message, 'content', '')
        
        if 'HumanMessage' in message_type:
            return f"🤖 USER: {content}"
        elif 'AIMessage' in message_type:
            return f"💬 AI: {content[:100]}..." if len(content) > 100 else f"💬 AI: {content}"
        elif 'ToolMessage' in message_type:
            return f"🔧 Tool: {content[:100]}..." if len(content) > 100 else f"🔧 Tool: {content}"
        else:
            return f"📋 {message_type}: {content}"
    
    return str(message)

def call_fastapi_endpoint(message: str) -> str:
    try:
        api_urls = [
            "http://api:8000/chat",
            "http://localhost:8080/chat",
            "http://127.0.0.1:8080/chat"
        ]
        
        for url in api_urls:
            try:
                response = requests.post(
                    url,
                    json={"message": message},
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json()["response"]
            except requests.exceptions.RequestException:
                continue
        
        return "❌ Could not connect to FastAPI service"
        
    except Exception as e:
        return f"❌ API call error: {str(e)}"

def run_agent_safe(query, log_capture):
    try:
        if st.session_state.chatbot:
            log_capture.write(f"👤 HUMAN: {query}")
            log_capture.write(f"🔄 AI thinking and processing...")
            
            response_obj = st.session_state.chatbot.chat(query)
            
            if hasattr(response_obj, 'final_response') and hasattr(response_obj, 'messages'):
                final_response = response_obj.final_response
                
                # Use the messages from QueryResponses which contains all workflow messages
                for i, message in enumerate(response_obj.messages):
                    try:
                        message_type = type(message).__name__
                        content = getattr(message, 'content', '')
                        
                        if 'HumanMessage' in message_type:
                            log_capture.write(f"👤 HUMAN: {content}")
                        elif 'AIMessage' in message_type:
                            if hasattr(message, 'tool_calls') and message.tool_calls:
                                log_capture.write(f"🤖 AI: {content[:100]}..." if len(content) > 100 else f"🤖 AI: {content}")
                                for tool_call in message.tool_calls:
                                    tool_name = tool_call.get('name', 'unknown')
                                    tool_args = tool_call.get('args', {})
                                    log_capture.write(f"⚡ CALLING TOOL: {tool_name} with args: {tool_args}")
                            else:
                                log_capture.write(f"🤖 AI: {content[:100]}..." if len(content) > 100 else f"🤖 AI: {content}")
                        elif 'ToolMessage' in message_type:
                            if content.startswith("Tool:"):
                                log_capture.write(f"🔧 {content}")
                            else:
                                log_capture.write(f"🔧 TOOL RESULT: {content[:100]}..." if len(content) > 100 else f"🔧 TOOL RESULT: {content}")
                        else:
                            log_capture.write(f"📋 {message_type}: {content[:100]}..." if len(content) > 100 else f"📋 {message_type}: {content}")
                            
                    except Exception as e:
                        log_capture.write(f"❌ Error processing message {i}: {str(e)}")
                
                log_capture.write(f"✅ FINAL: {final_response[:100]}..." if len(final_response) > 100 else f"✅ FINAL: {final_response}")
                return final_response if final_response else "I couldn't generate a response."
            else:
                return str(response_obj)
        else:
            return call_fastapi_endpoint(query)
            
    except Exception as e:
        log_capture.write(f"❌ ERROR: {str(e)}")
        logger.error(f"Agent error: {str(e)}")
        return f"Error: {str(e)}"

def run_agent_with_realtime_logs(query, log_container):
    log_capture = ThreadSafeLogCapture(log_container)
    
    try:
        log_capture.write(f"🔍 Processing: {query}")
        
        response = run_agent_safe(query, log_capture)
        
        st.session_state.agent_logs = log_capture.logs
        
        log_capture.update_display_safe()
        
        return response
        
    except Exception as e:
        error_msg = f"❌ ERROR: {str(e)}"
        log_capture.write(error_msg)
        st.session_state.agent_logs = log_capture.logs
        return f"Error: {str(e)}"

st.title("🤖 Cashify AI Assistant")
st.caption("Agent with Decision Tracking")

with st.sidebar:
    st.header("🤖 Agent Decision Steps")
    
    with st.expander("🔧 Debug Info"):
        st.write(f"Import: {import_strategy}")
        st.write(f"Chatbot: {st.session_state.chatbot is not None}")
    
    with st.expander("📜 Chat History (Last 5)"):
        if st.session_state.chatbot:
            try:
                history = st.session_state.chatbot.get_chat_history()
                if history:
                    for i, chat in enumerate(history):
                        st.text(f"💬 Chat {i+1}: {chat['user'][:30]}...")
                        st.caption(f"🤖 {chat['bot'][:50]}...")
                        st.caption(f"🕒 {chat['timestamp'][:19]}")
                        st.divider()
                else:
                    st.info("No chat history yet")
            except Exception as e:
                st.error(f"History error: {e}")
    
    log_placeholder = st.empty()
    st.session_state.log_container = log_placeholder
    
    with log_placeholder.container():
        if st.session_state.agent_logs:
            for log in st.session_state.agent_logs[-15:]:
                log = str(log).strip()
                if not log:
                    continue
                if "🔍 Processing" in log:
                    st.info(f"📝 {log}")
                elif "Step" in log:
                    st.code(log, language=None)
                elif "❌ ERROR" in log:
                    st.error(f"⚠️ {log}")
                else:
                    st.text(log)
        else:
            st.info("Logs will appear here...")
    
    st.markdown("---")
    st.subheader("💬 Stats")
    st.metric("Messages", len(st.session_state.messages))
    st.metric("Logs", len(st.session_state.agent_logs))
    
    # ADD: Exit and Clear buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Clear", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_logs = []
            st.session_state.processing = False
            st.rerun()
    
    with col2:
        if st.button("🚪 Exit", use_container_width=True, type="primary"):
            if st.session_state.chatbot:
                st.session_state.chatbot.clear_chat_history()
            st.session_state.messages = []
            st.session_state.agent_logs = []
            st.session_state.processing = False
            st.success("✅ Chat history cleared!")
            st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask me anything ..."):
    if not st.session_state.processing:
        st.session_state.processing = True
        
        st.session_state.agent_logs = []
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                response = run_agent_with_realtime_logs(prompt, st.session_state.log_container)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.session_state.processing = False