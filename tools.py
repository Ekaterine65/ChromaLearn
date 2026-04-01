from datetime import datetime, date, timedelta

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators

from models import db, Result, Task, Emotion, HarmonyType


class LoginForm(FlaskForm):
    login = StringField('Логин', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
    ])
    password = PasswordField('Пароль', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
    ])


class RegistrationForm(FlaskForm):
    login = StringField('Логин', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=4, max=25, message='Логин должен быть от 4 до 25 символов'),
    ])
    first_name = StringField('Имя', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=1, max=100, message='Имя должно быть не длиннее 100 символов'),
    ])
    second_name = StringField('Фамилия', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=1, max=100, message='Фамилия должна быть не длиннее 100 символов'),
    ])
    email = StringField('Email', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Email(message='Введите корректный email'),
        validators.Length(max=200),
    ])
    city = StringField('Город', [
        validators.Optional(),
        validators.Length(max=100, message='Название города должно быть не длиннее 100 символов'),
    ])
    password = PasswordField('Пароль', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=6, message='Пароль должен быть не короче 6 символов'),
    ])
    confirm_password = PasswordField('Подтвердите пароль', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.EqualTo('password', message='Пароли должны совпадать'),
    ])
 

class EditProfileForm(FlaskForm):
    login = StringField('Логин', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=4, max=25, message='Логин должен быть от 4 до 25 символов'),
    ])
    first_name = StringField('Имя', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=1, max=100, message='Имя должно быть не длиннее 100 символов'),
    ])
    second_name = StringField('Фамилия', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.Length(min=1, max=100, message='Фамилия должна быть не длиннее 100 символов'),
    ])
    email = StringField('Email', [
        validators.Optional(),
        validators.Email(message='Введите корректный email'),
        validators.Length(max=200),
    ])
    city = StringField('Город', [
        validators.Optional(),
        validators.Length(max=100, message='Название города должно быть не длиннее 100 символов'),
    ])
    password = PasswordField('Новый пароль', [
        validators.Optional(),
        validators.EqualTo('confirm_password', message='Пароли должны совпадать'),
        validators.Length(min=6, message='Пароль должен быть не короче 6 символов'),
    ])
    confirm_password = PasswordField('Подтвердите новый пароль')

    def validate_confirm_password(self, field):
        if self.password.data and not field.data:
            raise validators.ValidationError('Поле подтверждения пароля обязательно при смене пароля.')

# Profile aggregates
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


def build_profile_data(current_user) -> dict:
    if not current_user.is_authenticated:
        return {
            "name": "",
            "email": "",
            "since": "",
            "city": "",
            "level_badge": "",
            "stats": {
                "tasks_done": 0,
                "avg_score": 0,
                "streak_days": 0,
                "accessibility_tasks": 0,
            },
            "skills": {
                "harmony": 0,
                "emotion": 0,
                "contrast": 0,
                "colorblind": 0,
            },
            "completed_tasks": [],
            "activity": {},
            "activity_years": [date.today().year],
        }

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

    return {
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
