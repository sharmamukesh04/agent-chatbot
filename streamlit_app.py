import streamlit as st
import requests
import time
import json

# Page config
st.set_page_config(
    page_title="Cashify AI Assistant",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I assist you today? Whether it's about your order, profile, purchases, or anything else, feel free to ask!"}
    ]

if "tool_activities" not in st.session_state:
    st.session_state.tool_activities = []

if "processing" not in st.session_state:
    st.session_state.processing = False

if "use_real_api" not in st.session_state:
    st.session_state.use_real_api = True

# Custom CSS
st.markdown("""
<style>
    .tool-activity {
        background-color: #f0f2f6;
        padding: 12px;
        border-radius: 8px;
        margin: 8px 0;
        border-left: 4px solid #1f77b4;
    }
    .tool-thinking { border-left-color: #ff9800; background-color: #fff3e0; }
    .tool-completed { border-left-color: #4caf50; background-color: #e8f5e9; }
    .status-dot { 
        display: inline-block; 
        width: 8px; 
        height: 8px; 
        border-radius: 50%; 
        margin-right: 8px; 
    }
    .thinking { background-color: #ff9800; animation: pulse 1s infinite; }
    .completed { background-color: #4caf50; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
</style>
""", unsafe_allow_html=True)

def get_api_response(query):
    """Get response from FastAPI backend"""
    api_urls = [
        "http://api:8000/chat", 
        "http://localhost:8080/chat", 
        "http://127.0.0.1:8080/chat", 
    ]
    
    for url in api_urls:
        try:
            response = requests.post(
                url,
                json={"message": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "Sorry, I couldn't process your request."), True
                
        except requests.exceptions.RequestException:
            continue
    
    return "Sorry There is something Wrong", False

def display_tool_activities():
    """Display tool activities"""
    if st.session_state.tool_activities:
        for activity in st.session_state.tool_activities:
            status_text = "Processing..." if activity["status"] == "thinking" else "Completed"
            dot_class = activity["status"]
            
            st.markdown(f"""
            <div class="tool-activity tool-{activity['status']}">
                <div style="font-weight: bold;">
                    <span class="status-dot {dot_class}"></span>
                    {activity['tool']}
                </div>
                <div style="font-size: 0.9em; color: #666; margin-top: 4px;">
                    {status_text}
                </div>
                {f'<div style="font-size: 0.8em; color: #888; margin-top: 4px;">{activity["description"]}</div>' if activity["description"] else ''}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Tool activities will appear here when you send a message")

# Header
st.title("🤖 Cashify AI Assistant")
st.caption("Your intelligent customer service companion")

# with st.sidebar:
#     st.header("🔧 Tool Activity")
#     display_tool_activities()
    
#     st.markdown("---")
    
#     # API Status indicator
#     if st.session_state.use_real_api:
#         st.success("🟢 **Connected to Real API**")
#     else:
#         st.warning("🟡 **Using Mock Data** (API unavailable)")
    
#     if st.button("🔄 Clear Chat", key="clear_chat_button"):
#         st.session_state.messages = [
#             {"role": "assistant", "content": "Hello! How can I assist you today?"}
#         ]
#         st.session_state.tool_activities = []
#         st.session_state.processing = False
#         st.rerun()

# # Display messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    if not st.session_state.processing:
        st.session_state.processing = True
        
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Show user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process with tool simulation
        with st.chat_message("assistant"):
            # Show progress
            progress_placeholder = st.empty()
            
            with progress_placeholder:
                st.info("🔍 Validating query...")
                st.session_state.tool_activities = [{"tool": "Query Validator", "status": "thinking", "description": "Analyzing your request..."}]
            time.sleep(0.5)
            
            with progress_placeholder:
                st.info("⚙️ Processing query...")
                st.session_state.tool_activities = [
                    {"tool": "Query Validator", "status": "completed", "description": "Query validated"},
                    {"tool": "Query Processor", "status": "thinking", "description": "Determining action..."}
                ]
            time.sleep(0.5)

            tool_name, tool_desc = get_tool_info(prompt)
            with progress_placeholder:
                st.info(f"🔧 Executing {tool_name}...")
                st.session_state.tool_activities = [
                    {"tool": "Query Validator", "status": "completed", "description": "Query validated"},
                    {"tool": "Query Processor", "status": "completed", "description": "Action determined"},
                    {"tool": tool_name, "status": "thinking", "description": tool_desc}
                ]
            time.sleep(0.8)
            
            with progress_placeholder:
                st.info("✨ Generating response...")
                st.session_state.tool_activities = [
                    {"tool": "Query Validator", "status": "completed", "description": "Query validated"},
                    {"tool": "Query Processor", "status": "completed", "description": "Action determined"},
                    {"tool": tool_name, "status": "completed", "description": "Data retrieved"},
                    {"tool": "Response Generator", "status": "thinking", "description": "Crafting response..."}
                ]
            time.sleep(0.3)
            
            # Get response (try real API first, fallback to mock)
            assistant_response, is_real_api = get_api_response(prompt)
            st.session_state.use_real_api = is_real_api
            
            # Final update
            st.session_state.tool_activities = [
                {"tool": "Query Validator", "status": "completed", "description": "Query validated"},
                {"tool": "Query Processor", "status": "completed", "description": "Action determined"},
                {"tool": tool_name, "status": "completed", "description": "Data retrieved"},
                {"tool": "Response Generator", "status": "completed", "description": "Response ready"}
            ]
            
            # Clear progress and show response
            progress_placeholder.empty()
            st.markdown(assistant_response)
            
            # Add to session state
            st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        
        # Reset processing flag
        st.session_state.processing = False