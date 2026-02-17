"""Contact type handling with intelligent aliasing.

PFC has multiple contact types (BallBallContact, BallFacetContact, etc.)
that share the same interface. This module maps official paths to internal
documentation while preserving type information.

Architecture:
    Official API: itasca.BallBallContact.gap(), itasca.BallFacetContact.gap()
    Internal docs: Contact.gap() (shared interface)

    ContactTypeResolver handles the mapping transparently.
"""

from dataclasses import dataclass

# All contact types sharing the same interface
# These are the official PFC contact type names
CONTACT_TYPES = [
    "BallBallContact",
    "BallFacetContact",
    "BallPebbleContact",
    "PebblePebbleContact",
    "PebbleFacetContact",
]


@dataclass
class ContactQueryResult:
    """Result of Contact type query processing.

    Attributes:
        internal_path: Internal documentation path (e.g., "Contact.gap")
        contact_type: Specific contact type queried (e.g., "BallBallContact")
        original_query: Original query string from user
        all_types: All available contact types sharing this interface

    Example:
        >>> ContactQueryResult(
        ...     internal_path="Contact.gap",
        ...     contact_type="BallBallContact",
        ...     original_query="BallBallContact.gap",
        ...     all_types=CONTACT_TYPES
        ... )
    """

    internal_path: str
    contact_type: str
    original_query: str
    all_types: list[str]


class ContactTypeResolver:
    """Resolves Contact type queries to internal documentation paths.

    This resolver handles the mapping between official PFC contact type names
    (e.g., BallBallContact) and the internal unified documentation (Contact).
    """

    @staticmethod
    def is_contact_query(api_path: str) -> bool:
        """Check if query is for a Contact type method.

        Args:
            api_path: API path string to check

        Returns:
            True if path contains any known contact type name

        Examples:
            >>> ContactTypeResolver.is_contact_query("BallBallContact.gap")
            True
            >>> ContactTypeResolver.is_contact_query("itasca.ball.create")
            False
        """
        parts_lower = [p.lower() for p in api_path.split(".")]
        return any(ct.lower() in parts_lower for ct in CONTACT_TYPES)

    @staticmethod
    def resolve(api_path: str, quick_ref: dict[str, str]) -> ContactQueryResult | None:
        """Resolve Contact type query to internal path.

        Supports multiple query formats:
        - Full path: "itasca.BallBallContact.gap"
        - Partial path: "BallBallContact.gap"
        - Case-insensitive: "ballballcontact.gap"

        Note: Partial method name matching (e.g., "BallBallContact.force" → "Contact.force_global")
        is handled by BM25 search through tokenization and partial matching.

        Args:
            api_path: API path string to resolve
            quick_ref: Quick reference dict from index (for validation)

        Returns:
            ContactQueryResult if valid contact query with exact method match, None otherwise

        Examples:
            >>> resolve("BallBallContact.gap", {"Contact.gap": "..."})
            ContactQueryResult(internal_path="Contact.gap", ...)
            >>> resolve("ballballcontact.force", {...})
            None  # Partial match handled by BM25 search
            >>> resolve("itasca.ball.create", {...})
            None
        """
        parts = api_path.split(".")
        parts_lower = [p.lower() for p in parts]

        for contact_type in CONTACT_TYPES:
            contact_type_lower = contact_type.lower()

            if contact_type_lower in parts_lower:
                contact_idx = parts_lower.index(contact_type_lower)

                # Extract method name after contact type
                if contact_idx + 1 < len(parts):
                    method_name = parts[contact_idx + 1]
                    internal_path = f"Contact.{method_name}"

                    # Only return exact matches
                    # Partial matching is handled by BM25 search
                    if ContactTypeResolver._verify_method(internal_path, quick_ref):
                        return ContactQueryResult(
                            internal_path=internal_path,
                            contact_type=contact_type,
                            original_query=api_path.strip(),
                            all_types=CONTACT_TYPES,
                        )

        return None

    @staticmethod
    def _verify_method(internal_path: str, quick_ref: dict[str, str]) -> bool:
        """Verify that the method exists in Contact interface.

        Args:
            internal_path: Internal path to verify (e.g., "Contact.gap")
            quick_ref: Quick reference dict from index

        Returns:
            True if method exists in Contact interface
        """
        # Try exact match
        if internal_path in quick_ref:
            return True

        # Try case-insensitive match
        internal_path_lower = internal_path.lower()
        return any(api.lower() == internal_path_lower for api in quick_ref)

    @staticmethod
    def format_official_path(contact_type: str, method_name: str) -> str:
        """Format official API path for display.

        Args:
            contact_type: Contact type name (e.g., "BallBallContact")
            method_name: Method name (e.g., "gap")

        Returns:
            Official API path string

        Example:
            >>> ContactTypeResolver.format_official_path("BallBallContact", "gap")
            "itasca.BallBallContact.gap"
        """
        return f"itasca.{contact_type}.{method_name}"
