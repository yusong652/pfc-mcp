"""Contact API consolidation for search results.

This module handles deduplication of Contact type APIs (BallBallContact, BallFacetContact, etc.)
that share the same interface, reducing redundancy while preserving type information.
"""

from typing import List
from pfc_mcp.docs.models.search_result import SearchResult


def consolidate_contact_apis(results: List[SearchResult]) -> List[SearchResult]:
    """Consolidate duplicate Contact type APIs.

    When multiple Contact types (BallBallContact, BallFacetContact, etc.) share
    the same method, keep only the first (highest-scoring) result and add metadata
    indicating all applicable Contact types.

    This reduces redundancy in search results while informing LLM that the method
    is compatible across all Contact types.

    Design Philosophy:
    - **Pure function**: Doesn't modify input results
    - **Contact type detection**: Uses CONTACT_TYPES list from python_api.types
    - **Metadata enrichment**: Adds 'all_contact_types' to first result's metadata
    - **Preserves order**: Maintains score-based ranking from search engine

    Args:
        results: List of SearchResult objects (should be sorted by score, descending)

    Returns:
        New list with Contact methods consolidated

    Example:
        Before consolidation (10 results):
            1. itasca.BallBallContact.gap (score: 8.5)
            2. itasca.BallFacetContact.gap (score: 8.5)
            3. itasca.BallPebbleContact.gap (score: 8.5)
            4. itasca.PebblePebbleContact.gap (score: 8.5)
            5. itasca.PebbleFacetContact.gap (score: 8.5)
            6. itasca.BallBallContact.set_model (score: 7.2)
            7. itasca.BallFacetContact.set_model (score: 7.2)
            8. itasca.BallPebbleContact.set_model (score: 7.2)
            9. itasca.PebblePebbleContact.set_model (score: 7.2)
            10. itasca.PebbleFacetContact.set_model (score: 7.2)

        After consolidation (2 results):
            1. itasca.BallBallContact.gap (score: 8.5)
               metadata['all_contact_types'] = [
                   'BallBallContact', 'BallFacetContact', 'BallPebbleContact',
                   'PebblePebbleContact', 'PebbleFacetContact'
               ]
            2. itasca.BallBallContact.set_model (score: 7.2)
               metadata['all_contact_types'] = [
                   'BallBallContact', 'BallFacetContact', 'BallPebbleContact',
                   'PebblePebbleContact', 'PebbleFacetContact'
               ]

    Usage:
        >>> from pfc_mcp.docs.query import APISearch
        >>> from pfc_mcp.docs.search.postprocessing import consolidate_contact_apis
        >>>
        >>> results = APISearch.search("contact model", top_k=20)
        >>> len(results)
        20  # May contain many Contact type duplicates
        >>>
        >>> consolidated = consolidate_contact_apis(results)
        >>> len(consolidated)
        5  # Much cleaner!
        >>>
        >>> # Check metadata
        >>> consolidated[0].document.metadata.get('all_contact_types')
        ['BallBallContact', 'BallFacetContact', 'BallPebbleContact', ...]
    """
    # Import Contact types
    try:
        from pfc_mcp.docs.python_api.types.contact import CONTACT_TYPES
    except ImportError:
        # If Contact types not available, return unchanged
        return results

    consolidated = []
    seen_methods = {}  # Track Contact methods: {method_name: index_in_consolidated}

    for result in results:
        doc_name = result.document.name

        # Check if this is a Contact type API
        contact_type = None
        method_name = None

        for ct in CONTACT_TYPES:
            # Check if doc_name contains this Contact type
            # Examples: "itasca.BallBallContact.gap", "BallBallContact.gap"
            if f".{ct}." in doc_name or doc_name.startswith(f"{ct}."):
                contact_type = ct
                # Extract method name (everything after Contact type)
                parts = doc_name.split(f"{ct}.")
                if len(parts) == 2:
                    method_name = parts[1]  # e.g., "gap", "force_normal", "set_model"
                break

        # If not a Contact API, keep as-is
        if not contact_type or not method_name:
            consolidated.append(result)
            continue

        # If we've already seen this Contact method, update the first one's metadata
        if method_name in seen_methods:
            first_idx = seen_methods[method_name]
            first_result = consolidated[first_idx]

            # Update metadata to include this Contact type
            if "all_contact_types" not in first_result.document.metadata:
                # Initialize with the first Contact type we saw
                first_contact_type = None
                for ct in CONTACT_TYPES:
                    if f".{ct}." in first_result.document.name or first_result.document.name.startswith(f"{ct}."):
                        first_contact_type = ct
                        break

                first_result.document.metadata["all_contact_types"] = [first_contact_type] if first_contact_type else []

            # Add current Contact type if not already in the list
            if contact_type not in first_result.document.metadata["all_contact_types"]:
                first_result.document.metadata["all_contact_types"].append(contact_type)

            # Skip adding this duplicate result
            continue

        # First time seeing this Contact method - add it and track it
        seen_methods[method_name] = len(consolidated)
        consolidated.append(result)

    return consolidated
