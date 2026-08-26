from unittest.mock import Mock


def test_get_builds_url_and_uses_configured_timeout(api_client):
    response = Mock()
    response.status_code = 200
    api_client.session.request = Mock(return_value=response)

    result = api_client.get("/users", params={"active": "true"})

    assert result is response
    api_client.session.request.assert_called_once_with(
        "GET",
        "https://example.test/users",
        params={"active": "true"},
        timeout=10.0,
    )
    response.raise_for_status.assert_called_once_with()