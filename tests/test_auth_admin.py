from models import User, UserRole, db


def create_user(login="user", role=UserRole.user):
    user = User(
        login=login,
        first_name="Test",
        second_name="User",
        email=f"{login}@example.test",
        role=role,
    )
    user.set_password("Password1!")
    db.session.add(user)
    db.session.commit()
    return user


def login_as(client, user):
    response = client.post(
        "/auth/login",
        data={"login": user.login, "password": "Password1!"},
    )
    assert response.status_code == 302


def logout(client):
    with client.session_transaction() as session:
        session.clear()


def test_registration_rejects_duplicate_login(client):
    create_user(login="taken")

    response = client.post(
        "/auth/register",
        data={
            "login": "taken",
            "first_name": "New",
            "second_name": "User",
            "email": "new@example.test",
            "city": "",
            "password": "Password1!",
            "confirm_password": "Password1!",
        },
    )

    assert response.status_code == 200
    assert db.session.execute(db.select(User).where(User.login == "taken")).scalars().all()
    assert db.session.execute(db.select(User).where(User.email == "new@example.test")).scalar() is None


def test_registration_rejects_duplicate_email(client):
    create_user(login="existing")

    response = client.post(
        "/auth/register",
        data={
            "login": "newuser",
            "first_name": "New",
            "second_name": "User",
            "email": "existing@example.test",
            "city": "",
            "password": "Password1!",
            "confirm_password": "Password1!",
        },
    )

    assert response.status_code == 200
    assert db.session.execute(db.select(User).where(User.login == "newuser")).scalar() is None


def test_registration_rejects_weak_and_mismatched_passwords(client):
    response = client.post(
        "/auth/register",
        data={
            "login": "newuser",
            "first_name": "New",
            "second_name": "User",
            "email": "new@example.test",
            "city": "",
            "password": "password",
            "confirm_password": "different",
        },
    )

    assert response.status_code == 200
    assert db.session.execute(db.select(User).where(User.login == "newuser")).scalar() is None


def test_login_rejects_wrong_password(client):
    create_user(login="regular")

    response = client.post(
        "/auth/login",
        data={"login": "regular", "password": "wrong-password"},
    )

    assert response.status_code == 200
    with client.session_transaction() as session:
        assert "_user_id" not in session


def test_profile_requires_login(client):
    response = client.get("/profile")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_profile_edit_updates_basic_fields(client):
    user = create_user(login="regular")
    login_as(client, user)

    response = client.post(
        "/profile/edit",
        data={
            "login": "regular2",
            "first_name": "Updated",
            "second_name": "Person",
            "email": "updated@example.com",
            "city": "Moscow",
            "current_password": "",
            "password": "",
            "confirm_password": "",
        },
    )

    assert response.status_code == 302
    updated = db.session.get(User, user.id)
    assert updated.login == "regular2"
    assert updated.first_name == "Updated"
    assert updated.email == "updated@example.com"
    assert updated.city == "Moscow"


def test_profile_edit_requires_current_password_for_password_change(client):
    user = create_user(login="regular")
    login_as(client, user)

    response = client.post(
        "/profile/edit",
        data={
            "login": "regular",
            "first_name": "Test",
            "second_name": "User",
            "email": "regular@example.test",
            "city": "",
            "current_password": "",
            "password": "NewPassword1!",
            "confirm_password": "NewPassword1!",
        },
    )

    assert response.status_code == 200
    unchanged = db.session.get(User, user.id)
    assert unchanged.check_password("Password1!")


def test_profile_edit_rejects_duplicate_login_and_email(client):
    user = create_user(login="regular")
    create_user(login="taken")
    login_as(client, user)

    response = client.post(
        "/profile/edit",
        data={
            "login": "taken",
            "first_name": "Test",
            "second_name": "User",
            "email": "taken@example.test",
            "city": "",
            "current_password": "",
            "password": "",
            "confirm_password": "",
        },
    )

    assert response.status_code == 200
    unchanged = db.session.get(User, user.id)
    assert unchanged.login == "regular"
    assert unchanged.email == "regular@example.test"


def test_grafana_auth_statuses(client):
    assert client.get("/admin/grafana-auth").status_code == 401

    regular = create_user(login="regular")
    login_as(client, regular)
    assert client.get("/admin/grafana-auth").status_code == 403

    logout(client)
    admin = create_user(login="admin", role=UserRole.admin)
    login_as(client, admin)
    response = client.get("/admin/grafana-auth")
    assert response.status_code == 204
    assert response.headers["X-WEBAUTH-USER"] == "admin"


def test_admin_pages_redirect_to_grafana_dashboards(client):
    admin = create_user(login="admin", role=UserRole.admin)
    login_as(client, admin)

    response = client.get("/admin/tasks")

    assert response.status_code == 302
    assert response.headers["Location"].startswith(
        "/admin/grafana/d/chromalearn-tasks/"
    )
