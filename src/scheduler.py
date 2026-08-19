"""
Scheduler for RSS feed updates with intelligent frequency control.
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import FeedConfig, UpdateFrequency

logger = logging.getLogger(__name__)


class ScheduleType(str, Enum):
    """Types of update schedules."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WEEKDAYS = "weekdays"
    WEEKEND = "weekend"
    CUSTOM = "custom"


class FeedScheduler:
    """Manages scheduling of RSS feed updates."""

    def __init__(self, history_file: str = "data/fetch_history.json"):
        """
        Initialize the scheduler.

        Args:
            history_file: Path to fetch history file
        """
        self.history_file = Path(history_file)
        self.history: Dict[str, Any] = self._load_history()

    def _load_history(self) -> Dict[str, Any]:
        """Load fetch history from JSON file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                return {
                    "feeds": {},
                    "metadata": {"created": datetime.now().isoformat()},
                }
        except Exception as e:
            logger.error(f"Failed to load fetch history: {e}")
            return {"feeds": {}, "metadata": {"created": datetime.now().isoformat()}}

    def _save_history(self):
        """Save fetch history to JSON file."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save fetch history: {e}")

    def should_fetch_feed(self, feed: FeedConfig) -> bool:
        """
        Determine if a feed should be fetched based on its update frequency.

        Args:
            feed: Feed configuration

        Returns:
            True if feed should be fetched, False otherwise
        """
        feed_name = feed.name

        # Get feed history
        feed_history = self.history["feeds"].get(feed_name, {})

        # If no history, always fetch
        if not feed_history:
            return True

        # Check last fetch time
        last_fetch_str = feed_history.get("last_fetch")
        if not last_fetch_str:
            return True

        try:
            last_fetch = datetime.fromisoformat(last_fetch_str)
        except ValueError:
            return True

        # Check update frequency configuration (UpdateFrequency enum)
        freq = feed.update_frequency

        if freq == UpdateFrequency.DAILY:
            return self._should_fetch_daily(last_fetch)
        if freq == UpdateFrequency.WEEKDAY:
            return self._should_fetch_weekdays(last_fetch)
        if freq == UpdateFrequency.WEEKLY:
            return self._should_fetch_weekly(last_fetch, [6])  # Sunday
        if freq == UpdateFrequency.MONTHLY:
            return self._should_fetch_monthly(last_fetch)
        if freq == UpdateFrequency.SEASON:
            return self._should_fetch_season(last_fetch)
        # Unknown / default → daily
        logger.warning(f"Unknown update_frequency {freq!r} for feed {feed_name}")
        return self._should_fetch_daily(last_fetch)

    def _should_fetch_daily(self, last_fetch: datetime) -> bool:
        """Check if feed should be fetched daily."""
        today = datetime.now().date()
        last_fetch_date = last_fetch.date()
        return last_fetch_date < today

    def _should_fetch_weekly(self, last_fetch: datetime, days: List[int]) -> bool:
        """
        Check if feed should be fetched weekly on specific days.

        Args:
            last_fetch: Last fetch time
            days: List of days (0=Monday, 6=Sunday)
        """
        today = datetime.now()
        last_fetch_date = last_fetch.date()

        # If last fetch was today, don't fetch again
        if last_fetch_date >= today.date():
            return False

        # Check if today is one of the specified days
        today_weekday = today.weekday()
        return today_weekday in days

    def _should_fetch_weekdays(self, last_fetch: datetime) -> bool:
        """Check if feed should be fetched on weekdays (Mon-Fri)."""
        today = datetime.now()
        last_fetch_date = last_fetch.date()

        # If last fetch was today, don't fetch again
        if last_fetch_date >= today.date():
            return False

        # Check if today is a weekday (0=Monday, 4=Friday)
        today_weekday = today.weekday()
        return today_weekday < 5  # Monday-Friday

    def _should_fetch_weekend(self, last_fetch: datetime) -> bool:
        """Check if feed should be fetched on weekends (Sat-Sun)."""
        today = datetime.now()
        last_fetch_date = last_fetch.date()

        # If last fetch was today, don't fetch again
        if last_fetch_date >= today.date():
            return False

        # Check if today is a weekend (5=Saturday, 6=Sunday)
        today_weekday = today.weekday()
        return today_weekday >= 5

    def _should_fetch_monthly(self, last_fetch: datetime) -> bool:
        """Check if feed should be fetched on the 1st of the month."""
        today = datetime.now()
        last_fetch_date = last_fetch.date()
        if last_fetch_date >= today.date():
            return False
        return today.day == 1

    def _should_fetch_season(self, last_fetch: datetime) -> bool:
        """Check if feed should be fetched on quarter start (1/1, 4/1, 7/1, 10/1)."""
        today = datetime.now()
        last_fetch_date = last_fetch.date()
        if last_fetch_date >= today.date():
            return False
        return today.month % 3 == 1 and today.day == 1

    def _should_fetch_custom(self, last_fetch: datetime, schedule: str) -> bool:
        """
        Check if feed should be fetched based on custom schedule.

        Args:
            last_fetch: Last fetch time
            schedule: Custom schedule string (e.g., "mon,wed,fri")
        """
        today = datetime.now()
        last_fetch_date = last_fetch.date()

        # If last fetch was today, don't fetch again
        if last_fetch_date >= today.date():
            return False

        # Parse custom schedule
        days_map = {
            "mon": 0,
            "monday": 0,
            "tue": 1,
            "tuesday": 1,
            "wed": 2,
            "wednesday": 2,
            "thu": 3,
            "thursday": 3,
            "fri": 4,
            "friday": 4,
            "sat": 5,
            "saturday": 5,
            "sun": 6,
            "sunday": 6,
        }

        today_weekday = today.weekday()

        # Split schedule by commas and normalize
        schedule_days = [day.strip().lower() for day in schedule.split(",")]

        # Check if today matches any of the scheduled days
        for day_str in schedule_days:
            if day_str in days_map and days_map[day_str] == today_weekday:
                return True

        return False

    def record_fetch(self, feed_name: str, papers_fetched: int = 0):
        """
        Record a feed fetch event.

        Args:
            feed_name: Name of the feed
            papers_fetched: Number of papers fetched
        """
        now = datetime.now()

        if feed_name not in self.history["feeds"]:
            self.history["feeds"][feed_name] = {
                "first_fetch": now.isoformat(),
                "last_fetch": now.isoformat(),
                "total_fetches": 1,
                "total_papers": papers_fetched,
                "fetch_history": [],
            }
        else:
            feed_history = self.history["feeds"][feed_name]
            feed_history["last_fetch"] = now.isoformat()
            feed_history["total_fetches"] = feed_history.get("total_fetches", 0) + 1
            feed_history["total_papers"] = (
                feed_history.get("total_papers", 0) + papers_fetched
            )
            feed_history["fetch_history"].append(
                {"timestamp": now.isoformat(), "papers_fetched": papers_fetched}
            )

            # Keep only last 100 fetch events
            if len(feed_history["fetch_history"]) > 100:
                feed_history["fetch_history"] = feed_history["fetch_history"][-100:]

        self._save_history()
        logger.debug(f"Recorded fetch for {feed_name}: {papers_fetched} papers")

    def get_next_scheduled_time(self, feed: FeedConfig) -> Optional[datetime]:
        """
        Get the next scheduled fetch time for a feed.

        Args:
            feed: Feed configuration

        Returns:
            Next scheduled datetime or None if unknown
        """
        now = datetime.now()
        feed_history = self.history["feeds"].get(feed.name, {})

        if not feed_history:
            return now

        last_fetch_str = feed_history.get("last_fetch")
        if not last_fetch_str:
            return now

        try:
            last_fetch = datetime.fromisoformat(last_fetch_str)
        except ValueError:
            return now

        freq = feed.update_frequency
        if freq == UpdateFrequency.DAILY:
            return last_fetch + timedelta(days=1)
        if freq == UpdateFrequency.WEEKDAY:
            return self._next_weekday(last_fetch)
        if freq == UpdateFrequency.WEEKLY:
            return self._next_weekly_day(last_fetch, [6])  # Sunday
        if freq == UpdateFrequency.MONTHLY:
            return self._next_monthly(last_fetch)
        if freq == UpdateFrequency.SEASON:
            return self._next_season(last_fetch)
        # Unknown schedule, default to tomorrow
        return last_fetch + timedelta(days=1)

    def _next_weekly_day(self, last_fetch: datetime, days: List[int]) -> datetime:
        """Get next scheduled day for weekly updates."""
        if not days:
            return last_fetch + timedelta(days=7)

        today = datetime.now()
        today_weekday = today.weekday()

        # Find next scheduled day
        for day in sorted(days):
            if day > today_weekday:
                days_ahead = day - today_weekday
                return today + timedelta(days=days_ahead)

        # If no day later this week, use first day next week
        days_ahead = (7 - today_weekday) + days[0]
        return today + timedelta(days=days_ahead)

    def _next_weekday(self, last_fetch: datetime) -> datetime:
        """Get next weekday."""
        today = datetime.now()
        today_weekday = today.weekday()

        if today_weekday < 4:  # Monday-Thursday
            return today + timedelta(days=1)
        elif today_weekday == 4:  # Friday
            return today + timedelta(days=3)  # Next Monday
        else:  # Weekend
            # Already weekend, next Monday
            days_ahead = 7 - today_weekday
            return today + timedelta(days=days_ahead)

    def _next_weekend(self, last_fetch: datetime) -> datetime:
        """Get next weekend."""
        today = datetime.now()
        today_weekday = today.weekday()

        if today_weekday < 5:  # Monday-Friday
            days_ahead = 5 - today_weekday  # Next Saturday
            return today + timedelta(days=days_ahead)
        else:  # Already weekend
            return today + timedelta(days=7)  # Next weekend

    def _next_monthly(self, last_fetch: datetime) -> datetime:
        """Get next 1st of the month."""
        today = datetime.now()
        if today.day == 1:
            return today
        year = today.year + (1 if today.month == 12 else 0)
        month = (today.month % 12) + 1
        return datetime(year, month, 1)

    def _next_season(self, last_fetch: datetime) -> datetime:
        """Get next quarter start (1st of Jan/Apr/Jul/Oct)."""
        today = datetime.now()
        if today.month % 3 == 1 and today.day == 1:
            return today
        for m in (4, 7, 10):
            if m > today.month:
                return datetime(today.year, m, 1)
        return datetime(today.year + 1, 1, 1)

    def filter_feeds_to_fetch(self, feeds: List[FeedConfig]) -> List[FeedConfig]:
        """
        Filter feeds to only those that should be fetched today.

        Args:
            feeds: List of all feed configurations

        Returns:
            List of feeds that should be fetched today
        """
        feeds_to_fetch = []

        for feed in feeds:
            if self.should_fetch_feed(feed):
                feeds_to_fetch.append(feed)
                logger.info(f"Feed scheduled for fetch today: {feed.name}")
            else:
                next_time = self.get_next_scheduled_time(feed)
                if next_time:
                    next_str = next_time.strftime("%Y-%m-%d %H:%M")
                    logger.debug(f"Feed {feed.name} not scheduled until {next_str}")

        logger.info(f"Filtered {len(feeds)} feeds to {len(feeds_to_fetch)} for today")
        return feeds_to_fetch

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        total_feeds = len(self.history.get("feeds", {}))
        total_fetches = sum(
            feed_data.get("total_fetches", 0)
            for feed_data in self.history.get("feeds", {}).values()
        )
        total_papers = sum(
            feed_data.get("total_papers", 0)
            for feed_data in self.history.get("feeds", {}).values()
        )

        # Most active feeds
        feeds = self.history.get("feeds", {})
        most_active = sorted(
            [(name, data.get("total_fetches", 0)) for name, data in feeds.items()],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Recently fetched feeds
        recent = []
        for name, data in feeds.items():
            last_fetch = data.get("last_fetch")
            if last_fetch:
                recent.append((name, last_fetch))
        recent.sort(key=lambda x: x[1], reverse=True)
        recent = recent[:10]

        return {
            "total_feeds": total_feeds,
            "total_fetches": total_fetches,
            "total_papers": total_papers,
            "most_active_feeds": most_active,
            "recently_fetched": recent[:5],
        }


# Global scheduler instance
_global_scheduler: Optional[FeedScheduler] = None


def get_scheduler() -> FeedScheduler:
    """
    Get the global scheduler instance.

    Returns:
        FeedScheduler instance
    """
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = FeedScheduler()
    return _global_scheduler
