from flask import Flask, render_template
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user

app = Flask(__name__)

app.config.from_pyfile('config.py')
 
db.init_app(app)
migrate = Migrate(app, db)
 
init_login_manager(app)

# ── Mock data (заменить на БД в реальном приложении) ──────────────────────────

LEVELS = [
    {
        "id": 1,
        "slug": "basic",
        "title": "Базовый",
        "subtitle": "Гармония + Эмоция",
        "badge_emoji": "🟢",
        "badge_color": "lv1",
        "description": "Подберите палитру для передачи заданной эмоции. Подсказки активны.",
        "tools": ["Цветовой круг", "Типы палитр", "Подсказки"],
        "accent_color": "#6bffcc",
        "accent_rgba": "rgba(107,255,204,.12)",
    },
    {
        "id": 2,
        "slug": "advanced",
        "title": "Продвинутый",
        "subtitle": "Интуиция и стиль",
        "badge_emoji": "🟣",
        "badge_color": "lv2",
        "description": "Создайте палитру под абстрактное стилевое задание без подсказок.",
        "tools": ["Цветовой круг", "WCAG", "Без подсказок"],
        "accent_color": "#c8b4ff",
        "accent_rgba": "rgba(200,180,255,.12)",
    },
    {
        "id": 3,
        "slug": "expert",
        "title": "Экспертный",
        "subtitle": "Доступность (WCAG)",
        "badge_emoji": "🟠",
        "badge_color": "lv3",
        "description": "Обеспечьте контрастность WCAG 2.1 AA для людей с нарушениями зрения.",
        "tools": ["Цветовой круг", "Симулятор", "WCAG AA"],
        "accent_color": "#ff9f6b",
        "accent_rgba": "rgba(255,159,107,.12)",
    },
]

TASKS = {
    1: {
        "level_id": 1,
        "title": "Спокойствие",
        "emoji": "🌊",
        "description": "Назначьте 5 цветов по ролям, передающих умиротворение и тишину.",
        "requirements": [
            {"text": "Фон и поверхность заданы", "done": True},
            {"text": "Акцент и кнопки", "done": False},
            {"text": "Цвет текста задан", "done": False},
            {"text": "Аналоговая гармония", "done": False},
        ],
        "hints": [
            {"color": "#4a90d9", "name": "Синий",
             "text": "Доверие, спокойствие, глубина. Идеален для фона и поверхностей."},
            {"color": "#5bb37e", "name": "Зелёный",
             "text": "Природа, рост, гармония. Расслабляет нервную систему."},
            {"color": "#8da8c0", "name": "Серо-голубой",
             "text": "Нейтральный, воздушный. Отлично как дополнительный цвет."},
        ],
        "show_hints": True,
        "show_wcag": False,
        "show_vision_sim": False,
        "modal_score": 88,
        "modal_score_color": "#6bffcc",
        "modal_title": "Отлично! 🎨",
        "modal_sub": "Палитра хорошо передаёт спокойствие. Назначьте цвет текста для завершения.",
        "modal_criteria": [
            {"label": "🎵 Цветовая гармония", "value": "91 / 100", "color": "#6bffcc"},
            {"label": "💙 Эмоциональный отклик", "value": "85 / 100", "color": "#6bffcc"},
        ],
    },
    2: {
        "level_id": 2,
        "title": "Таинственность",
        "emoji": "🌙",
        "description": "Создайте палитру, передающую загадочность и глубину. Подсказки отключены.",
        "requirements": [
            {"text": "Назначьте все 5 ролей", "done": False},
            {"text": "Передайте заданную эмоцию", "done": False},
            {"text": "Соблюдайте цветовую гармонию", "done": False},
        ],
        "hints": [],
        "show_hints": False,
        "show_wcag": True,
        "show_vision_sim": False,
        "modal_score": 76,
        "modal_score_color": "#c8b4ff",
        "modal_title": "Хорошая работа! 🌙",
        "modal_sub": "Таинственность передана, но гармония требует доработки.",
        "modal_criteria": [
            {"label": "🎵 Цветовая гармония", "value": "72 / 100", "color": "#c8b4ff"},
            {"label": "💙 Эмоциональный отклик", "value": "80 / 100", "color": "#6bffcc"},
        ],
    },
    3: {
        "level_id": 3,
        "title": "Доступный интерфейс",
        "emoji": "♿",
        "description": "Создайте палитру, соответствующую WCAG 2.1 AA для людей с нарушениями цветовосприятия.",
        "requirements": [
            {"text": "Контраст текст/фон ≥ 4.5:1", "done": False},
            {"text": "Контраст кнопок ≥ 3:1", "done": False},
            {"text": "Читаемо при протанопии", "done": False},
            {"text": "Читаемо при дейтеранопии", "done": False},
        ],
        "hints": [],
        "show_hints": False,
        "show_wcag": True,
        "show_vision_sim": True,
        "modal_score": 63,
        "modal_score_color": "#ff9f6b",
        "modal_title": "Продолжайте! ♿",
        "modal_sub": "Контрастность не достигает WCAG AA. Попробуйте более тёмный текст.",
        "modal_criteria": [
            {"label": "🎵 Цветовая гармония", "value": "78 / 100", "color": "#6bffcc"},
            {"label": "💙 Эмоциональный отклик", "value": "70 / 100", "color": "#c8b4ff"},
            {"label": "♿ Контрастность WCAG", "value": "3.1:1 ✗ (нужно 4.5)", "color": "#ff6b8a"},
            {"label": "👁 Дальтонизм", "value": "Протанопия: слабо", "color": "#ff9f6b"},
        ],
    },
}

