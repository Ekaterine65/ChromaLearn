from flask import Flask, render_template
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user
from datetime import datetime, date, timedelta
from models import db, Result, Task, Emotion, HarmonyType
from auth import bp as auth_bp, init_login_manager
from admin import bp as admin_bp

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

# === Profile aggregates ===
LEVEL_BADGES = {
    1: "🟢 Базовый уровень",
    2: "🟣 Продвинутый уровень",
    3: "🟠 Экспертный уровень",
}

MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

HARMONY_LABELS = {
    HarmonyType.analogous: "Аналоговая",
    HarmonyType.complementary: "Комплементарная",
    HarmonyType.triadic: "Триадная",
    HarmonyType.monochromatic: "Монохроматическая",
}


def format_since(dt: datetime) -> str:
    return f"{MONTHS_RU.get(dt.month, '')} {dt.year}"


def format_ago(dt: datetime, now: datetime) -> str:
    days = max((now.date() - dt.date()).days, 0)
    if days == 0:
        return "Сегодня"
    if days == 1:
        return "Вчера"
    if days < 7:
        return f"{days} дня назад"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} нед. назад"
    months = max(days // 30, 1)
    return f"{months} мес. назад"


def score_class(score: int) -> str:
    if score >= 85:
        return "s-good"
    if score >= 70:
        return "s-ok"
    return "s-low"


def compute_streak(activity_data: dict, now: datetime) -> int:
    if not activity_data:
        return 0
    cursor = now.date()
    if activity_data.get(cursor.isoformat(), 0) == 0:
        cursor = cursor - timedelta(days=1)
    streak = 0
    while activity_data.get(cursor.isoformat(), 0) > 0:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak
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
app.register_blueprint(admin_bp)

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
    if not current_user.is_authenticated:
        profile_data = {
            "name": PROFILE["name"],
            "email": PROFILE["email"],
            "since": PROFILE["since"],
            "city": PROFILE["city"],
            "level_badge": PROFILE["level_badge"],
            "stats": {
                "tasks_done": int(PROFILE["stats"][0]["value"]),
                "avg_score": int(PROFILE["stats"][1]["value"]),
                "streak_days": int(PROFILE["stats"][2]["value"]),
                "accessibility_tasks": int(PROFILE["stats"][3]["value"]),
            },
            "skills": {
                "harmony": int(PROFILE["skills"][0]["value"]),
                "emotion": int(PROFILE["skills"][1]["value"]),
                "contrast": int(PROFILE["skills"][2]["value"]),
                "colorblind": int(PROFILE["skills"][3]["value"]),
            },
            "completed_tasks": PROFILE["completed_tasks"],
            "activity": {},
            "activity_years": [date.today().year],
        }
        return render_template("profile.html", profile=profile_data)

    now = datetime.now()
    user_id = current_user.id

    results = db.session.execute(
        db.select(Result)
        .where(Result.user_id == user_id)
        .order_by(Result.completed_at.desc())
    ).scalars().all()

    unique_tasks_count = db.session.execute(
        db.select(db.func.count(db.distinct(Result.task_id)))
        .where(Result.user_id == user_id)
    ).scalar() or 0

    avg_score = db.session.execute(
        db.select(db.func.avg(Result.score_total))
        .where(Result.user_id == user_id)
    ).scalar()
    avg_score = round(avg_score) if avg_score is not None else 0

    accessibility_count = db.session.execute(
        db.select(db.func.count(db.distinct(Result.task_id)))
        .join(Task, Task.id == Result.task_id)
        .where(Result.user_id == user_id, Task.level_number == 3)
    ).scalar() or 0

    avg_harmony = db.session.execute(
        db.select(db.func.avg(Result.score_harmony))
        .where(Result.user_id == user_id)
    ).scalar()
    avg_emotion = db.session.execute(
        db.select(db.func.avg(Result.score_emotion))
        .where(Result.user_id == user_id)
    ).scalar()
    avg_contrast = db.session.execute(
        db.select(db.func.avg(Result.score_contrast))
        .where(Result.user_id == user_id, Result.score_contrast.is_not(None))
    ).scalar()
    avg_colorblind = db.session.execute(
        db.select(db.func.avg(Result.score_colorblind))
        .where(Result.user_id == user_id, Result.score_colorblind.is_not(None))
    ).scalar()

    avg_harmony = round(avg_harmony) if avg_harmony is not None else 0
    avg_emotion = round(avg_emotion) if avg_emotion is not None else 0
    avg_contrast = round(avg_contrast) if avg_contrast is not None else 0
    avg_colorblind = round(avg_colorblind) if avg_colorblind is not None else 0

    max_level = db.session.execute(
        db.select(db.func.max(Task.level_number))
        .join(Result, Result.task_id == Task.id)
        .where(Result.user_id == user_id)
    ).scalar() or 1
    level_badge = LEVEL_BADGES.get(max_level, LEVEL_BADGES[1])

    results_by_task = {}
    attempts_by_task = {}
    for r in results:
        attempts_by_task[r.task_id] = attempts_by_task.get(r.task_id, 0) + 1
        if r.task_id not in results_by_task:
            results_by_task[r.task_id] = r

    completed_tasks = []
    task_ids = list(results_by_task.keys())
    if task_ids:
        tasks = db.session.execute(
            db.select(Task, Emotion)
            .outerjoin(Emotion, Emotion.id == Task.emotion_id)
            .where(Task.id.in_(task_ids))
        ).all()
        task_map = {t.id: (t, e) for t, e in tasks}
        for task_id, last_result in results_by_task.items():
            task, emotion = task_map.get(task_id, (None, None))
            if not task:
                continue
            icon = (emotion.emoji if emotion and emotion.emoji else "🎨")
            harmony = last_result.harmony_used or task.harmony_type
            completed_tasks.append({
                "icon": icon,
                "name": task.title,
                "lv": task.level_number,
                "lv_style": (
                    "background:rgba(200,180,255,.12);color:#c8b4ff"
                    if task.level_number == 2 else
                    "background:rgba(255,159,107,.12);color:#ff9f6b"
                    if task.level_number == 3 else ""
                ),
                "harmony": HARMONY_LABELS.get(harmony, "Без подсказок"),
                "ago": format_ago(last_result.completed_at, now),
                "attempts": attempts_by_task.get(task_id, 0),
                "score": last_result.score_total,
                "sc": score_class(last_result.score_total),
            })

    activity_data = {}
    for r in results:
        key = r.completed_at.date().isoformat()
        activity_data[key] = activity_data.get(key, 0) + 1

    streak_days = compute_streak(activity_data, now)

    activity_years = sorted(
        {int(k[:4]) for k in activity_data.keys()},
        reverse=True
    )
    if not activity_years:
        activity_years = [date.today().year]

    profile_data = {
        "name": current_user.full_name,
        "email": current_user.email,
        "since": format_since(current_user.created_at),
        "city": current_user.city or "—",
        "level_badge": level_badge,
        "stats": {
            "tasks_done": unique_tasks_count,
            "avg_score": avg_score,
            "streak_days": streak_days,
            "accessibility_tasks": accessibility_count,
        },
        "skills": {
            "harmony": avg_harmony,
            "emotion": avg_emotion,
            "contrast": avg_contrast,
            "colorblind": avg_colorblind,
        },
        "completed_tasks": completed_tasks,
        "activity": activity_data,
        "activity_years": activity_years,
    }
    return render_template("profile.html", profile=profile_data)

@app.route("/profile/edit")
def profile_edit():
    return render_template("profile_edit.html", profile=PROFILE)

