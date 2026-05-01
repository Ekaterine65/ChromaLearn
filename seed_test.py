"""
seed_db.py — заполнение БД тестовыми данными для ChromaLearn.

Запуск:
    python seed_db.py
    python seed_db.py unseed
"""

from datetime import datetime, timedelta
import os
import random
import secrets
from app import app
from models import db, User, UserRole, Emotion, Task, Color, EmotionColor, Result, HarmonyType

SEED_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD") or secrets.token_urlsafe(18)
SEED_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD") or secrets.token_urlsafe(18)


def seed():
    with app.app_context():
        # ── Пользователи ────────────────────────────────────────────────────
        admin = User(
            login="admin",
            role=UserRole.admin,
            first_name="Анна",
            second_name="Дмитриева",
            email="admin@chromalearn.ru",
            city="Москва",
            created_at=datetime(2024, 9, 1),
        )
        admin.set_password(SEED_ADMIN_PASSWORD)

        user1 = User(
            login="alexey",
            role=UserRole.user,
            first_name="Алексей",
            second_name="Иванов",
            email="alex@example.com",
            city="Москва",
            created_at=datetime(2025, 1, 10),
        )
        user1.set_password(SEED_USER_PASSWORD)

        user2 = User(
            login="maria",
            role=UserRole.user,
            first_name="Мария",
            second_name="Соколова",
            email="maria@example.com",
            city="Санкт-Петербург",
            created_at=datetime(2025, 2, 5),
        )
        user2.set_password(SEED_USER_PASSWORD)

        db.session.add_all([admin, user1, user2])
        db.session.commit()
        print("✓ Пользователи созданы")

        # ── Эмоции ──────────────────────────────────────────────────────────
        emotions_data = [
            ("Спокойствие",     "🌊"),
            ("Энергия",         "🔥"),
            ("Таинственность",  "🌙"),
            ("Минимализм",      "🌿"),
            ("Нежность",        "🌸"),
            ("Рассвет",         "🌅"),
            ("Океан",           "🌊"),
            ("Контраст",        "🖤"),
            ("Арктика",         "❄️"),
            ("Ночной город",    "🌃"),
            ("Осень",           "🍂"),
            ("Доступность",     "♿"),
        ]
        emotions = {}
        for name, emoji in emotions_data:
            e = Emotion(name=name, emoji=emoji)
            db.session.add(e)
            emotions[name] = e
        db.session.commit()
        print("✓ Эмоции созданы")

        # ── Цвета ───────────────────────────────────────────────────────────
        colors_data = [
            # hex,        name,            R,   G,   B,   H,   S,   L
            ("#4a90d9", "Синий",          74,  144, 217, 210,  64,  57),
            ("#5bb37e", "Зелёный",        91,  179, 126, 144,  32,  53),
            ("#8da8c0", "Серо-голубой",  141,  168, 192, 207,  20,  65),
            ("#c8a96e", "Золотистый",    200,  169, 110,  37,  41,  61),
            ("#9b59b6", "Фиолетовый",    155,   89, 182, 283,  35,  53),
            ("#e74c3c", "Красный",       231,   76,  60,   4,  77,  57),
            ("#1abc9c", "Мятный",         26,  188, 156, 168,  76,  42),
            ("#f39c12", "Оранжевый",     243,  156,  18,  37,  90,  51),
        ]
        colors = []
        for hex_, name, r, g, b, h, s, l in colors_data:
            c = Color(hex=hex_, name=name, red=r, green=g, blue=b, hue=h, saturate=s, lightness=l)
            db.session.add(c)
            colors.append(c)
        db.session.commit()
        print("✓ Цвета созданы")

        # ── EmotionColor ─────────────────────────────────────────────────────
        for i in [0, 1, 2]:
            db.session.add(EmotionColor(emotion=emotions["Спокойствие"], color=colors[i]))
        for i in [5, 7, 4]:
            db.session.add(EmotionColor(emotion=emotions["Энергия"], color=colors[i]))
        for i in [6, 3]:
            db.session.add(EmotionColor(emotion=emotions["Нежность"], color=colors[i]))
        db.session.commit()
        print("✓ EmotionColor привязки созданы")

        # ── Задания ──────────────────────────────────────────────────────────
        tasks_data = [
            (1, "Спокойствие",    "Спокойствие",
             "Назначьте 5 цветов по ролям, передающих умиротворение и тишину.",
             HarmonyType.analogous),
            (1, "Энергия",        "Энергия",
             "Создайте палитру, передающую динамику и мощь.",
             HarmonyType.complementary),
            (1, "Нежность",       "Нежность",
             "Подберите мягкую монохроматическую палитру нежности.",
             HarmonyType.monochromatic),
            (1, "Рассвет",        "Рассвет",
             "Передайте тёплые оттенки рассветного неба аналоговой гармонией.",
             HarmonyType.analogous),
            (1, "Осень",          "Осень",
             "Отразите золото и багрянец осени в палитре.",
             HarmonyType.analogous),
            (2, "Таинственность", "Таинственность",
             "Создайте палитру загадочности и глубины без подсказок.",
             None),
            (2, "Минимализм",     "Минимализм",
             "Монохроматическая палитра с минимумом оттенков.",
             HarmonyType.monochromatic),
            (2, "Океан",          "Океан",
             "Погрузитесь в глубины океана через цвет.",
             HarmonyType.analogous),
            (2, "Ночной город",   "Ночной город",
             "Передайте атмосферу ночного мегаполиса триадной гармонией.",
             HarmonyType.triadic),
            (3, "Доступность",    "Доступный интерфейс",
             "Создайте палитру WCAG 2.1 AA для людей с нарушениями зрения.",
             None),
            (3, "Контраст",       "Контраст",
             "Максимальный контраст с соблюдением WCAG AA и гармонии.",
             HarmonyType.complementary),
            (3, "Арктика",        "Арктика",
             "Монохромная ледяная палитра с проверкой WCAG AAA.",
             HarmonyType.monochromatic),
        ]

        tasks = []
        for level, emo_name, title, desc, harmony in tasks_data:
            t = Task(
                level_number=level,
                emotion=emotions[emo_name],
                title=title,
                description=desc,
                harmony_type=harmony,
            )
            db.session.add(t)
            tasks.append(t)
        db.session.commit()
        print("✓ Задания созданы")

        # ── Результаты ───────────────────────────────────────────────────────
        results_data = [
            (0,  85, 91, None, None, 94,  HarmonyType.analogous,      2,  5),
            (1,  80, 82, None, None, 81,  HarmonyType.complementary,  5,  3),
            (5,  80, 72, None, None, 76,  None,                        7,  7),
            (6,  91, 91, None, None, 91,  HarmonyType.monochromatic,  14,  2),
            (9,  70, 78, 31,   23,   63,  None,                       30, 11),
            (3,  88, 87, None, None, 88,  HarmonyType.analogous,      42,  2),
            (7,  79, 79, None, None, 79,  HarmonyType.analogous,      60,  4),
            (10, 71, 78, 64,   38,   71,  HarmonyType.complementary,  60,  9),
            (2,  96, 96, None, None, 96,  HarmonyType.monochromatic,  90,  1),
            (8,  68, 68, None, None, 68,  HarmonyType.triadic,        90,  6),
            (4,  85, 85, None, None, 85,  HarmonyType.analogous,      120, 3),
            (11, 58, 62, 31,   23,   58,  HarmonyType.monochromatic,  150, 14),
        ]

        now = datetime.now()
        for task_idx, sc_emo, sc_har, sc_con, sc_cb, sc_tot, harmony, days_ago, attempts in results_data:
            for attempt in range(attempts):
                is_last = (attempt == attempts - 1)
                score_mult = 0.7 + 0.3 * (attempt / max(attempts - 1, 1))
                r = Result(
                    user=user1,
                    task=tasks[task_idx],
                    score_emotion=int(sc_emo * (score_mult if not is_last else 1.0)),
                    score_harmony=int(sc_har * (score_mult if not is_last else 1.0)),
                    score_contrast=int(sc_con * score_mult) if sc_con else None,
                    score_colorblind=int(sc_cb * score_mult) if sc_cb else None,
                    score_total=int(sc_tot * (score_mult if not is_last else 1.0)),
                    harmony_used=harmony,
                    completed_at=now - timedelta(days=days_ago) + timedelta(hours=attempt),
                )
                db.session.add(r)

        for task_idx, score in [(0, 82), (1, 75), (2, 90), (5, 68)]:
            r = Result(
                user=user2,
                task=tasks[task_idx],
                score_emotion=score - 5,
                score_harmony=score,
                score_contrast=None,
                score_colorblind=None,
                score_total=score,
                harmony_used=tasks[task_idx].harmony_type,
                completed_at=now - timedelta(days=random.randint(5, 60)),
            )
            db.session.add(r)

        db.session.commit()
        print("✓ Результаты созданы")

        # ── Итог ─────────────────────────────────────────────────────────────
        def count(model):
            return db.session.execute(db.select(db.func.count()).select_from(model)).scalar()

        print("\n" + "═" * 50)
        print(f"  Пользователи : {count(User)}")
        print(f"  Эмоции       : {count(Emotion)}")
        print(f"  Задания      : {count(Task)}")
        print(f"  Цвета        : {count(Color)}")
        print(f"  Результаты   : {count(Result)}")
        print("═" * 50)
        print("\n✅ БД заполнена. Тестовые аккаунты:")
        print(f"   admin / {SEED_ADMIN_PASSWORD}  →  роль: admin")
        print(f"   alexey / {SEED_USER_PASSWORD}  →  роль: user (с историей)")
        print(f"   maria / {SEED_USER_PASSWORD}   →  роль: user")


def unseed():
    with app.app_context():
        db.session.execute(db.delete(Result))
        db.session.execute(db.delete(EmotionColor))
        db.session.execute(db.delete(Task))
        db.session.execute(db.delete(Color))
        db.session.execute(db.delete(Emotion))
        for login in ("admin", "alexey", "maria"):
            u = db.session.execute(db.select(User).filter_by(login=login)).scalar()
            if u:
                db.session.delete(u)
        db.session.commit()
        print("✓ Тестовые данные удалены")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "unseed":
        unseed()
    else:
        seed()
