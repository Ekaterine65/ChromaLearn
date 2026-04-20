from flask import Flask, render_template, session
from flask_migrate import Migrate
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user
from assessment import evaluate_task_solution
from models import db, HarmonyType, Result, Task
from auth import bp as auth_bp, init_login_manager, login_required
from admin import bp as admin_bp
from tools import build_profile_data, generate_task, task_to_game_dict

app = Flask(__name__)

app.config.from_pyfile('config.py')
 
db.init_app(app)
migrate = Migrate(app, db)
 
init_login_manager(app)

VALID_LEVEL_IDS = {1, 2, 3}

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
    return render_template("levels.html")


@app.route("/game/<int:level_id>")
def game(level_id: int):
    if level_id not in VALID_LEVEL_IDS:
        return render_template("landing.html"), 404

    session_key = f"active_task_level_{level_id}"
    task_id = session.get(session_key)
    task = None
    if task_id:
        db_task = db.session.get(Task, task_id)
        if db_task and db_task.level_number == level_id:
            task = task_to_game_dict(db_task)

    if not task:
        task = generate_task(level_id)
        session[session_key] = task["id"]

    return render_template("game.html", task=task, level_id=level_id, modal=MODAL_DATA.get(level_id))


@app.post("/api/tasks/<int:task_id>/evaluate")
def evaluate_task(task_id: int):
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    payload = request.get_json(silent=True) or {}
    harmony_used = task.harmony_type
    if not harmony_used and payload.get("harmony_type"):
        try:
            harmony_used = HarmonyType(payload["harmony_type"])
        except ValueError:
            harmony_used = None

    assessment = evaluate_task_solution(task, payload.get("palette") or [], harmony_used)

    saved = False
    if current_user.is_authenticated:
        result = Result(
            user_id=current_user.id,
            task_id=task.id,
            score_emotion=assessment.emotion.score,
            score_harmony=assessment.harmony.score,
            score_contrast=assessment.contrast.score,
            score_colorblind=assessment.color_vision.score,
            score_total=assessment.total_score,
            harmony_used=harmony_used,
        )
        db.session.add(result)
        db.session.commit()
        saved = True

    response = assessment.to_response()
    response["saved"] = saved
    return jsonify(response)


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