MODAL_DATA = {
    1: {
        "score": 88,
        "score_color": "#6bffcc",
        "title": "Отлично! 🎨",
        "sub": "Палитра хорошо передаёт спокойствие. Добавьте читаемый цвет текста для завершения.",
        "criteria": [
            {"label": "🎵 Цветовая гармония", "value": "91 / 100", "color": "#6bffcc"},
            {"label": "💙 Эмоциональный отклик", "value": "85 / 100", "color": "#6bffcc"},
            {"label": "🎯 Соответствие задаче", "value": "88 / 100", "color": "#6bffcc"},
        ],
    },
    2: {
        "score": 76,
        "score_color": "#c8b4ff",
        "title": "Хорошая работа! 🌙",
        "sub": "Таинственность передана, но композиции не хватает фокуса.",
        "criteria": [
            {"label": "🎵 Цветовая гармония", "value": "72 / 100", "color": "#c8b4ff"},
            {"label": "💙 Эмоциональный отклик", "value": "80 / 100", "color": "#6bffcc"},
            {"label": "🎯 Визуальный баланс", "value": "76 / 100", "color": "#c8b4ff"},
        ],
    },
    3: {
        "score": 63,
        "score_color": "#ff9f6b",
        "title": "Продолжайте! ♿",
        "sub": "Контрастность не достигает WCAG AA. Попробуйте более тёмный текст на светлом фоне.",
        "criteria": [
            {"label": "🎵 Цветовая гармония", "value": "78 / 100", "color": "#6bffcc"},
            {"label": "💙 Эмоциональный отклик", "value": "70 / 100", "color": "#c8b4ff"},
            {"label": "♿ Контрастность WCAG", "value": "3.1:1 ✗ (нужно 4.5)", "color": "#ff6b8a"},
            {"label": "👁 Дальтонизм", "value": "Протанопия: слабо", "color": "#ff9f6b"},
        ],
    },
}

