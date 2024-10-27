import asyncio
from io import BytesIO

import pytest
from unittest.mock import patch
from tests.constants import REPLAYS
from tests.helpers import async_generator_mock, generate_mock_replays_from_data


# Mock async generator to simulate async behavior
async def async_generator(data):
    for item in data:
        yield item


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_replays_into_sets(client):
    def sync_test():
        with client:

            with patch('app.replay_controller.get_replays') as mock_get_replays, \
                    patch('app.replay_controller.get_total_pages', return_value=3):

                mock_get_replays.return_value = async_generator_mock(generate_mock_replays_from_data(REPLAYS))
                response = client.get("/api/replay-sets?page=1")

                assert response.status_code == 200
                assert "replays" in response.json
                assert response.json["current_page"] == 1
                assert response.json["max_page"] == 3

                response = client.get("/api/replay-sets?page=-1000000")
                assert response.status_code == 404
                assert "error" in response.json

            with patch('app.replay_controller.get_replays') as mock_get_replays, \
                    patch('app.replay_controller.get_total_pages', return_value=3):

                mock_get_replays.return_value = async_generator_mock(generate_mock_replays_from_data(REPLAYS))
                response = client.get("/api/replay-sets?page=dab")
                assert response.status_code == 200
                assert response.json["current_page"] == 1
                assert "replays" in response.json

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_replay(client):
    def sync_test():
        with client:
            response = client.get("/api/replay/1")
            assert response.status_code == 200
            assert response.json["replay_id"] == 1

            response = client.get("/api/replay/dab")
            assert response.status_code == 401
            assert "error" in response.json

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_set_download_replay(client):

    def sync_test():
        with client:
            with patch('app.replay_controller.download_replays',
                       return_value=(BytesIO(b'data'), 'filename.zip', 'application/zip')):
                response = client.get(f"/download-set?replay_ids=1,2,3,4,5,6,7")
                assert response.status_code == 200
                assert response.headers['Content-Disposition'] == 'attachment; filename=replays-filename.zip'

                response = client.get(f"/download-set?replay_ids=dab")
                assert response.status_code == 401

            with patch('app.replay_controller.download_replays', return_value=None):
                response = client.get(f"/download-set?replay_ids=-100")
                assert response.status_code == 404

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_download_replay(client):

    def sync_test():
        with client:
            with patch('app.replay_controller.download_replay',
                       return_value=(BytesIO(b'data'), 'filename.dat', 'application/octet-stream')):
                response = client.get(f"/download?replay_id=1")

                assert response.status_code == 200
                assert response.headers['Content-Disposition'] == 'attachment; filename=filename.dat'

                response = client.get(f"/download?replay_id=dab")
                assert response.status_code == 401

            with patch('app.replay_controller.download_replay', return_value=None):
                response = client.get(f"/download?replay_id=-100")
                assert response.status_code == 404

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sync_test)


# @pytest.mark.asyncio
# async def test_delete_replay(client):
#
#     def sync_test():
#         with client:
#             with patch('app.replay_controller.delete_replay', return_value=True):
#                 response = client.delete(f"/api/replay/1")
#                 assert response.status_code == 403
#
#             with patch('app.utils.utils.require_api_key', lambda x: x):
#                 with patch('app.replay_controller.delete_replay', return_value=True):
#                     response = client.delete(f"/api/replay/1")
#                     assert response.status_code == 204
#
#                 with patch('app.replay_controller.delete_replay', return_value=None):
#                     response = client.delete(f"/api/replay/1")
#                     assert response.status_code == 404
#
#     loop = asyncio.get_running_loop()
#     await loop.run_in_executor(None, sync_test)
#
#
# @pytest.mark.asyncio
# async def test_update_replay(client):
#     def sync_test():
#         with client:
#             with patch('app.replay_controller.update_replay', return_value=True):
#                 response = client.update(f"/api/replay/1")
#                 assert response.status_code == 403
#
#             with patch('app.utils.utils.require_api_key', lambda x: x):
#                 with patch('app.replay_controller.update_replay', return_value=True):
#                     response = client.delete(f"/api/replay/1")
#                     assert response.status_code == 204
#
#                 with patch('app.replay_controller.update_replay', return_value=None):
#                     response = client.delete(f"/api/replay/1")
#                     assert response.status_code == 404
#
#     loop = asyncio.get_running_loop()
#     await loop.run_in_executor(None, sync_test)
