from langchain_core.tools import tool
from ..utils.config import get_settings
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage, BaseMessage, HumanMessage
from langchain_community.tools import DuckDuckGoSearchRun
from .llm import LLMinitialize
import json
from ..logs.logger import Logger


class AvailableTools:

    def __init__(self):
        self.settings = get_settings()
        self.llm = LLMinitialize().get_groq_llm()
        self.logger = Logger().get_logger()
        self.tools = [
            self.about_cashify,
            self.get_real_time_search,
            self.get_trending_product,
            self.get_last_purchases,
            self.get_order_tracking,
            self.get_personal_profile
        ]

    @tool
    def get_real_time_search(self, user_query: str) -> str:
        """Real-time search engine for any query. LLM will generate appropriate search terms based on user's question."""
        try:
            # Generate search query using LLM
            query_generator_prompt = SystemMessage(content="""You are a search query generator. 

    TASK: Convert user questions into effective search queries for web search.

    RULES:
    - Keep search queries short and focused
    - Use relevant keywords only
    - Remove question words (what, how, when, where, why)
    - Make it search-engine friendly

    Examples:
    "What's the price of iPhone 15?" → "iPhone 15 price India"
    "How many employees does Google have?" → "Google number of employees 2024"
    "What is the weather in Delhi?" → "Delhi weather today"
    "Tell me about Tesla cars" → "Tesla cars features specs"

    Respond with ONLY the search query, nothing else.""")
            
            query_messages = [query_generator_prompt, HumanMessage(content=f"User question: {user_query}")]
            query_response = self.llm.invoke(query_messages)
            
            search_query = query_response.content.strip()
            print(f"🔍 Generated search query: {search_query}")
            
            # Perform the search
            search = DuckDuckGoSearchRun()
            search_results = search.run(search_query)
            
            return f"Search Query: {search_query}\n\nResults: {search_results}"
            
        except Exception as e:
            return f"Could not perform search for: {user_query}. Error: {str(e)}"

    @tool
    def about_cashify(self) -> str:
        """Get Cashify company info"""
        try:
            with open('about.txt', 'r') as f:
                return f.read()
        except Exception as e:
            self.logger.error(
                msg=f"getting an error while loading about cashify: {str(e)}"
            )
            return "Company information unavailable"

    @tool
    def get_order_tracking(self) -> str:
        """Get order status"""
        try:
            with open('order_tracking.json', 'r') as f:
                data = json.load(f)
                product = data['product']
                agent = data['delivery_agent']
                return f"Order {data['order_id']}: {product['brand']} {product['model']} (₹{product['price']}) - Status: {data['status']}. Delivery Agent: {agent['name']} ({agent['contact']}). Estimated Delivery: {data['estimated_delivery']}. Track: {data['tracking_url']}"
        except Exception as e:
            self.logger.error(
                msg=f"getting an error while loading order tracking info : {str(e)}"
            )
            return "Order tracking information unavailable"

    @tool
    def get_last_purchases(self) -> str:
        """Get purchase history"""
        try:
            with open('last_purchase.json', 'r') as f:
                data = json.load(f)
                purchases = data['last_purchases']
                result = "Recent Purchases:\n"
                for p in purchases:
                    result += f"- {p['product_type']}: {p['brand']} {p['model']} - ₹{p['amount']} on {p['purchase_date']}\n"
                return result
        except Exception as e:
            self.logger.error(
                msg=f"getting an error while loading last purchase info: {str(e)}"
            )
            return "Purchase history unavailable"

    @tool 
    def get_personal_profile(self) -> str:
        """Get user profile"""
        try:
            with open('points.json', 'r') as f:
                data = json.load(f)
                gift_cards = data.get('gift_cards', [])
                cards_info = ""
                for card in gift_cards:
                    cards_info += f"  - {card['vendor']}: ₹{card['value']} (Expires: {card['expiry']}, Status: {card['status']})\n"
                
                return f"Profile: {data['name']} ({data['email']})\nCoins Balance: {data['coins_balance']}\nGift Cards:\n{cards_info}"
        except Exception as e:
            self.logger.error(
                msg=f"getting an error while loading personal info: {str(e)}"
            )
            return "Profile information unavailable"

    @tool 
    def get_trending_product(self) -> str:
        """Get trending products on Cashify"""
        try:
            with open('trending_products.json', 'r') as f:
                data = json.load(f)
                result = "Available Products:\n\n📱 MOBILES:\n"
                for mobile in data.get('mobiles', []):
                    status = "✅ Available" if mobile['available'] else "❌ Out of Stock"
                    result += f"- {mobile['brand']} {mobile['model']} ({mobile['storage']}) - ₹{mobile['price']} {status}\n"
                
                result += "\n💻 LAPTOPS:\n"
                for laptop in data.get('laptops', []):
                    status = "✅ Available" if laptop['available'] else "❌ Out of Stock"
                    result += f"- {laptop['brand']} {laptop['model']} ({laptop['ram']}, {laptop['storage']}) - ₹{laptop['price']} {status}\n"
                
                return result
        except Exception as e:
            self.logger.error(
                msg=f"getting an error while loading trending products: {str(e)}"
            )
            return "Product catalog unavailable"
    
    # def get_all_tools(self):
    #     tools = [
    #         self.about_cashify,
    #         self.get_real_time_search,
    #         self.get_trending_product,
    #         self.get_last_purchases,
    #         self.get_order_tracking,
    #         self.get_personal_profile
    #     ]

    #     return tools

