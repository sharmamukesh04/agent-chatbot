from langchain_core.messages import SystemMessage, HumanMessage
from typing import List


class QueryValidator:
    """Validates user queries for safety and appropriateness"""
    
    def __init__(self, llm):
        self.llm = llm
        self.harmful_keywords = [
            'hack', 'exploit', 'illegal', 'violence', 'bomb', 'weapon',
            'emergency', 'crisis', 'suicide', 'police', '911', 'password'
        ]
    
    def validate_query(self, user_query: str) -> bool:
        """Validate user query for safety and appropriateness"""
        
        # Quick keyword check
        if any(keyword in user_query.lower() for keyword in self.harmful_keywords):
            return False
        
        # LLM validation
        try:
            prompt = SystemMessage(content="""Validate this query for Cashify customer service.
            
ACCEPT: orders, products, pricing, profile, company info, general searches
REJECT: harmful, illegal, inappropriate, emergency content

Respond ONLY: "VALID" or "INVALID" """)
            
            response = self.llm.invoke([prompt, HumanMessage(content=f"Query: {user_query}")])
            return "VALID" in response.content.upper()
            
        except:
            return False
    
    def is_response_safe(self, content: str) -> bool:
        """Check response for inappropriate content"""
        unsafe_terms = ['emergency', '911', 'crisis', 'suicide', 'police']
        return not any(term in content.lower() for term in unsafe_terms)