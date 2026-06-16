"""Locks the contract that the agents service can read the field registry via an
interim key. The registry route must require a permission that is interim-allowed,
otherwise the analyze-rules flow 403s. See INTERIM_ALLOWED_PERMISSIONS."""
from app.core.permissions import INTERIM_ALLOWED_PERMISSIONS, Permission, interim_key_allows


def test_reports_read_is_interim_allowed():
    # The registry endpoint is gated by REPORTS_READ; the agents service reaches it
    # with an interim key, so REPORTS_READ must be interim-allowed.
    assert Permission.REPORTS_READ in INTERIM_ALLOWED_PERMISSIONS
    assert interim_key_allows([Permission.REPORTS_READ]) is True


def test_registry_route_uses_interim_allowed_permission():
    # Introspect the actual route dependency to ensure it isn't accidentally
    # changed back to a non-interim-allowed permission like REPORTS_MANAGE.
    from app.modules.reports.presentation.routes import router

    registry_routes = [r for r in router.routes
                       if getattr(r, "path", "") == "/report-rules/registry"]
    assert registry_routes, "registry route not found"
    # Walk the route's dependency tree collecting the permissions passed to
    # require_permissions (stored on the closure of the dependency callables).
    import inspect

    def _perms_in_route(route):
        found = set()
        deps = list(getattr(route.dependant, "dependencies", []))
        # Also include the route's own dependant call (the endpoint's Depends args)
        stack = deps[:]
        # Inspect the security/closure: require_permissions returns `dep` whose
        # closure holds `needed`. Find such closures among the route dependencies.
        for d in stack:
            call = getattr(d, "call", None)
            if call is None:
                continue
            closure = getattr(call, "__closure__", None) or ()
            for cell in closure:
                try:
                    val = cell.cell_contents
                except ValueError:
                    continue
                if isinstance(val, tuple) and all(isinstance(p, Permission) for p in val) and val:
                    found.update(val)
        return found

    perms = _perms_in_route(registry_routes[0])
    # The registry route must be gated only by interim-allowed permission(s).
    assert perms, "no require_permissions found on registry route"
    assert all(p in INTERIM_ALLOWED_PERMISSIONS for p in perms), f"registry perms not interim-allowed: {perms}"
