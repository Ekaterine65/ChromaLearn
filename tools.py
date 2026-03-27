from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators


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
    password = PasswordField('Пароль', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
        validators.EqualTo('confirm_password', message='Пароли должны совпадать'),
        validators.Length(min=6, message='Пароль должен быть не короче 6 символов'),
    ])
    confirm_password = PasswordField('Подтвердите пароль', [
        validators.DataRequired(message='Поле обязательно для заполнения'),
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