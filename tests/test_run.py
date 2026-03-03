from unittest.mock import patch

import pytest

from client.sync_client import run


def test_run_exits_if_source_dir_does_not_exist():
    with pytest.raises(SystemExit):
        run("/nonexistent/path", "http://127.0.0.1:5000")


def test_run_calls_initial_sync(source_dir):
    with patch("client.sync_client.SyncAPIClient"), \
         patch("client.sync_client.initial_sync") as mock_initial_sync, \
         patch("client.sync_client.Observer"), \
         patch("client.sync_client.time.sleep", side_effect=KeyboardInterrupt):

        run(str(source_dir), "http://127.0.0.1:5000")

        mock_initial_sync.assert_called_once()


def test_run_starts_observer(source_dir):
    with patch("client.sync_client.SyncAPIClient"), \
         patch("client.sync_client.initial_sync"), \
         patch("client.sync_client.Observer") as mock_observer_class, \
         patch("client.sync_client.time.sleep", side_effect=KeyboardInterrupt):

        run(str(source_dir), "http://127.0.0.1:5000")

        mock_observer_class.return_value.start.assert_called_once()


def test_run_stops_observer_on_keyboard_interrupt(source_dir):
    with patch("client.sync_client.SyncAPIClient"), \
         patch("client.sync_client.initial_sync"), \
         patch("client.sync_client.Observer") as mock_observer_class, \
         patch("client.sync_client.time.sleep", side_effect=KeyboardInterrupt):

        run(str(source_dir), "http://127.0.0.1:5000")

        mock_observer_class.return_value.stop.assert_called_once()
        mock_observer_class.return_value.join.assert_called_once()


def test_run_schedules_observer_recursively(source_dir):
    with patch("client.sync_client.SyncAPIClient"), \
         patch("client.sync_client.initial_sync"), \
         patch("client.sync_client.Observer") as mock_observer_class, \
         patch("client.sync_client.time.sleep", side_effect=KeyboardInterrupt):

        run(str(source_dir), "http://127.0.0.1:5000")

        call_kwargs = mock_observer_class.return_value.schedule.call_args
        assert call_kwargs[1]["recursive"] is True