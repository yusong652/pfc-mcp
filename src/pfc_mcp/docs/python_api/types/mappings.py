"""Type system mappings for PFC SDK.

This module defines mappings between PFC object classes and their
parent modules, used for generating official API paths.
"""

# Object class to module mapping
# Maps class names to their parent module names in PFC Python SDK
# Format: "ClassName" -> "module_name" or "module.submodule"
# Official API path structure: itasca.{module}.{Class}.{method}
#
# Examples:
#   Ball -> ball module -> itasca.ball.Ball.vel()
#   Facet -> wall module -> itasca.wall.Facet.vel()
#   Vertex -> wall.vertex module -> itasca.wall.vertex.Vertex.pos()
#   Pebble -> clump module -> itasca.clump.Pebble.vel()
#
# Note: Contact is NOT included here because it uses abstract path representation:
# keywords.json: itasca.contact.Contact.* (abstract)
# loader expands to: itasca.BallBallContact.*, itasca.BallFacetContact.*, etc. (concrete)
CLASS_TO_MODULE = {
    "Ball": "ball",
    "Clump": "clump",
    "Measure": "measure",
    "Wall": "wall",
    "Facet": "wall",  # Facet is under wall module
    "Vertex": "wall.vertex",  # Vertex is under wall.vertex submodule
    "Pebble": "clump",  # Pebble is under clump module
    "Template": "clump.template",  # Template is under clump.template submodule
}
