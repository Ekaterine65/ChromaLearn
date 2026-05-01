from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required
from models import db, User
from tools import LoginForm, RegistrationForm

bp = Blueprint('auth', __name__, url_prefix='/auth')


def get_back_url(default_endpoint: str) -> str:
    candidate = request.form.get('back_url') or request.args.get('back_url') or request.referrer
    if is_safe_back_url(candidate):
        return candidate
    return url_for(default_endpoint)


def is_safe_back_url(candidate) -> bool:
    if not candidate:
        return False
    parsed = urlparse(candidate)
    candidate_path = parsed.path or candidate
    return (not parsed.netloc or parsed.netloc == request.host) and candidate_path != request.path


def get_login_redirect_url(back_url: str) -> str:
    next_page = request.form.get('next') or request.args.get('next')
    if is_safe_back_url(next_page):
        return next_page
    if is_safe_back_url(back_url):
        return back_url
    return url_for('landing')


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Для доступа к данной странице необходимо пройти процедуру аутентификации.'
    login_manager.login_message_category = 'warning'
    login_manager.user_loader(load_user)
    login_manager.init_app(app)


def load_user(user_id):
    return db.session.execute(db.select(User).filter_by(id=user_id)).scalar()


@bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    back_url = get_back_url('landing')
    next_url = request.form.get('next') or request.args.get('next') or ''
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(login=form.login.data)).scalar()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему.', 'success')
            return redirect(get_login_redirect_url(back_url))
        flash('Неверный логин или пароль.', 'danger')
    return render_template('auth/login.html', form=form, back_url=back_url, next_url=next_url)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('landing'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    back_url = get_back_url('landing')
    if request.method == 'POST':
        form.validate()
        # Проверяем что логин не занят
        if not form.login.errors and db.session.execute(db.select(User).filter_by(login=form.login.data)).scalar():
            form.login.errors.append('Этот логин уже занят.')

        # Проверяем что email не занят
        if not form.email.errors and db.session.execute(db.select(User).filter_by(email=form.email.data)).scalar():
            form.email.errors.append('Этот email уже используется.')

        if any(field.errors for field in form):
            return render_template('auth/register.html', form=form, back_url=back_url)

        user = User(
            login=form.login.data,
            first_name=form.first_name.data,
            second_name=form.second_name.data,
            email=form.email.data,
            city=form.city.data or None,
        )
        user.set_password(form.password.data)

        try:
            db.session.add(user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Ошибка при создании аккаунта. Попробуйте ещё раз.', 'danger')
            return render_template('auth/register.html', form=form, back_url=back_url)

        flash('Аккаунт создан успешно!', 'success')
        login_user(user)
        if user.is_admin:
            return redirect(url_for('admin.overview'))
        return redirect(back_url)

    return render_template('auth/register.html', form=form, back_url=back_url)