PROFILE = {
    "initials": "АИ",
    "name": "Алексей Иванов",
    "email": "alex@example.com",
    "since": "января 2025",
    "city": "Москва",
    "level_badge": "🟠 Экспертный уровень",
    "stats": [
        {"icon": "✅", "value": "24", "label": "Заданий выполнено",
         "trend": "↑ +3 на этой неделе", "trend_color": "var(--success)"},
        {"icon": "🎯", "value": "87", "label": "Средний балл",
         "trend": "↑ +2 за месяц", "trend_color": "var(--success)"},
        {"icon": "🔥", "value": "12", "label": "Дней подряд",
         "trend": "Личный рекорд!", "trend_color": "var(--success)"},
        {"icon": "♿", "value": "14", "label": "Доступных палитр",
         "trend": "↑ +2 за месяц", "trend_color": "var(--success)"}
    ],
    "skills": [
        {"icon": "🎵", "name": "Цветовая гармония", "value": 88,
         "color": "var(--success)", "gradient": "#6bffcc,#4fcca0",
         "note": "Отлично — 9 из 10 заданий пройдено"},
        {"icon": "💙", "name": "Эмоциональный отклик", "value": 74,
         "color": "var(--accent)", "gradient": "#c8b4ff,#8b5fff",
         "note": "Хорошо — 7 из 10 заданий пройдено"},
        {"icon": "⚡", "name": "Контрастность WCAG", "value": 61,
         "color": "var(--accent2)", "gradient": "#ff9f6b,#e07040",
         "note": "8 из 13 заданий прошли проверку AA"},
        {"icon": "👁", "name": "Дальтонизм", "value": 38,
         "color": "#ffd93d", "gradient": "#ffd93d,#f0b800",
         "note": "Сложно — 3 из 8 симуляций пройдено"},
    ],
    "completed_tasks": [
        {"icon": "🌊", "name": "Спокойствие", "lv": 1,
         "lv_style": "", "harmony": "Аналоговая",
         "ago": "2 дня назад", "attempts": 5, "score": 94, "sc": "s-good"},
        {"icon": "🔥", "name": "Энергия", "lv": 1,
         "lv_style": "", "harmony": "Комплементарная",
         "ago": "5 дней назад", "attempts": 3, "score": 81, "sc": "s-ok"},
        {"icon": "🌙", "name": "Таинственность", "lv": 2,
         "lv_style": "background:rgba(200,180,255,.12);color:#c8b4ff",
         "harmony": "Без подсказок", "ago": "Неделю назад",
         "attempts": 7, "score": 76, "sc": "s-ok"},
        {"icon": "🌿", "name": "Минимализм", "lv": 2,
         "lv_style": "background:rgba(200,180,255,.12);color:#c8b4ff",
         "harmony": "Монохроматическая", "ago": "2 нед. назад",
         "attempts": 2, "score": 91, "sc": "s-good"},
        {"icon": "♿", "name": "Доступный интерфейс", "lv": 3,
         "lv_style": "background:rgba(255,159,107,.12);color:#ff9f6b",
         "harmony": "WCAG AA · Протан.", "ago": "Месяц назад",
         "attempts": 11, "score": 63, "sc": "s-low"},
        {"icon": "🌅", "name": "Рассвет", "lv": 1,
         "lv_style": "", "harmony": "Аналоговая",
         "ago": "6 нед. назад", "attempts": 2, "score": 88, "sc": "s-good"},
        {"icon": "🌊", "name": "Океан", "lv": 2,
         "lv_style": "background:rgba(200,180,255,.12);color:#c8b4ff",
         "harmony": "Аналоговая", "ago": "2 мес. назад",
         "attempts": 4, "score": 79, "sc": "s-ok"},
        {"icon": "🖤", "name": "Контраст", "lv": 3,
         "lv_style": "background:rgba(255,159,107,.12);color:#ff9f6b",
         "harmony": "Компл. + WCAG", "ago": "2 мес. назад",
         "attempts": 9, "score": 71, "sc": "s-ok"},
        {"icon": "🌸", "name": "Нежность", "lv": 1,
         "lv_style": "", "harmony": "Монохроматическая",
         "ago": "3 мес. назад", "attempts": 1, "score": 96, "sc": "s-good"},
        {"icon": "🌃", "name": "Ночной город", "lv": 2,
         "lv_style": "background:rgba(200,180,255,.12);color:#c8b4ff",
         "harmony": "Триадная", "ago": "3 мес. назад",
         "attempts": 6, "score": 68, "sc": "s-ok"},
        {"icon": "🍂", "name": "Осень", "lv": 1,
         "lv_style": "", "harmony": "Аналоговая",
         "ago": "4 мес. назад", "attempts": 3, "score": 85, "sc": "s-good"},
        {"icon": "❄️", "name": "Арктика", "lv": 3,
         "lv_style": "background:rgba(255,159,107,.12);color:#ff9f6b",
         "harmony": "Моно + WCAG AAA", "ago": "5 мес. назад",
         "attempts": 14, "score": 58, "sc": "s-low"},
    ],
}

