from lib.logger import get_logger

logger = get_logger(__name__)


def test_get_users_from_public_api(api_client):
    response = api_client.get("/users")

    assert response.status_code == 200
    users = response.json()
    logger.info("GET /users response body: %s", users)
    assert isinstance(users, list)
    assert users
    assert {"id", "name", "email"}.issubset(users[0])