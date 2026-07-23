"""
One-off script to clean up duplicate ActiveUpgrade rows.
Removes older duplicates for the same user/building_name/target_level
where is_completed=False, keeping only the most recent one.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.WARNING)

from sqlalchemy import select
from database.connection import async_session
from database.models import ActiveUpgrade


async def deduplicate():
    async with async_session() as session:
        result = await session.execute(
            select(ActiveUpgrade).where(ActiveUpgrade.is_completed == False)
        )
        rows = result.scalars().all()

        seen: dict[tuple[int, str, int], list[ActiveUpgrade]] = {}
        for row in rows:
            key = (row.user_id, row.building_name, row.target_level)
            seen.setdefault(key, []).append(row)

        removed = 0
        for key, dupes in seen.items():
            if len(dupes) <= 1:
                continue
            dupes.sort(key=lambda r: r.end_time, reverse=True)
            for old_row in dupes[1:]:
                old_row.is_completed = True
                removed += 1
                print(f"  Removed duplicate: user={old_row.user_id}, "
                      f"building={old_row.building_name}, "
                      f"level={old_row.target_level}")

        await session.commit()
        print(f"\nDone. Marked {removed} duplicate row(s) as completed.")

if __name__ == "__main__":
    asyncio.run(deduplicate())
