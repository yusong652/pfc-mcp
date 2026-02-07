"""Stopwords list for PFC technical documentation.

This module provides a curated stopwords list optimized for scientific and
technical documentation, preserving technical terms while filtering common
English words.
"""

# Technical documentation stopwords
# Carefully curated to avoid removing technical terms
STOPWORDS = {
    # Articles
    'a', 'an', 'the',

    # Pronouns
    'this', 'that', 'these', 'those',
    'it', 'its', 'itself',
    'they', 'them', 'their', 'theirs', 'themselves',
    'what', 'which', 'who', 'whom', 'whose',

    # Prepositions
    'with', 'from', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'as',
    'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'under', 'again', 'further', 'then', 'once',

    # Conjunctions
    'and', 'or', 'but', 'nor', 'so', 'yet',

    # Common verbs (be/have forms)
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'having',
    'do', 'does', 'did', 'doing',

    # Modal verbs
    'will', 'would', 'can', 'could', 'may', 'might',
    'shall', 'should', 'must',

    # Other common words
    'if', 'than', 'because', 'while', 'where', 'when',
    'why', 'how', 'all', 'both', 'each', 'few', 'more',
    'most', 'other', 'some', 'such', 'no', 'not', 'only',
    'own', 'same', 'than', 'too', 'very',

    # Common adverbs
    'here', 'there', 'now', 'then', 'just', 'also',
    'always', 'never', 'often', 'sometimes',
}

# Technical terms to PRESERVE (not stopwords)
# These are often confused with stopwords but are meaningful in PFC context
TECHNICAL_PRESERVE = {
    'set',        # set property, set value
    'get',        # get value, get property
    'command',    # PFC command
    'generate',   # generate balls
    'create',     # create objects
    'delete',     # delete objects
    'property',   # model property
    'model',      # contact model
    'contact',    # contact mechanics
    'ball',       # ball object
    'wall',       # wall object
    'cycle',      # simulation cycle
    'range',      # range specification
    'group',      # object group
    'id',         # object ID
    'list',       # list objects
    'find',       # find objects
    'near',       # near neighbors
    'zone',       # zone element
    'node',       # node element
    'face',       # facet face
    'edge',       # edge element
    'measure',    # measure command
    'calculate',  # calculate value
    'update',     # update state
    'reset',      # reset state
    'initialize', # initialize simulation
    'solve',      # solve equations
    'apply',      # apply force
    'assign',     # assign value
    'remove',     # remove object
    'clear',      # clear data
    'save',       # save state
    'restore',    # restore state
    'export',     # export data
    'import',     # import data
}


def is_stopword(word: str) -> bool:
    """Check if a word is a stopword.

    Args:
        word: Word to check (will be lowercased)

    Returns:
        True if word is a stopword, False otherwise

    Example:
        >>> is_stopword('the')
        True
        >>> is_stopword('ball')  # Technical term
        False
        >>> is_stopword('SET')   # Case insensitive
        False  # Preserved technical term
    """
    word_lower = word.lower()

    # Check if it's a preserved technical term
    if word_lower in TECHNICAL_PRESERVE:
        return False

    # Check if it's a stopword
    return word_lower in STOPWORDS
