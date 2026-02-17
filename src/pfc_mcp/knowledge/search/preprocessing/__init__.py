"""Text preprocessing utilities for PFC search system.

This package provides text processing utilities for search, including
tokenization and stopword filtering optimized for technical documentation.
"""

from pfc_mcp.knowledge.search.preprocessing.stopwords import STOPWORDS, is_stopword
from pfc_mcp.knowledge.search.preprocessing.tokenizer import TextTokenizer

__all__ = ["TextTokenizer", "STOPWORDS", "is_stopword"]