# ═══════════════════════════════════════════════════════
# ADMIN — данные и маршруты
# ═══════════════════════════════════════════════════════

from flask import request

ADMIN = {"name": "Анна Д.", "role": "Администратор"}

# ── Вспомогательный LCG для стабильных демо-данных ──────
def _lcg_seq(base, variance, seed, n=7):
    s = seed % 2147483647
    result = []
    for _ in range(n):
        s = s * 16807 % 2147483647
        v = (s - 1) / 2147483646
        result.append(round(base + (v - 0.5) * 2 * variance))
    return result


def _get_period():
    return request.args.get("period", "7d")


def _admin_context():
    """Общий контекст для всех admin-страниц."""
    return {
        "admin":  ADMIN,
        "period": _get_period(),
        "stats":  {"total_users": "1 247"},
    }


# ── Overview data ────────────────────────────────────────
def _overview_data():
    return {
        "kpis": [
            {"label": "Активных пользователей", "value": "1 247", "color": "green",
             "trend": "+12% за период", "up": True},
            {"label": "Заданий выполнено", "value": "8 934", "color": "purple",
             "trend": "+7% за период", "up": True},
            {"label": "Средний балл", "value": "82.4", "color": "orange",
             "trend": "−0.3 за период", "up": False},
            {"label": "Дней подряд (медиана)", "value": "11", "color": "yellow",
             "trend": "+2 за период", "up": True},
        ],
        "activity_started":  _lcg_seq(320, 80, 5),
        "activity_finished": _lcg_seq(250, 70, 6),
        "level_pcts": [51, 32, 17],
        "level_legend": [
            {"label": "Уровень 1 · Базовый",     "color": "#6bffcc", "pct": 51},
            {"label": "Уровень 2 · Продвинутый", "color": "#c8b4ff", "pct": 32},
            {"label": "Уровень 3 · Экспертный",  "color": "#ff9f6b", "pct": 17},
        ],
        "popular_tasks": [
            {"label": "🌊 Спокойствие",     "color": "#6bffcc", "pct": 94},
            {"label": "🌸 Нежность",         "color": "#c8b4ff", "pct": 87},
            {"label": "🔥 Энергия",          "color": "#ff9f6b", "pct": 79},
            {"label": "🌙 Таинственность",   "color": "#c8b4ff", "pct": 72},
            {"label": "♿ Доступность",       "color": "#ff9f6b", "pct": 58},
        ],
        "retention": [100, 74, 58, 44, 31],
        "harmony_usage": [
            {"label": "Аналоговая",      "color": "#6bffcc", "pct": 82},
            {"label": "Монохромная",     "color": "#c8b4ff", "pct": 64},
            {"label": "Комплементарная", "color": "#ff9f6b", "pct": 51},
            {"label": "Триадная",        "color": "#ffd93d", "pct": 38},
        ],
    }


