from io import BytesIO

import pytest
from unittest.mock import patch


from app import create_app

from app.routes import replay_routes, page_routes


# Mock async generator to simulate async behavior
async def async_generator(data):
    for item in data:
        yield item


@pytest.fixture(name="testapp")
def testapp():
    app = create_app()
    app.register_blueprint(replay_routes.bp)
    app.register_blueprint(page_routes.bp)
    return app


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_replays_into_sets(testapp):

    client = testapp.test_client()

    response = await client.get("/api/replay-sets?page=1")
    assert response.status_code == 200
    js = await response.json
    assert "replays" in await response.json
    assert js["current_page"] == 1

    response = await client.get("/api/replay-sets?page=1000000")
    assert response.status_code == 404
    assert "error" in await response.json

    response = await client.get("/api/replay-sets?page=-1")
    assert response.status_code == 200

    response = await client.get("/api/replay-sets?page=dab")
    assert response.status_code == 200
    js = await response.json
    assert js["current_page"] == 1
    assert "replays" in js


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_replay(testapp):
    client = testapp.test_client()
    response = await client.get("/api/replay/27aac657412286f126419ab47")
    assert response.status_code == 200
    response = await client.get("/api/replay/dab")
    assert response.status_code == 401
    assert "error" in response.json

@pytest.mark.asyncio
@pytest.mark.xfail
@pytest.mark.integration
async def test_set_download_replay(testapp):
    client = testapp.test_client()

    with patch('app.replay_controller.download_replays',
               return_value=(BytesIO(b'data'), 'filename.zip', 'application/zip')):
        response = await client.get(f"/download-set?filenames=27aac657412286f126419ab47.dat,a3d39509785247cd10055f307.dat,71412f406907666b87ca332ca.dat")
        assert response.status_code == 200
        assert response.headers['Content-Disposition'] == 'attachment; filename=filename.zip'
        # this will fail since donloads always return 200 for bow
        response = await client.get(f"/download-set?filenames=dab")
        assert response.status_code == 401

    with patch('app.replay_controller.download_replays', return_value=None):
        response = await client.get(f"/download-set?filenames=-10foihgfaohgfophfapofah0")
        assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.xfail
@pytest.mark.integration
async def test_download_replay(testapp):
    client = testapp.test_client()

    with patch('app.replay_controller.download_replay',
               return_value=(BytesIO(b'data'), 'filename.dat', 'application/octet-stream')):
        response = await client.get(f"/download?filename=27aac657412286f126419ab47")

        assert response.status_code == 200
        assert response.headers['Content-Disposition'] == 'attachment; filename=filename.dat'
        # this will fail since donloads always return 200 for bow
        response = await client.get(f"/download?filename=00000000")
        assert response.status_code == 401

    with patch('app.replay_controller.download_replay', return_value=None):
        response = await client.get(f"/download?filename=00000000")
        assert response.status_code == 404



@pytest.mark.asyncio
async def test_delete_replay(testapp):
    client = testapp.test_client()

    with patch("app.replay_controller.delete_replay", return_value=True):
        response = await client.delete(f"/api/replay/27aac657412286f126419ab47")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_replay(testapp):
    client = testapp.test_client()
    with patch("app.replay_controller.update_replay", return_value=True):
        response = await client.put(f"/api/replay/27aac657412286f126419ab47")
        assert response.status_code == 403
