from flask import Flask, render_template
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user
from models import db
from auth import bp as auth_bp, init_login_manager, login_required
from admin import bp as admin_bp
from tools import build_profile_data

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
@login_required
def profile():
    profile_data = build_profile_data(current_user)
    return render_template("profile.html", profile=profile_data)

@app.route("/profile/edit")
@login_required
def profile_edit():
    profile_data = {
        "name": current_user.full_name,
        "email": current_user.email,
        "city": current_user.city or "",
    }
    return render_template("profile_edit.html", profile=profile_data)

