from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from tools import LoginForm, RegistrationForm

bp = Blueprint('auth', __name__, url_prefix='/auth')


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
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).filter_by(login=form.login.data)).scalar()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему.', 'success')
            next_page = request.args.get('next')
            if current_user.is_admin:
                return redirect(url_for('admin.overview'))
            return redirect(next_page or url_for('landing'))
        flash('Неверный логин или пароль.', 'danger')
    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('landing'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Проверяем что логин не занят
        if db.session.execute(db.select(User).filter_by(login=form.login.data)).scalar():
            form.login.errors.append('Этот логин уже занят.')
            return render_template('auth/register.html', form=form)

        # Проверяем что email не занят
        if db.session.execute(db.select(User).filter_by(email=form.email.data)).scalar():
            form.email.errors.append('Этот email уже используется.')
            return render_template('auth/register.html', form=form)

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
            return render_template('auth/register.html', form=form)

        flash('Аккаунт создан успешно!', 'success')
        login_user(user)
        return redirect(url_for('landing'))

    return render_template('auth/register.html', form=form)