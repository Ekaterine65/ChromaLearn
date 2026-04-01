from flask import Blueprint, render_template, redirect, url_for, abort, request
from flask_login import login_required, current_user
from functools import wraps

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ── Вспомогательный LCG для стабильных демо-данных ──────────────────────────

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
        "admin": {
            "name": f"{current_user.first_name} {current_user.second_name[0]}.",
            "role": "Администратор",
        },
        "period": _get_period(),
        "stats": {"total_users": "1 247"},
    }


# ── Overview data ────────────────────────────────────────────────────────────

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
            {"label": "🌊 Спокойствие",   "color": "#6bffcc", "pct": 94},
            {"label": "🌸 Нежность",       "color": "#c8b4ff", "pct": 87},
            {"label": "🔥 Энергия",        "color": "#ff9f6b", "pct": 79},
            {"label": "🌙 Таинственность", "color": "#c8b4ff", "pct": 72},
            {"label": "♿ Доступность",     "color": "#ff9f6b", "pct": 58},
        ],
        "retention": [100, 74, 58, 44, 31],
        "harmony_usage": [
            {"label": "Аналоговая",      "color": "#6bffcc", "pct": 82},
            {"label": "Монохромная",     "color": "#c8b4ff", "pct": 64},
            {"label": "Комплементарная", "color": "#ff9f6b", "pct": 51},
            {"label": "Триадная",        "color": "#ffd93d", "pct": 38},
        ],
    }


# ── Users data ───────────────────────────────────────────────────────────────

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


# ── Tasks data ───────────────────────────────────────────────────────────────

def _tasks_data():
    rows = [
        {"icon": "🌊", "name": "Спокойствие",    "lv": 1, "harmony": "Аналоговая",      "avg_attempts": 5.1,  "pass_pct": 94, "trend_icon": "↑", "trend_color": "#6bffcc", "spark": _lcg_seq(94, 12, 40)},
        {"icon": "🌸", "name": "Нежность",        "lv": 1, "harmony": "Монохромная",     "avg_attempts": 2.8,  "pass_pct": 91, "trend_icon": "↑", "trend_color": "#6bffcc", "spark": _lcg_seq(91, 10, 41)},
        {"icon": "🌅", "name": "Рассвет",         "lv": 1, "harmony": "Аналоговая",      "avg_attempts": 3.2,  "pass_pct": 87, "trend_icon": "→", "trend_color": "#ffd93d", "spark": _lcg_seq(87,  8, 42)},
        {"icon": "🔥", "name": "Энергия",         "lv": 1, "harmony": "Компл.",          "avg_attempts": 3.9,  "pass_pct": 79, "trend_icon": "↓", "trend_color": "#ff6b8a", "spark": _lcg_seq(79, 14, 44)},
        {"icon": "🌿", "name": "Минимализм",      "lv": 2, "harmony": "Монохромная",     "avg_attempts": 4.0,  "pass_pct": 83, "trend_icon": "↑", "trend_color": "#6bffcc", "spark": _lcg_seq(83, 10, 43)},
        {"icon": "🌙", "name": "Таинственность",  "lv": 2, "harmony": "Без ограничений", "avg_attempts": 5.7,  "pass_pct": 72, "trend_icon": "→", "trend_color": "#ffd93d", "spark": _lcg_seq(72, 12, 45)},
        {"icon": "🌊", "name": "Океан",           "lv": 2, "harmony": "Аналоговая",      "avg_attempts": 4.8,  "pass_pct": 71, "trend_icon": "↑", "trend_color": "#6bffcc", "spark": _lcg_seq(71, 10, 46)},
        {"icon": "🖤", "name": "Контраст",        "lv": 3, "harmony": "Компл. + WCAG",   "avg_attempts": 8.2,  "pass_pct": 64, "trend_icon": "↓", "trend_color": "#ff6b8a", "spark": _lcg_seq(64, 14, 47)},
        {"icon": "♿", "name": "Доступность",      "lv": 3, "harmony": "WCAG AA",         "avg_attempts": 9.4,  "pass_pct": 58, "trend_icon": "→", "trend_color": "#ffd93d", "spark": _lcg_seq(58, 10, 48)},
        {"icon": "❄️", "name": "Арктика",         "lv": 3, "harmony": "Моно + WCAG AAA", "avg_attempts": 14.1, "pass_pct": 44, "trend_icon": "↓", "trend_color": "#ff6b8a", "spark": _lcg_seq(44, 10, 49)},
    ]
    return {
        "kpis": [
            {"label": "Всего попыток",    "value": "21 381", "color": "purple",
             "trend": "+8% за период", "up": True,
             "spark_data": _lcg_seq(3000, 600, 30), "spark_color": "#c8b4ff"},
            {"label": "Успешных попыток", "value": "14 207", "color": "green",
             "trend": "66% успеха", "up": True,
             "spark_data": _lcg_seq(2000, 400, 31), "spark_color": "#6bffcc"},
            {"label": "Среднее попыток",  "value": "2.4",    "color": "orange",
             "trend": "+0.2 к норме", "up": False,
             "spark_data": _lcg_seq(3, 1, 32), "spark_color": "#ff9f6b"},
            {"label": "Самое сложное",    "value": "Арктика", "color": "yellow",
             "trend": "14 попыток ср.", "up": False,
             "spark_data": [7, 8, 9, 11, 12, 13, 14], "spark_color": "#ffd93d"},
        ],
        "rows": rows,
    }


