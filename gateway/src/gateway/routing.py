from collections.abc import Mapping

# Only these paths are exposed to clients; everything else (e.g. /internal) gets 404.
PUBLIC_PREFIXES: tuple[str, ...] = ("/products", "/orders", "/admin")


def resolve_upstream(path: str, routes: Mapping[str, str]) -> str | None:
    """
    Resolves the incoming requested path to its corresponding upstream base URL
    based on a dynamic routing table configuration.

    Ensures safe prefix matching so that partial string overlaps (e.g., matching
    '/ordersXYZ' against '/orders') are correctly ignored.

    Args:
        path: The incoming request URL path (e.g., '/orders/123/items').
        routes: A dictionary mapping path prefixes to their upstream base URLs, e.g.
            {
                "/products": "http://monolith:8010",
                "/orders": "http://monolith:8010",
                "/admin": "http://monolith:8010",
            }
            (From Phase 2, "/products" will point at the inventory service instead.)

    Returns:
        The target upstream base URL string if a match is found, otherwise None.
        With the sample routes above:
            "/orders"                 -> "http://monolith:8010"   (exact prefix)
            "/orders/123/cancel"      -> "http://monolith:8010"   (sub-path)
            "/admin/products/x/stock" -> "http://monolith:8010"
            "/ordersXYZ"              -> None                     (look-alike, not a sub-path)
            "/internal/customers/abc" -> None                     (not public)
            "/"                       -> None
    """
    for prefix, upstream in routes.items():
        # Exact match or match followed by a sub-path delimiter slash prevents false positives
        if path == prefix or path.startswith(prefix + "/"):
            return upstream

    # Explicitly return None if the route is not found or not public
    return None
