"""Text tokenization for PFC search system.

This module provides tokenization functionality optimized for technical
documentation, handling special cases like hyphenated terms, numbers,
and technical abbreviations.
"""

import re

from pfc_mcp.knowledge.search.preprocessing.stopwords import is_stopword


class TextTokenizer:
    """Tokenizer for technical documentation text.

    Features:
    - Preserves technical terms and numbers
    - Handles hyphenated terms (e.g., "ball-ball" → ["ball", "ball"])
    - Handles underscored terms (e.g., "vel_x" → ["vel", "x"])
    - Smart dot splitting for API paths vs. decimals
    - Removes stopwords while preserving technical vocabulary
    - Lowercases for consistent matching

    Design:
    - Regex-based for performance
    - No stemming (preserves exact technical terms)
    - No lemmatization (not needed for partial matching)
    - CamelCase splitting for better term matching
    - Splits on hyphens, underscores, dots, and CamelCase boundaries

    Usage:
        >>> tokenizer = TextTokenizer()
        >>> tokenizer.tokenize("Create ball with radius 1.5")
        ['create', 'ball', 'radius', '1.5']

        >>> tokenizer.tokenize("Ball.vel velocity")
        ['ball', 'vel', 'velocity']

        >>> tokenizer.tokenize("itasca.ball.Ball.vel")
        ['itasca', 'ball', 'ball', 'vel']

        >>> tokenizer.tokenize("ball-ball contact model")
        ['ball', 'ball', 'contact', 'model']

        >>> tokenizer.tokenize("velocity vel_x component")
        ['velocity', 'vel', 'x', 'component']

        >>> tokenizer.tokenize("BallBallContact")
        ['ball', 'ball', 'contact']

        >>> tokenizer.tokenize("IterMechanical system")
        ['iter', 'mechanical', 'system']
    """

    # Regex pattern for word extraction
    # Matches: alphanumeric + hyphens + underscores + dots (for numbers)
    WORD_PATTERN = re.compile(r"\b[\w.-]+\b")

    # Pattern for numeric values (decimals, scientific notation)
    # Examples: 1.5, 0.001, .5, 1e-5, 2.5e10, -1.5e+20
    NUMERIC_PATTERN = re.compile(
        r"^"
        r"[+-]?"  # Optional sign
        r"(?:"
        r"\d+\.?\d*"  # Integer or decimal (1, 1., 1.5)
        r"|"
        r"\.\d+"  # Decimal starting with dot (.5)
        r")"
        r"(?:[eE][+-]?\d+)?"  # Optional scientific notation
        r"$"
    )

    # Minimum word length (avoid single-char noise)
    MIN_WORD_LENGTH = 2

    # Technical single-character tokens that should be preserved
    # These are common in scientific/engineering contexts
    TECHNICAL_SINGLE_CHARS = {"x", "y", "z", "r", "n", "t"}  # Coordinates, radius, normal, tangent

    def __init__(self, remove_stopwords: bool = True, min_length: int = 2):
        """Initialize tokenizer.

        Args:
            remove_stopwords: Whether to filter out stopwords
            min_length: Minimum word length to keep (default: 2)
        """
        self.remove_stopwords = remove_stopwords
        self.min_length = min_length

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into words.

        Args:
            text: Input text to tokenize

        Returns:
            List of tokens (lowercase, filtered)

        Example:
            >>> tokenizer = TextTokenizer()
            >>> tokenizer.tokenize("Distribute balls with overlaps")
            ['distribute', 'balls', 'overlaps']

            >>> tokenizer.tokenize("2D simulation with PFC")
            ['2d', 'simulation', 'pfc']

            >>> tokenizer.tokenize("ball-ball contact")
            ['ball', 'ball', 'contact']
        """
        if not text:
            return []

        # 1. Extract words BEFORE lowercasing (to preserve CamelCase info)
        original_words = self.WORD_PATTERN.findall(text)

        # 2. Create lowercase version for matching
        text_lower = text.lower()
        lowercase_words = self.WORD_PATTERN.findall(text_lower)

        # 3. Process each word (preserve original for CamelCase detection)
        tokens = []
        for original_word, word in zip(original_words, lowercase_words):
            # Handle dotted terms (smart split: API paths vs. decimals)
            # Context: API paths like "itasca.ball.Ball.vel" vs. decimals like "1.5"
            if "." in word:
                # Check if it's a numeric value (decimal or scientific notation)
                if self.NUMERIC_PATTERN.match(word):
                    # Numeric value - keep intact
                    if self._is_valid_token(word, from_technical_context=False):
                        tokens.append(word)
                else:
                    # API path - split on dots
                    # "itasca.ball.Ball.vel" → ["itasca", "ball", "ball", "vel"]
                    # Split both original and lowercase to preserve CamelCase info
                    original_parts = original_word.split(".")
                    lowercase_parts = word.split(".")
                    for original_part, part in zip(original_parts, lowercase_parts):
                        # Process each path component (may contain underscores)
                        if "_" in part:
                            # Handle underscores within path components
                            # "force_global" → ["force", "global"]
                            subparts = part.split("_")
                            for subpart in subparts:
                                if self._is_valid_token(subpart, from_technical_context=True):
                                    tokens.append(subpart)
                        elif "-" in part:
                            # Handle hyphens within path components
                            # "ball-ball" → ["ball", "ball"]
                            subparts = part.split("-")
                            for subpart in subparts:
                                if self._is_valid_token(subpart, from_technical_context=True):
                                    tokens.append(subpart)
                        else:
                            # Simple path component - check for CamelCase
                            # Example: "Ball" in "itasca.ball.Ball.vel"
                            camel_parts = self._split_camel_case(original_part)
                            for camel_part in camel_parts:
                                if self._is_valid_token(camel_part, from_technical_context=True):
                                    tokens.append(camel_part)
            # Handle hyphenated terms (split and keep parts)
            # Context: technical compound terms like "ball-ball"
            elif "-" in word:
                parts = word.split("-")
                for part in parts:
                    # In hyphenated context, preserve technical single chars
                    if self._is_valid_token(part, from_technical_context=True):
                        tokens.append(part)
            # Handle underscored terms (e.g., "vel_x", "set_pos", "end_1")
            # Split to improve matching: "vel_x" → ["vel", "x"]
            # Context: API naming conventions with direction/index suffixes
            elif "_" in word:
                parts = word.split("_")
                for part in parts:
                    # In underscore context, preserve technical single chars
                    if self._is_valid_token(part, from_technical_context=True):
                        tokens.append(part)
            else:
                # Check if original word is CamelCase and split it
                # Example: "BallBallContact" → ["ball", "ball", "contact"]
                # Use original_word to preserve CamelCase info
                camel_parts = self._split_camel_case(original_word)

                for part in camel_parts:
                    if self._is_valid_token(part, from_technical_context=False):
                        tokens.append(part)

        return tokens

    def tokenize_to_set(self, text: str) -> set[str]:
        """Tokenize text into a set of unique words.

        Useful for matching operations where duplicates don't matter.

        Args:
            text: Input text to tokenize

        Returns:
            Set of unique tokens

        Example:
            >>> tokenizer = TextTokenizer()
            >>> tokenizer.tokenize_to_set("ball ball contact")
            {'ball', 'contact'}
        """
        return set(self.tokenize(text))

    def _split_camel_case(self, word: str) -> list[str]:
        """Split CamelCase word into components.

        Args:
            word: Word to split (e.g., "BallBallContact", "IterMechanical")

        Returns:
            List of lowercase components

        Example:
            >>> self._split_camel_case("BallBallContact")
            ['ball', 'ball', 'contact']
            >>> self._split_camel_case("IterMechanical")
            ['iter', 'mechanical']
            >>> self._split_camel_case("simple")
            ['simple']  # Not CamelCase, return as-is
        """
        # Pattern: insert space before uppercase letters (except at start)
        # BallBallContact → Ball Ball Contact
        spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", word)

        # Split on spaces and lowercase
        parts = spaced.split()

        # Only return split if there are multiple parts (actual CamelCase)
        if len(parts) > 1:
            return [p.lower() for p in parts]
        else:
            return [word.lower()]

    def _is_valid_token(self, word: str, from_technical_context: bool = False) -> bool:
        """Check if a word is a valid token.

        Args:
            word: Word to check
            from_technical_context: True if word comes from underscore/hyphen splitting
                                   (e.g., "x" from "vel_x", "1" from "end_1")

        Returns:
            True if word should be kept, False otherwise

        Filtering rules:
        1. Length >= min_length (except numbers and technical single chars)
        2. Not a stopword (unless it's a technical term)
        3. Contains at least one alphanumeric character

        Special handling:
        - Technical single characters (x, y, z, r, n, t) ALWAYS preserved
        - Single-digit numbers always preserved
        - Rationale: In scientific/engineering docs, x/y/z are semantically meaningful
        """
        # Allow single-digit numbers (e.g., "1" from "end_1")
        if word.isdigit():
            return True

        # ALWAYS preserve technical single characters (regardless of context)
        # This is critical for keywords like "force global y", "contact force x"
        # where x/y/z are semantically important but not in underscore/hyphen context
        if len(word) == 1 and word.lower() in self.TECHNICAL_SINGLE_CHARS:
            return True

        # Must have minimum length for other tokens
        if len(word) < self.min_length:
            return False

        # Must contain at least one alphanumeric character
        if not any(c.isalnum() for c in word):
            return False

        # Check stopwords (if enabled)
        if self.remove_stopwords and is_stopword(word):
            return False

        return True

    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize query text for consistent processing.

        Args:
            query: User query string

        Returns:
            Normalized query (lowercase, whitespace normalized)

        Example:
            >>> TextTokenizer.normalize_query("  Create   Ball  ")
            'create ball'
        """
        # Remove extra whitespace and lowercase
        query = " ".join(query.split())
        return query.lower()
