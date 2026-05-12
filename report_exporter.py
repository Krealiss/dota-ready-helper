# -*- coding: utf-8 -*-
"""Модуль експорту звітів у різних форматах."""
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from stats_tracker import Statistics
from logger import logger

class ReportExporter:
    """Клас для експорту звітів."""

    def __init__(self, stats: Statistics):
        self.stats = stats

    def export_csv(self, output_path: Path, include_sessions: bool = True):
        """
        Експортувати статистику у CSV.

        Args:
            output_path: Шлях до вихідного файлу
            include_sessions: Включити детальну інформацію про сесії
        """
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # Заголовок
                writer.writerow(['Dota Ready Helper - Статистика'])
                writer.writerow(['Згенеровано:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                writer.writerow([])

                # Загальна статистика
                summary = self.stats.get_summary()
                writer.writerow(['Загальна статистика'])
                writer.writerow(['Показник', 'Значення'])
                writer.writerow(['Всього прийнято матчів', summary['total_matches_accepted']])
                writer.writerow(['Всього пропущено', summary['total_matches_missed']])
                writer.writerow(['Середній час очікування (с)', f"{summary['average_wait_time']:.1f}"])
                writer.writerow(['Сьогодні прийнято', summary['today_accepted']])
                writer.writerow(['Сьогодні пропущено', summary['today_missed']])
                writer.writerow([])

                # Детальна інформація про сесії
                if include_sessions and self.stats.data['sessions']:
                    writer.writerow(['Історія матчів'])
                    writer.writerow([
                        'Дата/Час', 'Початок пошуку', 'Матч знайдено',
                        'Прийнято', 'Час очікування (с)', 'ID сесії'
                    ])

                    for session in self.stats.data['sessions']:
                        writer.writerow([
                            session['timestamp'],
                            session['search_started'],
                            session['match_found'],
                            'Так' if session['accepted'] else 'Ні',
                            f"{session['wait_time_seconds']:.1f}",
                            session['session_id']
                        ])

            logger.info(f"Звіт експортовано у CSV: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Помилка експорту CSV: {e}")
            return False

    def export_json(self, output_path: Path, pretty: bool = True):
        """
        Експортувати статистику у JSON.

        Args:
            output_path: Шлях до вихідного файлу
            pretty: Форматувати JSON для читабельності
        """
        try:
            data = {
                'generated_at': datetime.now().isoformat(),
                'summary': self.stats.get_summary(),
                'daily_stats': self.stats.get_daily_stats(days=30),
                'all_sessions': self.stats.data['sessions']
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)

            logger.info(f"Звіт експортовано у JSON: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Помилка експорту JSON: {e}")
            return False

    def export_html(self, output_path: Path):
        """
        Експортувати статистику у HTML.

        Args:
            output_path: Шлях до вихідного файлу
        """
        try:
            summary = self.stats.get_summary()
            daily = self.stats.get_daily_stats(days=7)

            html = f"""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dota Ready Helper - Статистика</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #1a1a2e;
            color: #eee;
        }}
        .header {{
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #16213e;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #4ecca3;
        }}
        .stat-label {{
            color: #aaa;
            margin-top: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #16213e;
            border-radius: 10px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #0f3460;
        }}
        th {{
            background: #0f3460;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Dota Ready Helper</h1>
        <p>Статистика згенерована: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{summary['total_matches_accepted']}</div>
            <div class="stat-label">Всього прийнято матчів</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{summary['average_wait_time']:.1f}с</div>
            <div class="stat-label">Середній час очікування</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{summary['today_accepted']}</div>
            <div class="stat-label">Прийнято сьогодні</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{summary['current_session_matches']}</div>
            <div class="stat-label">У поточній сесії</div>
        </div>
    </div>

    <h2>📅 Статистика за останні 7 днів</h2>
    <table>
        <thead>
            <tr>
                <th>Дата</th>
                <th>Прийнято</th>
                <th>Пропущено</th>
                <th>Середній час (с)</th>
            </tr>
        </thead>
        <tbody>
"""

            for day in daily:
                html += f"""
            <tr>
                <td>{day['date']}</td>
                <td>{day['matches_accepted']}</td>
                <td>{day['matches_missed']}</td>
                <td>{day.get('average_wait_time', 0):.1f}</td>
            </tr>
"""

            html += """
        </tbody>
    </table>

    <div class="footer">
        <p>Dota Ready Helper v2.1</p>
    </div>
</body>
</html>
"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            logger.info(f"Звіт експортовано у HTML: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Помилка експорту HTML: {e}")
            return False

    def export_text(self, output_path: Path):
        """
        Експортувати статистику у текстовий файл.

        Args:
            output_path: Шлях до вихідного файлу
        """
        try:
            summary = self.stats.get_summary()
            daily = self.stats.get_daily_stats(days=7)

            text = f"""
╔══════════════════════════════════════════════════════════╗
║          Dota Ready Helper - Статистика                  ║
╚══════════════════════════════════════════════════════════╝

Згенеровано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

═══════════════════════════════════════════════════════════
  ЗАГАЛЬНА СТАТИСТИКА
═══════════════════════════════════════════════════════════

  Всього прийнято матчів:     {summary['total_matches_accepted']}
  Всього пропущено:           {summary['total_matches_missed']}
  Середній час очікування:    {summary['average_wait_time']:.1f}с

  Сьогодні прийнято:          {summary['today_accepted']}
  Сьогодні пропущено:         {summary['today_missed']}

  У поточній сесії:           {summary['current_session_matches']}

═══════════════════════════════════════════════════════════
  СТАТИСТИКА ЗА ОСТАННІ 7 ДНІВ
═══════════════════════════════════════════════════════════

"""

            for day in daily:
                text += f"""
  {day['date']}
    Прийнято:      {day['matches_accepted']}
    Пропущено:     {day['matches_missed']}
    Середній час:  {day.get('average_wait_time', 0):.1f}с
"""

            text += """
═══════════════════════════════════════════════════════════

Dota Ready Helper v2.1
"""

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)

            logger.info(f"Звіт експортовано у TXT: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Помилка експорту TXT: {e}")
            return False

    def export_all(self, output_dir: Path):
        """
        Експортувати у всі формати.

        Args:
            output_dir: Директорія для збереження файлів
        """
        output_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        results = {
            'csv': self.export_csv(output_dir / f'stats_{timestamp}.csv'),
            'json': self.export_json(output_dir / f'stats_{timestamp}.json'),
            'html': self.export_html(output_dir / f'stats_{timestamp}.html'),
            'txt': self.export_text(output_dir / f'stats_{timestamp}.txt')
        }

        success_count = sum(results.values())
        logger.info(f"Експортовано {success_count}/4 форматів")

        return results
