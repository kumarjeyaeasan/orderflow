from gateway.routing import resolve_upstream

# Standard small routing table dictionary used for test coverage
ROUTES = {"/orders": "http://m", "/products": "http://m", "/admin": "http://m"}


def test_exact_prefix_is_routed():
    """Verifies that paths matching an exact route prefix map correctly."""
    assert resolve_upstream("/orders", ROUTES) == "http://m"
    assert resolve_upstream("/products", ROUTES) == "http://m"
    assert resolve_upstream("/admin", ROUTES) == "http://m"


def test_sub_path_is_routed():
    """Verifies that extended sub-paths under a valid prefix map correctly."""
    assert resolve_upstream("/orders/123/cancel", ROUTES) == "http://m"
    assert resolve_upstream("/admin/products/x/stock", ROUTES) == "http://m"


def test_lookalike_prefix_is_not_routed():
    """Ensures partial string overlaps do not trigger incorrect prefix matches."""
    assert resolve_upstream("/ordersXYZ", ROUTES) is None
    assert resolve_upstream("/products-v2", ROUTES) is None


def test_internal_path_is_not_routed():
    """Ensures that unmapped internal-only routes return None."""
    assert resolve_upstream("/internal/customers/abc", ROUTES) is None


def test_root_and_unknown_paths_are_not_routed():
    """Ensures general root directories and completely unknown patterns fail cleanly."""
    assert resolve_upstream("/", ROUTES) is None
    assert resolve_upstream("/nope", ROUTES) is None
