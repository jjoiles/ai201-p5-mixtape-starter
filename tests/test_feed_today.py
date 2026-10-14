
"""
Regression test for Issue #2:
Friends Listening Now includes yesterday's activity.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch


"""
Regression tests for Issue #2:
Friends Listening Now should show only today's activity.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app import create_app, db
from models import User, Song, ListeningEvent, friendships
from services.feed_service import get_friends_listening_now


@pytest.fixture
def test_app(tmp_path):
    database_path = tmp_path / "mixtape_feed_test.db"

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def create_test_data(listened_at):
    viewer = User(
        username="feed_test_viewer",
        email="feed_viewer@example.com",
    )

    friend = User(
        username="feed_test_friend",
        email="feed_friend@example.com",
    )

    db.session.add_all([viewer, friend])
    db.session.flush()

    db.session.execute(
        friendships.insert().values(
            user_id=viewer.id,
            friend_id=friend.id,
        )
    )

    song = Song(
        title="Test Song",
        artist="Test Artist",
        shared_by=friend.id,
    )

    db.session.add(song)
    db.session.flush()

    db.session.add(
        ListeningEvent(
            user_id=friend.id,
            song_id=song.id,
            listened_at=listened_at,
        )
    )

    db.session.commit()

    return viewer.id, friend.id


def test_listening_now_excludes_yesterday(test_app):
    with test_app.app_context():
        today = datetime.now(timezone.utc).date()

        fake_now = datetime.combine(
            today,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) + timedelta(hours=9)

        yesterday_listen = fake_now - timedelta(hours=10)

        viewer_id, friend_id = create_test_data(
            yesterday_listen
        )

        with patch("services.feed_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fake_now

            result = get_friends_listening_now(viewer_id)

        assert result == [], (
            "Yesterday's listening activity should not "
            "appear in today's Listening Now feed."
        )


def test_listening_now_includes_today(test_app):
    with test_app.app_context():
        today = datetime.now(timezone.utc).date()

        fake_now = datetime.combine(
            today,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ) + timedelta(hours=9)

        today_listen = fake_now - timedelta(hours=1)

        viewer_id, friend_id = create_test_data(
            today_listen
        )

        with patch("services.feed_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = fake_now

            result = get_friends_listening_now(viewer_id)

        assert len(result) == 1
        assert result[0]["friend"]["id"] == friend_id
