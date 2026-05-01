from flask_login import AnonymousUserMixin

from assessment import (
    calculate_color_vision_score,
    calculate_contrast_score,
    calculate_emotion_score,
    calculate_harmony_score,
    calculate_solution_scores,
    calculate_total_score,
    normalize_palette,
    process_task_submission,
)
from models import Color, Emotion, EmotionColor, HarmonyType, Result, Task, db


def test_normalize_palette_keeps_valid_hex_uppercase_and_limits_to_five():
    palette = normalize_palette([
        "#ffffff",
        "not-a-color",
        "#000000",
        "#abc123",
        "#DEF456",
        "#111111",
        "#222222",
    ])

    assert palette == ["#FFFFFF", "#000000", "#ABC123", "#DEF456", "#111111"]


def test_level_three_total_score_uses_accessibility_weights():
    score = calculate_total_score(
        level=3,
        harmony=100,
        emotion=80,
        contrast=50,
        color_vision=20,
    )

    assert score == 60


def test_level_one_and_two_total_scores_ignore_accessibility_criteria():
    assert calculate_total_score(1, harmony=100, emotion=80, contrast=0, color_vision=0) == 90
    assert calculate_total_score(2, harmony=20, emotion=80, contrast=100, color_vision=100) == 50


def test_solution_scores_include_accessibility_only_for_level_three(app):
    level_two_task = Task(level_number=2, title="Level 2", description="Task")
    level_three_task = Task(level_number=3, title="Level 3", description="Task")

    level_two = calculate_solution_scores(
        level_two_task,
        ["#FFFFFF", "#F2F2F2", "#E0E0E0", "#000000", "#777777"],
    )
    level_three = calculate_solution_scores(
        level_three_task,
        ["#FFFFFF", "#F2F2F2", "#E0E0E0", "#000000", "#777777"],
    )

    assert level_two["contrast"] is None
    assert level_two["color_vision"] is None
    assert level_three["contrast"]["score"] >= 90
    assert isinstance(level_three["color_vision"]["score"], int)


def test_harmony_score_accepts_good_palettes_for_each_harmony_type():
    cases = [
        (HarmonyType.analogous, ["#FF0000", "#FF8000", "#FFFF00"]),
        (HarmonyType.complementary, ["#FF0000", "#00FFFF"]),
        (HarmonyType.triadic, ["#FF0000", "#00FF00", "#0000FF"]),
        (HarmonyType.monochromatic, ["#1F4E79", "#2F75B5", "#5B9BD5"]),
    ]

    for harmony_type, palette in cases:
        result = calculate_harmony_score(palette, harmony_type)
        assert result["score"] >= 80, (harmony_type, result)


def test_harmony_score_penalizes_bad_palette_for_requested_harmony():
    result = calculate_harmony_score(
        ["#FF0000", "#00FF00", "#0000FF"],
        HarmonyType.monochromatic,
    )

    assert result["score"] < 50


def test_contrast_score_rewards_accessible_text_against_surfaces():
    result = calculate_contrast_score(["#FFFFFF", "#F2F2F2", "#E0E0E0", "#000000"])

    assert result["score"] >= 90
    assert all(check["normal_passed"] for check in result["details"]["checks"])


def test_contrast_score_penalizes_low_contrast_text():
    result = calculate_contrast_score(["#FFFFFF", "#F8F8F8", "#EEEEEE", "#DDDDDD"])

    assert result["score"] < 50
    assert not any(check["normal_passed"] for check in result["details"]["checks"])


def test_color_vision_score_distinguishes_clear_and_similar_palettes():
    clear = calculate_color_vision_score(["#000000", "#FFFFFF", "#0057B8"])
    similar = calculate_color_vision_score(["#FF0000", "#00AA00", "#AA5500"])

    assert clear["score"] > similar["score"]
    assert set(clear["details"]) == {"protanopia", "deuteranopia", "tritanopia"}


def test_emotion_score_uses_reference_colors(app):
    emotion = Emotion(name="calm", name_ru="Calm")
    color = Color(
        name="Reference blue",
        hex="#336699",
        red=51,
        green=102,
        blue=153,
        hue=210,
        saturate=50,
        lightness=40,
        use_case="Reference",
    )
    db.session.add_all([emotion, color])
    db.session.flush()
    db.session.add(EmotionColor(emotion_id=emotion.id, color_id=color.id))
    db.session.commit()

    matching = calculate_emotion_score(["#336699", "#2F5F8F"], emotion.id)
    distant = calculate_emotion_score(["#FF0000", "#00FF00"], emotion.id)

    assert matching["score"] > distant["score"]
    assert matching["details"]["reference_count"] == 1


def test_process_task_submission_stores_anonymous_result(app):
    task = Task(
        level_number=1,
        title="Calm",
        description="Build a calm palette",
        harmony_type=HarmonyType.monochromatic,
    )
    db.session.add(task)
    db.session.commit()

    response = process_task_submission(
        task,
        ["#224466", "#2A557F", "#336699", "#3D7AB8", "#478FD6"],
        AnonymousUserMixin(),
    )

    saved_result = db.session.execute(db.select(Result)).scalar_one()
    assert response["saved"] is True
    assert saved_result.user_id is None
    assert saved_result.task_id == task.id
    assert saved_result.score_total == response["total_score"]
