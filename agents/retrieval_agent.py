"""
Knowledge Retrieval Agent / Tool for HelpDesk AI.
Retrieves relevant IT Standard Operating Procedures (SOPs) and articles from the local knowledge base.
"""

from typing import List, Dict, Any
from knowledge_base import search_knowledge_base


def run_retrieval_agent(title: str, description: str, category: str = None) -> List[Dict[str, Any]]:
    """
    Retrieves the most relevant knowledge base articles based on ticket query and category hint.
    """
    query = f"{title} {description}"
    articles = search_knowledge_base(query=query, category_hint=category, top_k=2)
    return articles
