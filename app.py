from flask import Flask, render_template, session
from flask_migrate import Migrate
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user
from assessment import process_task_submission
from models import db, Task
from auth import bp as auth_bp, init_login_manager, login_required
from admin import bp as admin_bp
from tools import build_profile_data, generate_task, task_to_game_dict

app = Flask(__name__)

app.config.from_pyfile('config.py')
 
db.init_app(app)
migrate = Migrate(app, db)
 
init_login_manager(app)

VALID_LEVEL_IDS = {1, 2, 3}

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


@app.route("/game/<int:level_id>", methods=["GET", "POST"])
def game(level_id: int):
    if level_id not in VALID_LEVEL_IDS:
        return render_template("landing.html"), 404

    session_key = f"active_task_level_{level_id}"

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        task_id = payload.get("task_id") or session.get(session_key)
        task = db.session.get(Task, task_id) if task_id else None
        if not task or task.level_number != level_id:
            return jsonify({"error": "Task not found"}), 404
        return jsonify(process_task_submission(
            task,
            payload.get("palette") or [],
            payload.get("harmony_type"),
            current_user,
        ))

    task_id = session.get(session_key)
    task = None
    if task_id:
        db_task = db.session.get(Task, task_id)
        if db_task and db_task.level_number == level_id:
            task = task_to_game_dict(db_task)

    if not task:
        task = generate_task(level_id)
        #session[session_key] = task["id"]

    return render_template("game.html", task=task, level_id=level_id)

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




