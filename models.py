import enum
from typing import Optional, List
from datetime import datetime

import sqlalchemy as sa
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, DateTime, ForeignKey, MetaData, Float, Text
from werkzeug.security import generate_password_hash, check_password_hash


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


db = SQLAlchemy(model_class=Base)

class UserRole(enum.Enum):
    user  = "user"
    admin = "admin"

class HarmonyType(enum.Enum):
    analogous     = "analogous"
    complementary = "complementary"
    triadic       = "triadic"
    monochromatic = "monochromatic"


class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[UserRole] = mapped_column(sa.Enum(UserRole), default=UserRole.user)
    first_name: Mapped[str] = mapped_column(String(100))
    second_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    city: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    results: Mapped[List["Result"]] = relationship(back_populates="user")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.second_name}"

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.admin

    def __repr__(self) -> str:
        return f"<User {self.login!r}>"


class Emotion(Base):
    __tablename__ = "emotions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    name_ru: Mapped[Optional[str]] = mapped_column(String(100))
    emoji: Mapped[Optional[str]] = mapped_column(String(10))

    tasks: Mapped[List["Task"]] = relationship(back_populates="emotion")
    emotion_colors: Mapped[List["EmotionColor"]] = relationship(back_populates="emotion")

    def __repr__(self) -> str:
        return f"<Emotion {self.name!r}>"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    level_number: Mapped[int] = mapped_column(Integer)
    emotion_id: Mapped[Optional[int]] = mapped_column(ForeignKey("emotions.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(String(1000))
    harmony_type: Mapped[Optional[HarmonyType]] = mapped_column(sa.Enum(HarmonyType))

    emotion: Mapped[Optional["Emotion"]] = relationship(back_populates="tasks")
    results: Mapped[List["Result"]] = relationship(back_populates="task")

    def __repr__(self) -> str:
        return f"<Task {self.title!r} (level {self.level_number})>"


class Color(Base):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    hex: Mapped[str] = mapped_column(String(7))
    red: Mapped[int] = mapped_column(Integer)
    green: Mapped[int] = mapped_column(Integer)
    blue: Mapped[int] = mapped_column(Integer)
    hue: Mapped[float] = mapped_column(Float)
    saturate: Mapped[float] = mapped_column(Float)
    lightness: Mapped[float] = mapped_column(Float)
    use_case: Mapped[Optional[str]] = mapped_column(Text)

    emotion_colors: Mapped[List["EmotionColor"]] = relationship(back_populates="color")

    def __repr__(self) -> str:
        return f"<Color {self.hex!r}>"


class EmotionColor(Base):
    __tablename__ = "emotion_colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    emotion_id: Mapped[int] = mapped_column(ForeignKey("emotions.id"))
    color_id: Mapped[int] = mapped_column(ForeignKey("colors.id"))

    emotion: Mapped["Emotion"] = relationship(back_populates="emotion_colors")
    color: Mapped["Color"] = relationship(back_populates="emotion_colors")

    def __repr__(self) -> str:
        return f"<EmotionColor emotion={self.emotion_id} color={self.color_id}>"


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    score_emotion: Mapped[int] = mapped_column(Integer)
    score_harmony: Mapped[int] = mapped_column(Integer)
    score_contrast: Mapped[Optional[int]] = mapped_column(Integer)
    score_colorblind: Mapped[Optional[int]] = mapped_column(Integer)
    score_total: Mapped[int] = mapped_column(Integer)
    harmony_used: Mapped[Optional[HarmonyType]] = mapped_column(sa.Enum(HarmonyType))
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="results")
    task: Mapped["Task"] = relationship(back_populates="results")

    def __repr__(self) -> str:
        return f"<Result user={self.user_id} task={self.task_id} score={self.score_total}>"