# ── Users data ───────────────────────────────────────────
def _users_data():
    return {
        "kpis": [
            {"label": "Всего пользователей", "value": "1 247", "color": "green",
             "trend": "+47 за период", "up": True,
             "spark_data": _lcg_seq(1200, 30, 10), "spark_color": "#6bffcc"},
            {"label": "Новых за период", "value": "183", "color": "purple",
             "trend": "+23% к прошлому", "up": True,
             "spark_data": _lcg_seq(25, 8, 11), "spark_color": "#c8b4ff"},
            {"label": "Активных сегодня", "value": "94", "color": "orange",
             "trend": "из 1247 всего", "up": True,
             "spark_data": _lcg_seq(80, 20, 12), "spark_color": "#ff9f6b"},
            {"label": "Отток за период", "value": "2.3%", "color": "yellow",
             "trend": "−0.4% к прошлому", "up": True,
             "spark_data": _lcg_seq(2, 1, 13), "spark_color": "#ffd93d"},
        ],
        "monthly_growth": _lcg_seq(80, 30, 20, n=12),
        "funnel": [
            {"emoji": "🟢", "name": "Уровень 1 пройден", "sub": "Базовый · Гармония + эмоция",
             "color": "#6bffcc", "count": 786, "pct": 63},
            {"emoji": "🟣", "name": "Уровень 2 пройден", "sub": "Продвинутый · Без подсказок",
             "color": "#c8b4ff", "count": 432, "pct": 35},
            {"emoji": "🟠", "name": "Уровень 3 пройден", "sub": "Экспертный · WCAG + дальтонизм",
             "color": "#ff9f6b", "count": 178, "pct": 14},
        ],
        "score_distribution": [45, 98, 187, 324, 412, 181],
    }


# ── Tasks data ───────────────────────────────────────────
def _tasks_data():
    rows = [
        {"icon":"🌊","name":"Спокойствие",         "lv":1,"harmony":"Аналоговая",      "avg_attempts":5.1, "pass_pct":94,"trend_icon":"↑","trend_color":"#6bffcc","spark":_lcg_seq(94,12,40)},
        {"icon":"🌸","name":"Нежность",              "lv":1,"harmony":"Монохромная",     "avg_attempts":2.8, "pass_pct":91,"trend_icon":"↑","trend_color":"#6bffcc","spark":_lcg_seq(91,10,41)},
        {"icon":"🌅","name":"Рассвет",               "lv":1,"harmony":"Аналоговая",      "avg_attempts":3.2, "pass_pct":87,"trend_icon":"→","trend_color":"#ffd93d","spark":_lcg_seq(87,8,42)},
        {"icon":"🌿","name":"Минимализм",            "lv":2,"harmony":"Монохромная",     "avg_attempts":4.0, "pass_pct":83,"trend_icon":"↑","trend_color":"#6bffcc","spark":_lcg_seq(83,10,43)},
        {"icon":"🔥","name":"Энергия",               "lv":1,"harmony":"Компл.",          "avg_attempts":3.9, "pass_pct":79,"trend_icon":"↓","trend_color":"#ff6b8a","spark":_lcg_seq(79,14,44)},
        {"icon":"🌙","name":"Таинственность",        "lv":2,"harmony":"Без ограничений", "avg_attempts":5.7, "pass_pct":72,"trend_icon":"→","trend_color":"#ffd93d","spark":_lcg_seq(72,12,45)},
        {"icon":"🌊","name":"Океан",                 "lv":2,"harmony":"Аналоговая",      "avg_attempts":4.8, "pass_pct":71,"trend_icon":"↑","trend_color":"#6bffcc","spark":_lcg_seq(71,10,46)},
        {"icon":"🖤","name":"Контраст",              "lv":3,"harmony":"Компл. + WCAG",  "avg_attempts":8.2, "pass_pct":64,"trend_icon":"↓","trend_color":"#ff6b8a","spark":_lcg_seq(64,14,47)},
        {"icon":"♿","name":"Доступность",            "lv":3,"harmony":"WCAG AA",         "avg_attempts":9.4, "pass_pct":58,"trend_icon":"→","trend_color":"#ffd93d","spark":_lcg_seq(58,10,48)},
        {"icon":"❄️","name":"Арктика",               "lv":3,"harmony":"Моно + WCAG AAA","avg_attempts":14.1,"pass_pct":44,"trend_icon":"↓","trend_color":"#ff6b8a","spark":_lcg_seq(44,10,49)},
    ]
    return {
        "kpis": [
            {"label": "Всего попыток",     "value": "21 381", "color": "purple",
             "trend": "+8% за период", "up": True,
             "spark_data": _lcg_seq(3000, 600, 30), "spark_color": "#c8b4ff"},
            {"label": "Успешных попыток",  "value": "14 207", "color": "green",
             "trend": "66% успеха", "up": True,
             "spark_data": _lcg_seq(2000, 400, 31), "spark_color": "#6bffcc"},
            {"label": "Среднее попыток",   "value": "2.4",    "color": "orange",
             "trend": "+0.2 к норме", "up": False,
             "spark_data": _lcg_seq(3, 1, 32), "spark_color": "#ff9f6b"},
            {"label": "Самое сложное",     "value": "Арктика","color": "yellow",
             "trend": "14 попыток ср.", "up": False,
             "spark_data": [7,8,9,11,12,13,14], "spark_color": "#ffd93d"},
        ],
        "rows": rows,
    }


