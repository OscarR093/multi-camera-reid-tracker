"""Generate fake historical hourly counts for dashboard testing."""
import sys
import os
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage.sqlite_client import SQLiteClient


def backfill(db_path: str = "data/persons.db", hours: int = 48):
    sql = SQLiteClient(db_path)
    now = datetime.now()

    base = random.randint(5, 15)

    for i in range(hours, -1, -1):
        dt = now - timedelta(hours=i)
        hour_str = dt.strftime("%Y-%m-%d %H:00")

        for cam_id in ["cam_0", "cam_1"]:
            if 8 <= dt.hour <= 21:
                peak_factor = 1.0 + 0.5 * random.random()
                variation = random.randint(-3, 5)
            elif 22 <= dt.hour <= 23 or 0 <= dt.hour <= 6:
                peak_factor = 0.2 + 0.3 * random.random()
                variation = random.randint(-1, 2)
            else:
                peak_factor = 0.4 + 0.4 * random.random()
                variation = random.randint(-2, 3)

            count = max(1, int(base * peak_factor) + variation)
            sql.save_hourly_count(cam_id, hour_str, count)

    print(f"Backfilled {hours + 1} hours x 2 cameras = {(hours + 1) * 2} records")


if __name__ == "__main__":
    backfill()
