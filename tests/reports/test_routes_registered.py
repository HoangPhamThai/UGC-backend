def test_report_routes_registered():
    from app.modules.reports.presentation.routes import router
    paths = {r.path for r in router.routes}
    assert "/reports/eligible" in paths
    assert "/reports/generate" in paths
    assert "/reports" in paths
    assert "/reports/template" in paths
    assert "/reports/template/download" in paths
    assert "/reports/{report_id}" in paths
    assert "/reports/{report_id}/finalize" in paths
    assert "/reports/{report_id}/regenerate" in paths
    assert "/reports/{report_id}/download" in paths
    assert "/me/reports" in paths
    assert "/me/reports/{report_id}/download" in paths


def test_app_registers_report_router():
    from app.app import app
    paths = {r.path for r in app.routes}
    assert "/api/v1/reports/eligible" in paths
    assert "/api/v1/me/reports" in paths
