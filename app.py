from flask import Flask, render_template, session
import random
from urllib.parse import urlparse

from flask_migrate import Migrate
from flask import flash, jsonify, redirect, request, url_for
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user
from assessment import build_color_vision_preview_response, process_task_submission
from models import db, Task, User
from auth import bp as auth_bp, init_login_manager, login_required
from admin import bp as admin_bp
from tools import EditProfileForm, build_profile_data, generate_task, task_to_game_dict

app = Flask(__name__)

app.config.from_pyfile('config.py')
 
db.init_app(app)
migrate = Migrate(app, db)
 
init_login_manager(app)

VALID_LEVEL_IDS = {1, 2, 3}
PREVIEW_SITES = ["aelius.html", "shop.html", "media-blog.html"]


def clear_active_game_session() -> None:
    for level_id in VALID_LEVEL_IDS:
        session.pop(f"active_task_level_{level_id}", None)
        session.pop(f"active_site_level_{level_id}", None)
    session.modified = True


def get_back_url(default_endpoint: str) -> str:
    candidate = request.form.get("back_url") or request.referrer
    if candidate:
        parsed = urlparse(candidate)
        candidate_path = parsed.path or candidate
        if (not parsed.netloc or parsed.netloc == request.host) and candidate_path != request.path:
            return candidate
    return url_for(default_endpoint)

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
    clear_active_game_session()
    return render_template("levels.html")


@app.route("/game/<int:level_id>", methods=["GET", "POST"])
def game(level_id: int):
    if level_id not in VALID_LEVEL_IDS:
        return render_template("landing.html"), 404

    session.permanent = True
    session_key = f"active_task_level_{level_id}"
    site_session_key = f"active_site_level_{level_id}"

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        if payload.get("action") == "vision_preview":
            return jsonify(build_color_vision_preview_response(payload.get("palette") or []))

        task_id = payload.get("task_id") or session.get(session_key)
        task = db.session.get(Task, task_id) if task_id else None
        if not task or task.level_number != level_id:
            return jsonify({"error": "Task not found"}), 404
        result = process_task_submission(
            task,
            payload.get("palette") or [],
            current_user,
        )
        return jsonify(result)

    task_id = session.get(session_key)
    task = None
    if task_id:
        db_task = db.session.get(Task, task_id)
        if db_task and db_task.level_number == level_id:
            task = task_to_game_dict(db_task)

    selected_site = session.get(site_session_key)

    if not task:
        task = generate_task(level_id, persist=True)
        session[session_key] = task["id"]
        selected_site = random.choice(PREVIEW_SITES)
        session[site_session_key] = selected_site
        session.modified = True
    elif selected_site not in PREVIEW_SITES:
        selected_site = random.choice(PREVIEW_SITES)
        session[site_session_key] = selected_site
        session.modified = True

    return render_template("game.html", task=task, level_id=level_id, selected_site=selected_site)

@app.route("/profile")
@login_required
def profile():
    profile_data = build_profile_data(current_user)
    return render_template("profile.html", profile=profile_data)

@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    form = EditProfileForm(obj=current_user)
    back_url = get_back_url("profile")
    if request.method == "POST":
        form.validate()

        existing_login = db.session.execute(
            db.select(User).where(User.login == form.login.data, User.id != current_user.id)
        ).scalar() if not form.login.errors else None
        if existing_login:
            form.login.errors.append("Этот логин уже занят.")

        existing_email = db.session.execute(
            db.select(User).where(User.email == form.email.data, User.id != current_user.id)
        ).scalar() if not form.email.errors else None
        if existing_email:
            form.email.errors.append("Этот email уже используется.")

        if form.password.data and not form.current_password.data:
            form.current_password.errors.append("Введите текущий пароль для смены пароля.")
        elif form.password.data and not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Текущий пароль указан неверно.")

        if not any(field.errors for field in form):
            current_user.login = form.login.data
            current_user.first_name = form.first_name.data
            current_user.second_name = form.second_name.data
            current_user.email = form.email.data
            current_user.city = form.city.data or None
            if form.password.data:
                current_user.set_password(form.password.data)
            db.session.commit()
            flash("Профиль сохранён.", "success")
            return redirect(url_for("profile"))

    return render_template("profile_edit.html", form=form, back_url=back_url)




