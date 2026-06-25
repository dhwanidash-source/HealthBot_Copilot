import json

def fetch_campaign_data() -> str:
    """Retrieves current active marketing campaigns and their discounts."""
    # In production, this would query the CAMPAIGNS SQL table
    campaigns = [
        {"campaign_id": "C1", "name": "Annual Wellness Check", "discount": "15%", "target": "inactive users"},
        {"campaign_id": "C2", "name": "Diabetes Management", "discount": "20%", "target": "high risk"}
    ]
    return json.dumps(campaigns)

def segment_user(age: int, risk_score: str, engagement_score: int) -> str:
    """Classifies the user into a marketing segment based on their profile data."""
    if risk_score.lower() in ["high", "medium"] and engagement_score < 50:
        return "Segment: High-Risk Inactive. Recommend: Re-engagement + Wellness Check."
    elif engagement_score >= 80:
        return "Segment: Highly Engaged. Recommend: Loyalty cross-sell."
    return "Segment: General Population. Recommend: Standard newsletter."


import os
from langchain_community.tools.tavily_search import TavilySearchResults

def get_tavily_search_tool(max_results: int = 7, search_depth: str = "advanced"):
    """
    Initializes and returns a Tavily Search tool wrapper.
    Expects TAVILY_API_KEY to be set in the environment variables.
    """
    
    return TavilySearchResults(max_results=max_results, search_depth=search_depth)