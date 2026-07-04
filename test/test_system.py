import os

import pytest
import requests


@pytest.mark.skipif(
    not os.environ.get("BASE_URL") or not os.environ.get("ID_TOKEN"),
    reason="BASE_URL and ID_TOKEN are required for deployed system test",
)
def test_system() -> None:
    base_url = os.environ["BASE_URL"]
    id_token = os.environ["ID_TOKEN"]

    resp = requests.get(
        base_url, headers={"Authorization": f"Bearer {id_token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Successfully running Cat."}
