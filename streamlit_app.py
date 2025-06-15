# ===== FIX: Add this to the top of your streamlit_app.py =====

import sys
import os
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

# Fix threading context for Streamlit
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/app')

import streamlit as st
import io
from contextlib import redirect_stdout
import time
import traceback
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import strategies with error handling
try:
    from app.services.chatbot import CashifyChatbotService
    from app.models.state import QueryResponses
    import_strategy = "Direct import successful"
except ImportError as e:
    import requests
    CashifyChatbotService = None
    QueryResponses = None
    import_strategy = f"Using FastAPI fallback: {e}"

# Page config
st.set_page_config(page_title="Cashify AI Assistant", page_icon="🤖", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent_logs" not in st.session_state:
    st.session_state.agent_logs = []

if "processing" not in st.session_state:
    st.session_state.processing = False

if "log_container" not in st.session_state:
    st.session_state.log_container = None

# Fixed chatbot initialization
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
    """Thread-safe log capture that works with Streamlit"""
    def __init__(self, log_container):
        self.logs = []
        self.log_container = log_container
        self._lock = threading.Lock()
        
    def write(self, message):
        if message.strip():
            with self._lock:
                self.logs.append(message.strip())
            # Don't update display from background threads
            
    def flush(self):
        pass
    
    def update_display_safe(self):
        """Update display from main thread only"""
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
    """Convert different message types to display format"""
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
    """Fallback: Call FastAPI endpoint"""
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
    """Run agent in a thread-safe manner"""
    try:
        if st.session_state.chatbot:
            # Run chatbot with captured stdout
            with redirect_stdout(log_capture):
                response_obj = st.session_state.chatbot.chat(query)
            
            # Extract response
            if hasattr(response_obj, 'final_response') and hasattr(response_obj, 'messages'):
                final_response = response_obj.final_response
                
                # Log messages safely
                for i, message in enumerate(response_obj.messages):
                    try:
                        formatted_message = format_message_for_display(message)
                        log_capture.write(f"Step {i+1}: {formatted_message}")
                    except Exception as e:
                        log_capture.write(f"Step {i+1}: Error: {str(e)}")
                
                return final_response if final_response else "I couldn't generate a response."
            else:
                return str(response_obj)
        else:
            # Use FastAPI fallback
            return call_fastapi_endpoint(query)
            
    except Exception as e:
        log_capture.write(f"❌ ERROR: {str(e)}")
        logger.error(f"Agent error: {str(e)}")
        return f"Error: {str(e)}"

def run_agent_with_realtime_logs(query, log_container):
    """Main function to run agent with real-time logs"""
    log_capture = ThreadSafeLogCapture(log_container)
    
    try:
        log_capture.write(f"🔍 Processing: {query}")
        
        # Run agent in current thread (avoid threading issues)
        response = run_agent_safe(query, log_capture)
        
        # Update logs in session state
        st.session_state.agent_logs = log_capture.logs
        
        # Update display safely
        log_capture.update_display_safe()
        
        return response
        
    except Exception as e:
        error_msg = f"❌ ERROR: {str(e)}"
        log_capture.write(error_msg)
        st.session_state.agent_logs = log_capture.logs
        return f"Error: {str(e)}"

# Header
st.title("🤖 Cashify AI Assistant")
st.caption("Real LLM Agent with Decision Tracking")

# Sidebar
with st.sidebar:
    st.header("🤖 Agent Decision Steps")
    
    # Debug info
    with st.expander("🔧 Debug Info"):
        st.write(f"Import: {import_strategy}")
        st.write(f"Chatbot: {st.session_state.chatbot is not None}")
    
    # Log container
    log_placeholder = st.empty()
    st.session_state.log_container = log_placeholder
    
    # Show logs
    if st.session_state.agent_logs:
        with log_placeholder.container():
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
        with log_placeholder.container():
            st.info("Logs will appear here...")
    
    st.markdown("---")
    st.subheader("💬 Stats")
    st.metric("Messages", len(st.session_state.messages))
    st.metric("Logs", len(st.session_state.agent_logs))
    
    if st.button("🔄 Clear", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent_logs = []
        st.session_state.processing = False
        st.rerun()

# Chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything about Cashify..."):
    if not st.session_state.processing:
        st.session_state.processing = True
        
        # Clear logs
        st.session_state.agent_logs = []
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Show user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process and show response
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                response = run_agent_with_realtime_logs(prompt, st.session_state.log_container)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.session_state.processing = False