# ── Skills data ──────────────────────────────────────────
def _skills_data():
    return {
        "platform_avg": [
            {"icon":"🎵","name":"Цветовая гармония", "pct":74,"delta":"+6%","up":True, "color":"#6bffcc"},
            {"icon":"💙","name":"Эмоц. отклик",       "pct":68,"delta":"+4%","up":True, "color":"#c8b4ff"},
            {"icon":"♿","name":"Контрастность WCAG", "pct":49,"delta":"+2%","up":True, "color":"#ff9f6b"},
            {"icon":"👁","name":"Дальтонизм",          "pct":31,"delta":"−1%","up":False,"color":"#ffd93d"},
        ],
        "weak_zones": [
            {"label":"👁 Дальтонизм · Тританопия",  "color":"#ff6b8a","pct":23},
            {"label":"♿ WCAG AAA (Уровень 3)",       "color":"#ff9f6b","pct":31},
            {"label":"👁 Дальтонизм · Протанопия",  "color":"#ffd93d","pct":39},
            {"label":"🎵 Триадная гармония",          "color":"#ffd93d","pct":44},
            {"label":"💙 Абстрактные эмоции",        "color":"#c8b4ff","pct":51},
        ],
        "by_level": [
            # Level 1
            [{"icon":"🎵","name":"Цветовая гармония","pct":88,"color":"#6bffcc"},
             {"icon":"💙","name":"Эмоц. отклик",      "pct":83,"color":"#6bffcc"}],
            # Level 2 (not shown in template but kept for consistency)
            [{"icon":"🎵","name":"Цветовая гармония","pct":74,"color":"#c8b4ff"},
             {"icon":"💙","name":"Эмоц. отклик",      "pct":69,"color":"#c8b4ff"}],
            # Level 3
            [{"icon":"♿","name":"Контрастность WCAG","pct":49,"color":"#ff9f6b"},
             {"icon":"👁","name":"Дальтонизм",          "pct":31,"color":"#ffd93d"},
             {"icon":"🎵","name":"Цветовая гармония",  "pct":62,"color":"#ff9f6b"},
             {"icon":"💙","name":"Эмоц. отклик",       "pct":58,"color":"#ff9f6b"}],
        ],
    }


