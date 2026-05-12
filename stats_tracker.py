# -*- coding: utf-8 -*-
"""Модуль статистики для відстеження роботи бота."""
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

from logger import logger

@dataclass
class MatchSession:
    """Інформація про одну сесію пошуку матчу."""
    timestamp: str
    search_started: str
    match_found: str
    accepted: bool
    wait_time_seconds: float
    session_id: str

@dataclass
class DailyStats:
    """Статистика за день."""
    date: str
    matches_accepted: int
    matches_missed: int
    total_wait_time: float
    average_wait_time: float
    sessions: List[MatchSession]

class Statistics:
    """Клас для збору та аналізу статистики."""

    def __init__(self, stats_dir: Optional[Path] = None):
        self.stats_dir = stats_dir or Path(__file__).parent / "stats"
        self.stats_dir.mkdir(exist_ok=True)

        self.stats_file = self.stats_dir / "statistics.json"
        self.current_session_file = self.stats_dir / "current_session.json"

        self.data = self._load_stats()
        self.current_session = self._load_current_session()

    def _load_stats(self) -> Dict:
        """Завантажити статистику з файлу."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Помилка завантаження статистики: {e}")
                return self._init_stats()
        return self._init_stats()

    def _init_stats(self) -> Dict:
        """Ініціалізувати порожню статистику."""
        return {
            "total_matches_accepted": 0,
            "total_matches_missed": 0,
            "total_sessions": 0,
            "total_runtime_hours": 0.0,
            "first_run": datetime.now().isoformat(),
            "last_run": datetime.now().isoformat(),
            "daily_stats": {},
            "sessions": []
        }

    def _save_stats(self):
        """Зберегти статистику у файл."""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Помилка збереження статистики: {e}")

    def _load_current_session(self) -> Dict:
        """Завантажити поточну сесію."""
        if self.current_session_file.exists():
            try:
                with open(self.current_session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "started_at": datetime.now().isoformat(),
            "search_started_at": None,
            "matches_in_session": 0
        }

    def _save_current_session(self):
        """Зберегти поточну сесію."""
        try:
            with open(self.current_session_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_session, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Помилка збереження сесії: {e}")

    def start_search(self):
        """Зафіксувати початок пошуку матчу."""
        self.current_session["search_started_at"] = datetime.now().isoformat()
        self._save_current_session()
        logger.debug("Статистика: початок пошуку")

    def match_accepted(self):
        """Зафіксувати прийняття матчу."""
        if not self.current_session.get("search_started_at"):
            logger.warning("Матч прийнято, але пошук не було розпочато")
            return

        now = datetime.now()
        search_started = datetime.fromisoformat(self.current_session["search_started_at"])
        wait_time = (now - search_started).total_seconds()

        # Створити запис про матч
        match_record = {
            "timestamp": now.isoformat(),
            "search_started": self.current_session["search_started_at"],
            "match_found": now.isoformat(),
            "accepted": True,
            "wait_time_seconds": wait_time,
            "session_id": self.current_session["session_id"]
        }

        # Оновити загальну статистику
        self.data["total_matches_accepted"] += 1
        self.data["total_sessions"] += 1
        self.data["last_run"] = now.isoformat()
        self.data["sessions"].append(match_record)

        # Оновити денну статистику
        today = now.strftime("%Y-%m-%d")
        if today not in self.data["daily_stats"]:
            self.data["daily_stats"][today] = {
                "date": today,
                "matches_accepted": 0,
                "matches_missed": 0,
                "total_wait_time": 0.0,
                "sessions": []
            }

        daily = self.data["daily_stats"][today]
        daily["matches_accepted"] += 1
        daily["total_wait_time"] += wait_time
        daily["sessions"].append(match_record)

        # Оновити поточну сесію
        self.current_session["matches_in_session"] += 1
        self.current_session["search_started_at"] = None

        self._save_stats()
        self._save_current_session()

        logger.info(f"Статистика: матч прийнято за {wait_time:.1f}с")

    def match_missed(self):
        """Зафіксувати пропущений матч."""
        self.data["total_matches_missed"] += 1

        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.data["daily_stats"]:
            self.data["daily_stats"][today] = {
                "date": today,
                "matches_accepted": 0,
                "matches_missed": 0,
                "total_wait_time": 0.0,
                "sessions": []
            }

        self.data["daily_stats"][today]["matches_missed"] += 1
        self._save_stats()

        logger.info("Статистика: матч пропущено")

    def get_summary(self) -> Dict:
        """Отримати загальну статистику."""
        total_accepted = self.data["total_matches_accepted"]
        total_missed = self.data["total_matches_missed"]

        # Середній час очікування
        if self.data["sessions"]:
            avg_wait = sum(s["wait_time_seconds"] for s in self.data["sessions"]) / len(self.data["sessions"])
        else:
            avg_wait = 0.0

        # Статистика за сьогодні
        today = datetime.now().strftime("%Y-%m-%d")
        today_stats = self.data["daily_stats"].get(today, {
            "matches_accepted": 0,
            "matches_missed": 0,
            "total_wait_time": 0.0
        })

        return {
            "total_matches_accepted": total_accepted,
            "total_matches_missed": total_missed,
            "total_sessions": self.data["total_sessions"],
            "average_wait_time": avg_wait,
            "today_accepted": today_stats["matches_accepted"],
            "today_missed": today_stats["matches_missed"],
            "current_session_matches": self.current_session["matches_in_session"],
            "first_run": self.data["first_run"],
            "last_run": self.data["last_run"]
        }

    def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Отримати статистику за останні N днів."""
        result = []
        today = datetime.now().date()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            stats = self.data["daily_stats"].get(date, {
                "date": date,
                "matches_accepted": 0,
                "matches_missed": 0,
                "total_wait_time": 0.0,
                "sessions": []
            })

            # Розрахувати середній час
            if stats["sessions"]:
                stats["average_wait_time"] = stats["total_wait_time"] / len(stats["sessions"])
            else:
                stats["average_wait_time"] = 0.0

            result.append(stats)

        return list(reversed(result))

    def get_formatted_summary(self) -> str:
        """Отримати форматований текст статистики."""
        summary = self.get_summary()

        text = "📊 Статистика Dota Ready Helper\n"
        text += "=" * 40 + "\n\n"

        text += "🎮 Загальна статистика:\n"
        text += f"  • Прийнято матчів: {summary['total_matches_accepted']}\n"
        text += f"  • Пропущено матчів: {summary['total_matches_missed']}\n"
        text += f"  • Середній час очікування: {summary['average_wait_time']:.1f}с\n\n"

        text += "📅 Сьогодні:\n"
        text += f"  • Прийнято: {summary['today_accepted']}\n"
        text += f"  • Пропущено: {summary['today_missed']}\n\n"

        text += "🔄 Поточна сесія:\n"
        text += f"  • Матчів у сесії: {summary['current_session_matches']}\n"

        return text

    def export_to_csv(self, output_file: Path):
        """Експортувати статистику у CSV."""
        import csv

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Дата/Час", "Початок пошуку", "Знайдено",
                "Прийнято", "Час очікування (с)", "ID сесії"
            ])

            for session in self.data["sessions"]:
                writer.writerow([
                    session["timestamp"],
                    session["search_started"],
                    session["match_found"],
                    "Так" if session["accepted"] else "Ні",
                    f"{session['wait_time_seconds']:.1f}",
                    session["session_id"]
                ])

        logger.info(f"Статистику експортовано у {output_file}")

    def export_to_json(self, output_file: Path):
        """Експортувати статистику у JSON."""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        logger.info(f"Статистику експортовано у {output_file}")

    def reset_stats(self):
        """Скинути всю статистику."""
        self.data = self._init_stats()
        self.current_session = {
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "started_at": datetime.now().isoformat(),
            "search_started_at": None,
            "matches_in_session": 0
        }
        self._save_stats()
        self._save_current_session()
        logger.info("Статистику скинуто")
