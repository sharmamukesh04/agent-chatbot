import streamlit as st
from app.services.chatbot import CashifyChatbotService

# Page config
st.set_page_config(
    page_title="Cashify AI Assistant", 
    page_icon="🤖", 
    layout="wide"
)

# Initialize chatbot
@st.cache_resource
def get_chatbot():
    return CashifyChatbotService()

# Main layout
col1, col2 = st.columns([1, 2])

# Left sidebar - Simple workflow info
with col1:
    st.header("🔄 Workflow Status")
    
    if "current_step" in st.session_state:
        st.success(f"Current: {st.session_state.current_step}")
    else:
        st.info("Ready for queries")
    
    st.divider()
    
    st.subheader("📋 Available Tools")
    tools = [
        "📊 Order Tracking",
        "🛍️ Trending Products", 
        "👤 Personal Profile",
        "📖 About Cashify",
        "🔍 Real-time Search",
        "📦 Last Purchases"
    ]
    
    for tool in tools:
        st.text(tool)

# Right side - Chat Interface
with col2:
    st.title("🤖 Cashify AI Assistant")
    st.markdown("*Your intelligent customer service companion*")
    
    # Initialize chatbot and chat history
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = get_chatbot()
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input - OUTSIDE columns to avoid restrictions
if prompt := st.chat_input("How can I help you today?"):
    # Update workflow status
    st.session_state.current_step = "Processing query..."
    
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Get bot response
    try:
        response = st.session_state.chatbot.chat(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.current_step = "Response completed"
        
    except Exception as e:
        error_response = f"Sorry, I encountered an error: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": error_response})
        st.session_state.current_step = "Error occurred"

# Bottom stats
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Messages", len(st.session_state.messages))

with col2:
    user_messages = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("User Queries", user_messages)

with col3:
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        if "current_step" in st.session_state:
            del st.session_state.current_step