"""Search result model for PFC search system.

This module defines the structure of search results returned by search engines,
including relevance scores, ranking information, and match details for
explainability.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from pfc_mcp.docs.models.document import SearchDocument


@dataclass
class SearchResult:
    """Search result model.

    Represents a single search result with document, relevance score,
    and detailed match information for transparency and debugging.

    Attributes:
        document: The matched SearchDocument
        score: Relevance score (higher = more relevant)
            Score ranges depend on scoring algorithm:
            - Keyword: 0-1100+ (see keyword_matcher.py)
            - BM25: 0-50+ (depends on query length and IDF values)
            - Hybrid: 0-100 (normalized weighted combination)
        match_info: Detailed match information for explainability
            Common fields:
            - matching_words: List of exact matching keywords
            - partial_matches: List of (query_word, doc_word, quality) tuples
            - matched_keywords: List of matched document keywords
            - bm25_terms: Dict of {term: idf_score} for BM25 matches
        rank: Result ranking (1-based, 1 is best)
        score_breakdown: Optional detailed score components
            Example: {"keyword": 850, "bm25": 12.3, "hybrid": 79.3}

    Usage:
        >>> result = SearchResult(
        ...     document=doc,
        ...     score=85.3,
        ...     match_info={
        ...         "matching_words": ["create", "ball"],
        ...         "partial_matches": [("pos", "position", 0.8)]
        ...     },
        ...     rank=1
        ... )
        >>> result.score
        85.3
        >>> result.rank
        1
    """

    document: SearchDocument
    score: float
    match_info: Dict[str, Any]
    rank: int
    score_breakdown: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """Validate and normalize fields after initialization."""
        if self.score_breakdown is None:
            self.score_breakdown = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary representation.

        Useful for API responses, logging, and serialization.

        Returns:
            Dictionary with all result fields including document data
        """
        return {
            "document": self.document.to_dict(),
            "score": self.score,
            "match_info": self.match_info,
            "rank": self.rank,
            "score_breakdown": self.score_breakdown
        }

    def get_highlighted_title(self, highlight_tag: str = "**") -> str:
        """Generate title with matched terms highlighted.

        Args:
            highlight_tag: Tag to wrap around matched terms (default: "**" for bold in markdown)

        Returns:
            Title with matched terms highlighted

        Example:
            >>> result.match_info = {"matching_words": ["create"]}
            >>> result.document.title = "ball create"
            >>> result.get_highlighted_title()
            'ball **create**'
        """
        title = self.document.title
        matching_words = self.match_info.get("matching_words", [])

        for word in matching_words:
            # Case-insensitive replacement while preserving original case
            import re
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            title = pattern.sub(f"{highlight_tag}\\g<0>{highlight_tag}", title)

        return title

    def get_match_quality(self) -> str:
        """Get human-readable match quality description.

        Returns:
            Match quality description: "Exact", "Partial", or "Weak"

        Example:
            >>> result.score = 950
            >>> result.get_match_quality()
            'Exact'
            >>> result.score = 450
            >>> result.get_match_quality()
            'Partial'
        """
        # Heuristic based on score (adjust thresholds as needed)
        if self.score >= 800:
            return "Exact"
        elif self.score >= 400:
            return "Partial"
        else:
            return "Weak"