# ── Skills data ──────────────────────────────────────────────────────────────

def _skills_data():
    return {
        "platform_avg": [
            {"icon": "🎵", "name": "Цветовая гармония", "pct": 74, "delta": "+6%", "up": True,  "color": "#6bffcc"},
            {"icon": "💙", "name": "Эмоц. отклик",       "pct": 68, "delta": "+4%", "up": True,  "color": "#c8b4ff"},
            {"icon": "♿", "name": "Контрастность WCAG", "pct": 49, "delta": "+2%", "up": True,  "color": "#ff9f6b"},
            {"icon": "👁", "name": "Дальтонизм",          "pct": 31, "delta": "−1%", "up": False, "color": "#ffd93d"},
        ],
        "weak_zones": [
            {"label": "👁 Дальтонизм · Тританопия",  "color": "#ff6b8a", "pct": 23},
            {"label": "♿ WCAG AAA (Уровень 3)",       "color": "#ff9f6b", "pct": 31},
            {"label": "👁 Дальтонизм · Протанопия",  "color": "#ffd93d", "pct": 39},
            {"label": "🎵 Триадная гармония",          "color": "#ffd93d", "pct": 44},
            {"label": "💙 Абстрактные эмоции",        "color": "#c8b4ff", "pct": 51},
        ],
        "by_level": [
            [{"icon": "🎵", "name": "Цветовая гармония", "pct": 88, "color": "#6bffcc"},
             {"icon": "💙", "name": "Эмоц. отклик",      "pct": 83, "color": "#6bffcc"}],
            [{"icon": "🎵", "name": "Цветовая гармония", "pct": 74, "color": "#c8b4ff"},
             {"icon": "💙", "name": "Эмоц. отклик",      "pct": 69, "color": "#c8b4ff"}],
            [{"icon": "♿", "name": "Контрастность WCAG", "pct": 49, "color": "#ff9f6b"},
             {"icon": "👁", "name": "Дальтонизм",          "pct": 31, "color": "#ffd93d"},
             {"icon": "🎵", "name": "Цветовая гармония",  "pct": 62, "color": "#ff9f6b"},
             {"icon": "💙", "name": "Эмоц. отклик",       "pct": 58, "color": "#ff9f6b"}],
        ],
    }


# ── Alerts data ──────────────────────────────────────────────────────────────

def _alerts_data():
    return {
        "items": [
            {"type": "warn", "icon": "⚠️",
             "title": "Уровень 3 · Низкий процент прохождения",
             "body": "За последние 30 дней среднее прохождение задания «Арктика» составляет 44%.",
             "action_url": "/admin/tasks", "action_label": "К заданиям →"},
            {"type": "warn", "icon": "⚠️",
             "title": "Навык «Дальтонизм» — отстающий",
             "body": "Средний прогресс по навыку дальтонизм остаётся на уровне 31%.",
             "action_url": "/admin/skills", "action_label": "К навыкам →"},
            {"type": "info", "icon": "ℹ️",
             "title": "Рост новых пользователей +23%",
             "body": "За последние 30 дней зафиксирован рост регистраций на 23%.",
             "action_url": None, "action_label": None},
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
            {"label": "Стандарт",       "value": "k≥5",   "color": "#6bffcc", "sub": "k-анонимность"},
            {"label": "Персональных ID", "value": "0",     "color": "#6bffcc", "sub": "не хранится"},
            {"label": "Срок хранения",  "value": "90 дн", "color": "#c8b4ff", "sub": "агрегаты"},
        ],
    }


# ── Роуты ────────────────────────────────────────────────────────────────────

@bp.route("/")
@bp.route("/overview")
@admin_required
def overview():
    return render_template(
        "admin_overview.html",
        active_page="overview",
        overview=_overview_data(),
        **_admin_context(),
    )


@bp.route("/users")
@admin_required
def users():
    return render_template(
        "admin_users.html",
        active_page="users",
        users=_users_data(),
        **_admin_context(),
    )


@bp.route("/tasks")
@admin_required
def tasks():
    return render_template(
        "admin_tasks.html",
        active_page="tasks",
        tasks_stats=_tasks_data(),
        **_admin_context(),
    )


@bp.route("/skills")
@admin_required
def skills():
    return render_template(
        "admin_skills.html",
        active_page="skills",
        skills=_skills_data(),
        **_admin_context(),
    )
