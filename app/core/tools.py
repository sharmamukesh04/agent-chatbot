import json
import os
from langchain_core.tools import tool

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

@tool 
def get_real_time_search(user_query: str) -> str:
    """Real-time search engine for any query"""
    data_dir = "/app/data"
    try:
        filepath = os.path.join(data_dir, "search_results.json")
        with open(filepath, 'r', encoding='utf-8') as f:
            search_data = json.load(f)
        return f"Search results for '{user_query}':\n" + json.dumps(search_data, indent=2)
    except Exception as e:
        return f"Error performing search: {str(e)}"

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