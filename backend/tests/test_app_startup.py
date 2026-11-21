def _route_paths():
    import main

    return {getattr(route, "path", "") for route in main.app.routes}


def test_app_imports_and_registers_routes():
    paths = _route_paths()
    for expected in [
        "/auth/signup",
        "/auth/login",
        "/auth/forgot-password",
        "/auth/reset-password",
        "/predict",
        "/ws/chat",
    ]:
        assert expected in paths, f"missing route: {expected}"


def test_training_is_not_exposed_over_http():
    assert not any(path.startswith("/train") for path in _route_paths())
