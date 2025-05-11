from typing import Any, List, Dict, Optional, Type, Union, Callable
from duckduckgo_search import DDGS
from mediapipe.tasks import python
from mediapipe.tasks.python import text
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional
import time
from importlib.resources import files

class MCPRag:
    @staticmethod
    def analyze_dependencies() -> Dict[str, bool]:
        """
        rag
        """
        dependencies = {
            "mcprag": True
        }
        
        return dependencies

    @staticmethod
    def __control__() -> bool:
        return True
    

    def search(self, query: str, num_results:int=10, top_k:int=5) -> str:
        """
        Search the web for a given query. Give back context to the LLM
        with a RAG-like similarity sort.

        Args:
            query (str): The query to search for.
            num_results (int): Number of results to return.
            top_k (int): Use top "k" results for content.

        Returns:
            Dict of strings containing best search based on input query. Formatted in markdown.
        """
        ddgs = DDGS()
        results = ddgs.text(query, max_results=num_results) 
        scored_results = self._sort_by_score(self._add_score_to_dict(query, results))
        top_results = scored_results[0:top_k]

        # fetch content using thread pool
        md_content = self._fetch_all_content(top_results)

        # formatted as dict
        return md_content

    def _add_score_to_dict(self, query: str, results: List[Dict]) -> List[Dict]:
        """Add similarity scores to search results."""
        PATH = files('mcp_local_rag').joinpath('embedder/embedder.tflite')
        base_options = python.BaseOptions(model_asset_path=PATH)
        l2_normalize, quantize = True, False
        options = text.TextEmbedderOptions(
            base_options=base_options, l2_normalize=l2_normalize, quantize=quantize)
        embedder = text.TextEmbedder.create_from_options(options)
        query_embedding = embedder.embed(query)

        for i in results:
            i['score'] = text.TextEmbedder.cosine_similarity(
                            embedder.embed(i['body']).embeddings[0],
                            query_embedding.embeddings[0])

        return results

    def _sort_by_score(self, results: List[Dict]) -> List[Dict]:
        """Sort results by similarity score."""
        return sorted(results, key=lambda x: x['score'], reverse=True)

    def _fetch_content(self, url: str, timeout: int = 5) -> Optional[str]:
        """Fetch content from a URL with timeout."""
        try:
            start_time = time.time()
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            content = BeautifulSoup(response.text, "html.parser").get_text()
            print(f"Fetched {url} in {time.time() - start_time:.2f}s")
            return content[:10000]  # limitting content to 10k
        except requests.RequestException as e:
            print(f"Error fetching {url}: {type(e).__name__} - {str(e)}")
            return None

    def _fetch_all_content(self, results: List[Dict]) -> List[str]:
        """Fetch content from all URLs using a thread pool."""
        urls = [site['href'] for site in results if site.get('href')]
        
        # parallelize requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            # submit fetch tasks to executor
            future_to_url = {executor.submit(self._fetch_content, url): url for url in urls}
            
            content_list = []
            for future in future_to_url:
                try:
                    content = future.result()
                    if content:
                        content_list.append({
                            "type": "text",
                            "text": content
                        })
                except Exception as e:
                    print(f"Request failed with exception: {e}")
            
        return content_list
