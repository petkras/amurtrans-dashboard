"""Create reproducible demonstration orders for the lab dashboard."""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

DEST = Path(__file__).with_name("demo_orders.csv")
CITIES = ["Комсомольск-на-Амуре", "Хабаровск", "Амурск", "Советская Гавань"]
STATUSES = ["Закрыт", "Доставлен", "В пути", "Запланирован", "На согласовании"]


def main() -> None:
    rng = random.Random(8)
    with DEST.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["order_id", "created_at", "origin", "destination", "status", "carrier", "planned_hours", "actual_hours", "price_rub", "documents_complete"])
        for index in range(1, 121):
            created = date(2026, 1, 1) + timedelta(days=rng.randrange(240))
            origin, destination = rng.sample(CITIES, 2)
            status = rng.choices(STATUSES, weights=[42, 20, 16, 13, 9])[0]
            planned = rng.choice([8, 12, 16, 24, 36, 48])
            completed = status in {"Доставлен", "Закрыт"}
            actual = max(3, planned + rng.randint(-5, 12)) if completed else ""
            writer.writerow([
                f"AT-{index:04d}", created.isoformat(), origin, destination, status,
                rng.choice(["Собственный парк", "Перевозчик А", "Перевозчик Б"]),
                planned, actual, rng.randrange(12, 95) * 1000,
                "Да" if status == "Закрыт" else "Нет",
            ])
    print(f"Wrote {DEST}")


if __name__ == "__main__":
    main()
