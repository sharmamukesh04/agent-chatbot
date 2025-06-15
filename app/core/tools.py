import json
import os
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from .llm import LLMinitialize

# REMOVE the monkey-patch (causing the error)
# Just use DuckDuckGo directly without header modification

llm = LLMinitialize().get_groq_llm()

@tool
def about_cashify() -> str:
    """Get Cashify company information"""
    data_dir = "/app/data"
    try:
        filepath = os.path.join(data_dir, "about.txt")
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        try:
            filepath = os.path.join(data_dir, "company_info.json")
            with open(filepath, 'r', encoding='utf-8') as f:
                company_data = json.load(f)
                return json.dumps(company_data, indent=2)
        except Exception as e:
            return f"Error reading company info: {str(e)}"

def clean_query(text):
    """Remove thinking tags and get clean search query"""
    if '<think>' in text:
        text = text.split('</think>')[-1] if '</think>' in text else text.split('<think>')[0]
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return lines[-1] if lines else text.strip()

@tool
def get_real_time_search(user_query: str) -> str:
    """Real-time search engine for any query"""
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        
        query_generator_prompt = SystemMessage(content="""Convert to search terms. Return ONLY 2-4 words.

Examples:
"What's the price of iPhone 15?" → iPhone 15 price
"top 5 smartphones 2024" → best smartphones 2024
"weather in Delhi" → Delhi weather today

Return ONLY the search words:""")
        
        query_messages = [query_generator_prompt, HumanMessage(content=f"User question: {user_query}")]
        query_response = llm.invoke(query_messages)
        
        # Clean the response
        search_query = clean_query(query_response.content.strip())
        print(f"🔍 Generated search query: {search_query}")
        
        # Use DuckDuckGo search directly
        search = DuckDuckGoSearchRun()
        search_results = search.run(search_query)
        
        return f"Search Query: {search_query}\n\nResults: {search_results}"
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
        # Fallback to simple response
        return f"Search temporarily unavailable for: {user_query}"
    
    
@tool
def get_trending_product() -> str:
    """Get trending products"""
    data_dir = "/app/data"
    try:
        filepath = os.path.join(data_dir, "trending_products.json")
        with open(filepath, 'r', encoding='utf-8') as f:
            trending_data = json.load(f)
        
        # Format like the working Jupyter version
        result = "Available Products:\n\n📱 MOBILES:\n"
        for mobile in trending_data.get('mobiles', []):
            status = "✅ Available" if mobile.get('available', True) else "❌ Out of Stock"
            result += f"- {mobile.get('brand', 'Unknown')} {mobile.get('model', '')} ({mobile.get('storage', '')}) - ₹{mobile.get('price', 'N/A')} {status}\n"
        
        result += "\n💻 LAPTOPS:\n"
        for laptop in trending_data.get('laptops', []):
            status = "✅ Available" if laptop.get('available', True) else "❌ Out of Stock"
            result += f"- {laptop.get('brand', 'Unknown')} {laptop.get('model', '')} ({laptop.get('ram', '')}, {laptop.get('storage', '')}) - ₹{laptop.get('price', 'N/A')} {status}\n"
        
        return result
        
    except Exception as e:
        return f"Error reading trending products: {str(e)}"

@tool
def get_last_purchases() -> str:
    """Get purchase history"""
    data_dir = "/app/data"
    try:
        filepath = os.path.join(data_dir, "last_purchase.json")
        with open(filepath, 'r', encoding='utf-8') as f:
            purchases_data = json.load(f)
        
        purchases = purchases_data.get('last_purchases', [])
        result = "Recent Purchases:\n"
        for p in purchases:
            result += f"- {p.get('product_type', 'Item')}: {p.get('brand', '')} {p.get('model', '')} - ₹{p.get('amount', 'N/A')} on {p.get('purchase_date', 'Unknown date')}\n"
        
        return result
        
    except Exception as e:
        return f"Error reading purchase history: {str(e)}"

@tool
def get_order_tracking() -> str:
    """Get order status and tracking"""
    data_dir = "/app/data"
    try:
        filepath = os.path.join(data_dir, "order_tracking.json")
        with open(filepath, 'r', encoding='utf-8') as f:
            tracking_data = json.load(f)
        
        # Format like the working Jupyter version  
        product = tracking_data.get('product', {})
        agent = tracking_data.get('delivery_agent', {})
        
        result = f"Order {tracking_data.get('order_id', 'Unknown')}: "
        result += f"{product.get('brand', '')} {product.get('model', '')} "
        result += f"(₹{product.get('price', 'N/A')}) - "
        result += f"Status: {tracking_data.get('status', 'Unknown')}. "
        result += f"Delivery Agent: {agent.get('name', 'Unknown')} ({agent.get('contact', 'N/A')}). "
        result += f"Estimated Delivery: {tracking_data.get('estimated_delivery', 'TBD')}. "
        result += f"Track: {tracking_data.get('tracking_url', 'N/A')}"
        
        return result
        
    except Exception as e:
        return f"Error reading order tracking: {str(e)}"

@tool
def get_personal_profile() -> str:
    """Get user profile information"""
    data_dir = "/app/data"
    try:
        filepath = os.path.join(data_dir, "points.json")
        with open(filepath, 'r', encoding='utf-8') as f:
            profile_data = json.load(f)
        
        # Format like the working Jupyter version
        gift_cards = profile_data.get('gift_cards', [])
        cards_info = ""
        for card in gift_cards:
            cards_info += f"  - {card.get('vendor', 'Unknown')}: ₹{card.get('value', 'N/A')} (Expires: {card.get('expiry', 'Unknown')}, Status: {card.get('status', 'Unknown')})\n"
        
        result = f"Profile: {profile_data.get('name', 'Unknown')} ({profile_data.get('email', 'Unknown')})\n"
        result += f"Coins Balance: {profile_data.get('coins_balance', 'N/A')}\n"
        result += f"Gift Cards:\n{cards_info}"
        
        return result
        
    except Exception as e:
        return f"Error reading profile: {str(e)}"

AVAILABLE_TOOLS = [
    about_cashify,
    get_real_time_search, 
    get_trending_product,
    get_last_purchases,
    get_order_tracking,
    get_personal_profile
]