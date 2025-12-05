# Antigravity Ultra - Agent Tools: Web Search
import httpx
from typing import List, Dict, Any
from dataclasses import dataclass
import urllib.parse


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchTool:
    """Web search using DuckDuckGo (no API key needed)"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=30.0,
            follow_redirects=True
        )
    
    async def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Search the web using DuckDuckGo"""
        results = []
        
        try:
            # Use DuckDuckGo HTML version
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Parse results (simple parsing)
            html = response.text
            results = self._parse_results(html, num_results)
            
        except Exception as e:
            print(f"Search error: {e}")
        
        return results
    
    def _parse_results(self, html: str, num_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo HTML results"""
        results = []
        
        # Find result blocks
        import re
        
        # Extract result links and titles
        pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)
        
        # Extract snippets
        snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+(?:<b>[^<]+</b>[^<]*)*)</a>'
        snippets = re.findall(snippet_pattern, html)
        
        for i, (url, title) in enumerate(matches[:num_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            # Clean up snippet
            snippet = re.sub(r'<[^>]+>', '', snippet)
            
            results.append(SearchResult(
                title=title.strip(),
                url=url,
                snippet=snippet.strip()
            ))
        
        return results
    
    async def search_formatted(self, query: str, num_results: int = 5) -> str:
        """Search and return formatted results for LLM"""
        results = await self.search(query, num_results)
        
        if not results:
            return f"No results found for: {query}"
        
        formatted = f"Search results for: {query}\n\n"
        for i, r in enumerate(results, 1):
            formatted += f"{i}. **{r.title}**\n"
            formatted += f"   URL: {r.url}\n"
            formatted += f"   {r.snippet}\n\n"
        
        return formatted
    
    async def close(self):
        await self.client.aclose()


# Tool definition for the agent
WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": "Search the web for information. Use this when you need current information or facts you don't know.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default: 5)",
                "default": 5
            }
        },
        "required": ["query"]
    }
}