# ── Alerts data ──────────────────────────────────────────
def _alerts_data():
    return {
        "items": [
            {"type": "warn", "icon": "⚠️",
             "title": "Уровень 3 · Низкий процент прохождения",
             "body": "За последние 30 дней среднее прохождение задания «Арктика» составляет 44% — на 18% ниже порогового значения. Рекомендуется пересмотреть сложность или добавить промежуточные подсказки для проверки WCAG AAA.",
             "action_url": "/admin/tasks", "action_label": "К заданиям →"},
            {"type": "warn", "icon": "⚠️",
             "title": "Навык «Дальтонизм» — отстающий",
             "body": "Средний прогресс по навыку дальтонизм остаётся на уровне 31%. За последние 4 недели роста нет. Возможная причина — недостаточное количество практических заданий на симуляцию тританопии.",
             "action_url": "/admin/skills", "action_label": "К навыкам →"},
            {"type": "info", "icon": "ℹ️",
             "title": "Рост новых пользователей +23%",
             "body": "За последние 30 дней зафиксирован рост регистраций на 23% по сравнению с предыдущим периодом. Пиковый день — среда. Рекомендуется проверить нагрузку на серверы в рабочие дни между 12:00 и 15:00.",
             "action_url": None, "action_label": None},
            {"type": "info", "icon": "ℹ️",
             "title": "Аналитический отчёт готов",
             "body": "Ежемесячный агрегированный отчёт за текущий период сформирован. Все данные анонимизированы по стандарту k-анонимности (k≥5). Доступен для выгрузки в формате CSV.",
             "action_url": "?export=csv", "action_label": "↓ Скачать CSV"},
        ],
        "system_chips": [
            {"label": "Аноним. уровень", "value": "k≥5",  "color": "#6bffcc"},
            {"label": "Персон. данных",  "value": "0",     "color": "#6bffcc"},
            {"label": "Сессий сегодня",  "value": "312",   "color": "#c8b4ff"},
            {"label": "Запросов / мин",  "value": "47",    "color": "#ffd93d"},
            {"label": "Ошибок (24ч)",    "value": "3",     "color": "#6bffcc"},
        ],
        "error_counts": _lcg_seq(4, 3, 99),
        "anon_status": [
            {"label": "Стандарт",         "value": "k≥5",    "color": "#6bffcc", "sub": "k-анонимность"},
            {"label": "Персональных ID",   "value": "0",      "color": "#6bffcc", "sub": "не хранится"},
            {"label": "Срок хранения",     "value": "90 дн",  "color": "#c8b4ff", "sub": "агрегаты"},
        ],
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.errorhandler(SQLAlchemyError)
def handle_sqlalchemy_error(err):
    error_msg = ('Возникла ошибка при подключении к базе данных. '
                 'Повторите попытку позже.')
    return f'{error_msg} (Подробнее: {err})', 500
 
 
@app.context_processor
def inject_user():
    return dict(user=current_user)

@app.route("/")
def landing():
    return render_template("landing.html")


app.register_blueprint(auth_bp)

@app.route("/levels")
def levels():
    return render_template("levels.html", levels=LEVELS)


@app.route("/game/<int:level_id>")
def game(level_id: int):
    task = TASKS.get(level_id)
    level = next((l for l in LEVELS if l["id"] == level_id), None)
    if not task or not level:
        return render_template("landing.html"), 404
    return render_template("game.html", task=task, level=level, modal=MODAL_DATA.get(level_id))


@app.route("/profile")
def profile():
    return render_template("profile.html", profile=PROFILE)

@app.route("/profile/edit")
def profile_edit():
    return render_template("profile_edit.html", profile=PROFILE)

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


# ── Admin routes ─────────────────────────────────────────

@app.route("/admin")
@app.route("/admin/overview")
def admin_overview():
    return render_template(
        "admin_overview.html",
        active_page="overview",
        overview=_overview_data(),
        **_admin_context(),
    )


@app.route("/admin/users")
def admin_users():
    return render_template(
        "admin_users.html",
        active_page="users",
        users=_users_data(),
        **_admin_context(),
    )


@app.route("/admin/tasks")
def admin_tasks():
    return render_template(
        "admin_tasks.html",
        active_page="tasks",
        tasks_stats=_tasks_data(),
        **_admin_context(),
    )


@app.route("/admin/skills")
def admin_skills():
    return render_template(
        "admin_skills.html",
        active_page="skills",
        skills=_skills_data(),
        **_admin_context(),
    )

