
# Mixtape Bug Hunt — Project 5

## Codebase Map

### Application Overview

Mixtape is a Flask-based social music application that allows users to share songs, create collaborative playlists, rate music, and track listening activity.

The application follows a layered architecture that separates HTTP request handling, business logic, and database models.

### Main Files and Responsibilities

- `app.py`: Creates and configures the Flask application and initializes the database.

- `models.py`: Defines seven SQLAlchemy models: User, Tag, Song, ListeningEvent, Rating, Playlist, and Notification. It also defines three association tables: friendships, song_tags, and playlist_entries. The playlist_entries table stores each song's position, the user who added it, and when it was added.

- `routes/songs.py`: Handles requests for sharing, searching, and rating songs.
- `routes/playlists.py`: Handles playlist creation and song management endpoints.
- `routes/users.py`: Handles user profiles, listening streaks, and notifications.
- `routes/feed.py`: Handles requests for listening activity and friends' feeds.
- `services/streak_service.py`: Contains the logic for calculating listening streaks.
- `services/feed_service.py`: Handles the retrieval of friends' listening activity.
- `services/search_service.py`: Implements song search functionality.
- `services/notification_service.py`: Handles song ratings and notification-related operations.
- `services/playlist_service.py`: Retrieves songs belonging to playlists.
- `seed_data.py`: Populates the database with sample data.
- `tests/`: Contains automated tests for application functionality.

### Feature Data Flow: Viewing Playlist Songs


### Feature Data Flow: Viewing Playlist Songs

1. A user sends a GET request to `/playlists/<playlist_id>/songs`.
2. Flask routes the request to `get_songs()` in `routes/playlists.py`.
3. The route calls `get_playlist_songs(playlist_id)` from `services/playlist_service.py`.
4. The service is responsible for retrieving the songs associated with the requested playlist.
5. The route receives the returned songs and formats a JSON response containing two fields: `songs` and `count`.
6. The `count` field is calculated using `len(songs)`.
7. If the service raises a ValueError, the route returns a JSON error response with HTTP status 404.


### Architectural Patterns

The application uses Flask Blueprints to organize related endpoints. For example, routes/playlists.py defines a playlists_bp Blueprint containing endpoints for creating playlists, retrieving playlist details, listing songs, and adding songs.

Database relationships are managed through SQLAlchemy. The playlist_entries association table connects playlists and songs while also storing metadata such as song position and the user who added each song.

The routes use jsonify() to return JSON responses and handle ValueError exceptions by returning appropriate HTTP error codes.


## Root Cause Analysis

### Issue #5 — The Last Song in a Playlist Never Shows Up

**1. How I Reproduced It**

I ran the existing playlist tests using:

`python -m pytest tests/test_playlists.py -v`

Before modifying the code, two tests failed:
- test_playlist_returns_all_songs
- test_playlist_returns_songs_in_order

The tests confirmed that the playlist retrieval function was not returning every song in the playlist.

**2. How I Found the Root Cause**

I began by reviewing the application structure in README.md and tracing the playlist retrieval process.

I examined routes/playlists.py and identified the get_songs() endpoint, which calls get_playlist_songs() in services/playlist_service.py.

After examining that service function, I identified the list slicing operation in its return statement. This explained why the last song was missing.

**3. The Root Cause**

The get_playlist_songs() function correctly queried the database and ordered songs by their playlist position.

However, its return statement used:

`return [song.to_dict() for song in songs[:-1]]`

The Python slice `[:-1]` excludes the final element of a list.

Because the songs were ordered by position, the final element represented the most recently added song. Consequently, the function consistently omitted that song from its response.

**4. My Fix**

I removed the list slicing operation and changed the return statement to:

`return [song.to_dict() for song in songs]`

This allows the function to return every song retrieved from the database while preserving the existing playlist order.

No other application functionality needed to be changed.

**5. Side-Effect Check**

After implementing the fix, I reran:

`python -m pytest tests/test_playlists.py -v`

All three tests passed:
- test_playlist_returns_all_songs
- test_playlist_returns_songs_in_order
- test_empty_playlist_returns_empty_list

This verified that the service returns all playlist songs, maintains their correct ordering, and handles empty playlists.


### Issue #2 — Friends Listening Now Shows People From Yesterday

**1. How I Reproduced It**

I created a regression test in `tests/test_feed_today.py` to simulate a friend listening to a song at 11 PM yesterday and another user checking the feed at 9 AM today.

Before modifying the service, the test failed because yesterday's listening activity appeared in the feed.

The failure confirmed that the application was including activity from the previous calendar day.

**2. How I Found the Root Cause**

I reviewed `routes/feed.py` and traced the `/feed/<user_id>/listening-now` endpoint to `get_friends_listening_now()` in `services/feed_service.py`.

I examined the filtering logic and identified that it calculated the cutoff by subtracting 24 hours from the current time.

This explained why listening events from yesterday were still being returned.

**3. The Root Cause**

The service originally used:

`RECENT_THRESHOLD = timedelta(hours=24)`

and calculated the cutoff using:

`cutoff = datetime.now(timezone.utc) - RECENT_THRESHOLD`

This created a rolling 24-hour window rather than a calendar-day filter.

For example, when checking the feed at 9 AM, a listening event from 11 PM yesterday was still within the previous 24 hours.

As a result, the application incorrectly displayed yesterday's activity.

**4. My Fix**

I updated `get_friends_listening_now()` to calculate the beginning of the current UTC calendar day:

`now = datetime.now(timezone.utc)`

`start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)`

I then updated the database query to include listening events occurring between `start_of_today` and `now`.

This ensures that only today's listening activity appears in the feed.

The general activity feed was left unchanged.

**5. Side-Effect Check**

I created two regression tests using an isolated SQLite test database:

- `test_listening_now_excludes_yesterday`
- `test_listening_now_includes_today`

I ran:

`python -m pytest tests/test_feed_today.py -v`

Both tests passed.

This confirmed that yesterday's listening activity is excluded while today's listening activity is still displayed correctly.

The tests also use a temporary database to avoid modifying the application's original data.


