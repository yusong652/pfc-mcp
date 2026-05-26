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

ALL_VERSIONS = ["6.0", "7.0", "9.0"]

# Contact types sharing the full mechanical interface.
MECHANICAL_CONTACT_TYPES = [
    "BallBallContact",
    "BallFacetContact",
    "BallPebbleContact",
    "PebblePebbleContact",
    "PebbleFacetContact",
    "BallRBlockContact",
    "PebbleRBlockContact",
    "RBlockFacetContact",
    "RBlockRBlockContact",
    "VertexFacetContact",
]

THERMAL_CONTACT_TYPES = [
    "BallBallThermalContact",
    "BallFacetThermalContact",
    "BallPebbleThermalContact",
    "PebblePebbleThermalContact",
    "PebbleFacetThermalContact",
]

CONTACT_TYPES = MECHANICAL_CONTACT_TYPES
ALL_CONTACT_TYPES = MECHANICAL_CONTACT_TYPES + THERMAL_CONTACT_TYPES

CONTACT_INTERFACE_TYPES = {
    "Contact": MECHANICAL_CONTACT_TYPES,
    "ThermalContact": THERMAL_CONTACT_TYPES,
}

CONTACT_TYPE_TO_INTERFACE = {
    contact_type: interface
    for interface, contact_types in CONTACT_INTERFACE_TYPES.items()
    for contact_type in contact_types
}

CONTACT_TYPE_VERSIONS = {contact_type: ALL_VERSIONS for contact_type in ALL_CONTACT_TYPES}
CONTACT_TYPE_VERSIONS["VertexFacetContact"] = ["9.0"]

# PFC 9 runtime reflection shows thermal contacts share these non-force
# Contact methods. Thermal-specific power/set_power are real but do not have
# source docs in this tree yet, so they are intentionally not expanded here.
THERMAL_CONTACT_METHODS = {
    "activate",
    "activated",
    "active",
    "end1",
    "end2",
    "extra",
    "gap",
    "group",
    "group_remove",
    "groups",
    "has_prop",
    "id",
    "in_group",
    "inhibit",
    "method",
    "model",
    "normal",
    "normal_x",
    "normal_y",
    "normal_z",
    "offset",
    "offset_x",
    "offset_y",
    "offset_z",
    "persist",
    "pos",
    "pos_x",
    "pos_y",
    "pos_z",
    "prop",
    "props",
    "set_extra",
    "set_group",
    "set_inhibit",
    "set_model",
    "set_persist",
    "set_prop",
    "shear",
    "shear_x",
    "shear_y",
    "shear_z",
    "valid",
}


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


def is_contact_type(contact_type: str) -> bool:
    return contact_type in CONTACT_TYPE_TO_INTERFACE


def get_contact_interface(contact_type: str) -> str | None:
    return CONTACT_TYPE_TO_INTERFACE.get(contact_type)


def get_contact_type_versions(contact_type: str) -> list[str]:
    return CONTACT_TYPE_VERSIONS.get(contact_type, ALL_VERSIONS)


def get_contact_types_for_interface(interface: str) -> list[str]:
    return CONTACT_INTERFACE_TYPES.get(interface, [])


def get_contact_types_for_method(method_name: str) -> list[str]:
    contact_types = list(MECHANICAL_CONTACT_TYPES)
    if method_name in THERMAL_CONTACT_METHODS:
        contact_types.extend(THERMAL_CONTACT_TYPES)
    return contact_types


def get_contact_type_from_api_path(api_path: str) -> str | None:
    parts = api_path.split(".")
    for part in parts:
        if is_contact_type(part):
            return part
    return None


def contact_type_supports_method(contact_type: str, method_name: str) -> bool:
    interface = get_contact_interface(contact_type)
    if interface == "ThermalContact":
        return method_name in THERMAL_CONTACT_METHODS
    return interface == "Contact"


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
        return any(ct.lower() in parts_lower for ct in ALL_CONTACT_TYPES)

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

        for contact_type in ALL_CONTACT_TYPES:
            contact_type_lower = contact_type.lower()

            if contact_type_lower in parts_lower:
                contact_idx = parts_lower.index(contact_type_lower)

                # Extract method name after contact type
                if contact_idx + 1 < len(parts):
                    method_name = parts[contact_idx + 1]
                    interface = get_contact_interface(contact_type)
                    if not interface:
                        continue
                    internal_path = f"{interface}.{method_name}"

                    # Only return exact matches
                    # Partial matching is handled by BM25 search
                    if contact_type_supports_method(contact_type, method_name) and ContactTypeResolver._verify_method(
                        internal_path, quick_ref
                    ):
                        return ContactQueryResult(
                            internal_path=internal_path,
                            contact_type=contact_type,
                            original_query=api_path.strip(),
                            all_types=get_contact_types_for_method(method_name),
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

        if internal_path.startswith(("Contact.", "ThermalContact.")):
            interface, method_name = internal_path.split(".", 1)
            return any(
                f"itasca.{contact_type}.{method_name}" in quick_ref
                for contact_type in get_contact_types_for_interface(interface)
            )

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
