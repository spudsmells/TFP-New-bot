from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Platform detection patterns
SPOTIFY_RE = re.compile(r"https?://open\.spotify\.com/(track|album|playlist)/(\w+)")
APPLE_MUSIC_RE = re.compile(r"https?://music\.apple\.com/\S+")
SOUNDCLOUD_RE = re.compile(r"https?://(www\.)?soundcloud\.com/\S+")
TIDAL_RE = re.compile(r"https?://(www\.|listen\.)?tidal\.com/\S+")
DEEZER_RE = re.compile(r"https?://(www\.)?deezer\.com/\S+")

PLATFORM_PATTERNS = {
    "spotify": SPOTIFY_RE,
    "apple_music": APPLE_MUSIC_RE,
    "soundcloud": SOUNDCLOUD_RE,
    "tidal": TIDAL_RE,
    "deezer": DEEZER_RE,
}


@dataclass
class ConversionResult:
    success: bool
    platform: str
    artist: str | None = None
    title: str | None = None
    youtube_url: str | None = None
    error: str | None = None


def detect_platform(url: str) -> str | None:
    """Detect which music platform a URL belongs to."""
    for platform, pattern in PLATFORM_PATTERNS.items():
        if pattern.search(url):
            return platform
    return None


def extract_music_urls(text: str) -> list[tuple[str, str]]:
    """Extract all music platform URLs from text. Returns [(url, platform)]."""
    results = []
    for platform, pattern in PLATFORM_PATTERNS.items():
        for match in pattern.finditer(text):
            results.append((match.group(0), platform))
    return results


async def get_spotify_metadata(url: str, client_id: str | None, client_secret: str | None) -> tuple[str | None, str | None]:
    """Extract artist and title from Spotify URL using spotipy."""
    if not client_id or not client_secret:
        return None, None

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        ))

        match = SPOTIFY_RE.search(url)
        if not match:
            return None, None

        content_type, content_id = match.group(1), match.group(2)
        if content_type == "track":
            track = sp.track(content_id)
            artist = track["artists"][0]["name"] if track.get("artists") else None
            title = track.get("name")
            return artist, title
    except Exception:
        logger.exception("Spotify metadata extraction failed")

    return None, None


async def search_youtube(query: str) -> str | None:
    """Search YouTube using yt-dlp (avoids API quota)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "yt-dlp",
            f"ytsearch1:{query}",
            "--get-id",
            "--no-warnings",
            "--no-playlist",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        video_id = stdout.decode().strip()
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
    except asyncio.TimeoutError:
        logger.warning("yt-dlp search timed out for: %s", query)
    except Exception:
        logger.exception("yt-dlp search failed for: %s", query)
    return None


async def convert(
    url: str,
    platform: str,
    spotify_client_id: str | None = None,
    spotify_client_secret: str | None = None,
) -> ConversionResult:
    """Convert a music platform URL to a YouTube URL."""
    artist, title = None, None

    # Try to get metadata
    if platform == "spotify":
        artist, title = await get_spotify_metadata(url, spotify_client_id, spotify_client_secret)

    # Build search query
    if artist and title:
        query = f"{artist} - {title}"
    else:
        # Fallback: use the URL itself as a search hint
        query = url

    youtube_url = await search_youtube(query)

    if youtube_url:
        return ConversionResult(
            success=True, platform=platform,
            artist=artist, title=title, youtube_url=youtube_url,
        )
    return ConversionResult(
        success=False, platform=platform,
        artist=artist, title=title, error="YouTube search returned no results",
    )
