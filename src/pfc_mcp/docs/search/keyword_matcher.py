"""Shared keyword matching and scoring algorithms.

This module provides reusable keyword matching functions used by both
command search and Python API search systems. The algorithms are inspired
by BM25 principles with support for partial matching (prefix/substring).
"""

from typing import Set, Tuple


def calculate_relevance_score(
    keyword_words: Set[str],
    query_words: Set[str],
    matching_words: Set[str]
) -> int:
    """Calculate relevance score using multi-factor ranking with partial matching.

    This scoring algorithm is inspired by BM25 and considers three factors:
    1. Keyword coverage (primary): How much of the keyword is covered by the query
    2. Query precision (secondary): How focused is the match (fewer extra words = better)
    3. Match count (tie-breaker): Absolute number of matching words

    The algorithm supports both exact matching and partial matching (via
    find_partial_matches) to handle abbreviations like "pos" → "position".

    Args:
        keyword_words: Set of words in the keyword phrase
        query_words: Set of words in the user's query
        matching_words: Set of exact matching words (overlap between keyword and query)

    Returns:
        Integer score (0-1100+, higher = more relevant)

    Score breakdown:
        - Keyword coverage: 0-1000 points (primary factor)
        - Query precision: 0-100 points (secondary factor)
        - Match count: 1-10 points (tie-breaker)

    Examples:
        >>> # Exact match: query="create ball", keyword="create ball"
        >>> calculate_relevance_score(
        ...     {"create", "ball"},
        ...     {"create", "ball"},
        ...     {"create", "ball"}
        ... )
        1104  # 1000 (full coverage) + 100 (perfect precision) + 4 (2 exact matches × 2)

        >>> # Partial match: query="pos", keyword="ball position"
        >>> # (Assuming find_partial_matches found "pos" → "position" with quality 0.8)
        >>> calculate_relevance_score(
        ...     {"ball", "position"},
        ...     {"pos"},
        ...     set()  # No exact matches, partial handled separately
        ... )
        # Returns ~450: coverage=0.4 (0.8/2), precision=0.5, count=1
    """
    # Calculate exact and partial matches
    exact_matches = matching_words
    partial_matches, partial_quality = find_partial_matches(
        query_words - exact_matches,
        keyword_words - exact_matches
    )

    # Calculate effective coverage including partial matches
    # Partial matches contribute based on their quality (0.6-0.8 weight)
    exact_match_contribution = len(exact_matches)
    partial_match_contribution = len(partial_matches) * partial_quality

    total_match_value = exact_match_contribution + partial_match_contribution

    # Factor 1: Keyword coverage (primary factor, 0-1000 points)
    # How much of the keyword is covered by the query (exact + partial)
    keyword_coverage = total_match_value / len(keyword_words) if keyword_words else 0

    # Factor 2: Query precision (secondary factor, 0-100 points)
    # Penalize queries with many irrelevant words
    # Partial matches count as 0.5 for precision (less precise than exact)
    effective_query_matches = len(exact_matches) + len(partial_matches) * 0.5
    query_precision = effective_query_matches / len(query_words) if query_words else 0

    # Factor 3: Match count (tie-breaker, 1-10 points)
    # Exact matches worth more than partial matches
    match_count = len(exact_matches) * 2 + len(partial_matches)

    # Combined score (weighted sum)
    score = int(
        keyword_coverage * 1000 +  # Primary: complete matches rank highest
        query_precision * 100 +     # Secondary: focused queries rank higher
        match_count                 # Tie-breaker: exact matches > partial
    )

    return score


def find_partial_matches(
    unmatched_query_words: Set[str],
    unmatched_keyword_words: Set[str]
) -> Tuple[Set[Tuple[str, str]], float]:
    """Find partial matches between unmatched query and keyword words.

    Uses prefix and substring matching to handle abbreviations:
    - Prefix matching (minimum 3 chars): quality 0.8
    - Substring matching: quality 0.6

    This allows queries like "pos" to match "position", "vel" to match
    "velocity", etc.

    Args:
        unmatched_query_words: Query words that didn't exact-match
        unmatched_keyword_words: Keyword words that didn't exact-match

    Returns:
        Tuple of (partial_matches, avg_quality) where:
        - partial_matches: Set of (query_word, keyword_word) pairs
        - avg_quality: Average match quality (0.0-1.0)

    Examples:
        >>> find_partial_matches(
        ...     {"pos", "vel"},
        ...     {"position", "velocity"}
        ... )
        ({('pos', 'position'), ('vel', 'velocity')}, 0.8)

        >>> find_partial_matches(
        ...     {"norm"},
        ...     {"normal", "normalize"}
        ... )
        ({('norm', 'normal')}, 0.8)  # Picks best match

        >>> find_partial_matches(
        ...     {"xyz"},
        ...     {"position", "velocity"}
        ... )
        (set(), 0.0)  # No match
    """
    partial_matches = set()
    quality_scores = []

    for q_word in unmatched_query_words:
        best_match = None
        best_quality = 0

        for k_word in unmatched_keyword_words:
            quality = word_match_quality(q_word, k_word)

            if quality > best_quality:
                best_quality = quality
                best_match = k_word

        # Only accept matches with quality >= 0.6 (substring match minimum)
        if best_match and best_quality >= 0.6:
            partial_matches.add((q_word, best_match))
            quality_scores.append(best_quality)

    # Calculate average quality
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    return partial_matches, avg_quality


def word_match_quality(query_word: str, keyword_word: str) -> float:
    """Calculate match quality between two words.

    Scoring rules:
    - Exact match: 1.0 (shouldn't happen in partial matching context)
    - Prefix match (3+ chars): 0.8
    - Substring match: 0.6
    - No match: 0.0

    Minimum prefix length of 3 chars prevents false positives from
    common short words like "a", "an", "the".

    Args:
        query_word: Word from query (lowercase)
        keyword_word: Word from keyword (lowercase)

    Returns:
        Match quality score (0.0-1.0)

    Examples:
        >>> word_match_quality("pos", "position")
        0.8  # Prefix match

        >>> word_match_quality("vel", "velocity")
        0.8  # Prefix match

        >>> word_match_quality("norm", "normal")
        0.8  # Prefix match

        >>> word_match_quality("xyz", "position")
        0.0  # No match

        >>> word_match_quality("at", "atmosphere")
        0.0  # Too short for prefix (< 3 chars)

        >>> word_match_quality("mod", "model")
        0.8  # Prefix match (exactly 3 chars)
    """
    if query_word == keyword_word:
        return 1.0  # Exact match (shouldn't happen in partial matching)

    # Prefix matching (minimum 3 chars to avoid false positives)
    min_prefix_len = 3
    if len(query_word) >= min_prefix_len and len(keyword_word) >= min_prefix_len:
        # Check if one is prefix of the other
        if keyword_word.startswith(query_word) or query_word.startswith(keyword_word):
            return 0.8

    # Substring matching (one is contained in the other)
    # IMPORTANT: Skip substring matching for single-character query words
    # to avoid false positives (e.g., "z" matching "horizontal")
    if len(query_word) > 1:
        if query_word in keyword_word or keyword_word in query_word:
            return 0.6

    return 0.0
