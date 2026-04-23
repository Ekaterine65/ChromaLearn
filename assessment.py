from __future__ import annotations

from math import sqrt
from typing import Iterable

from models import Color, EmotionColor, HarmonyType, Result, Task, db

DEFAULT_TOLERANCE_DEGREES = 18.0

LEVEL_WEIGHTS = {
    1: {"harmony": 0.50, "emotion": 0.50, "contrast": 0, "color_vision": 0},
    2: {"harmony": 0.50, "emotion": 0.50, "contrast": 0, "color_vision": 0},
    3: {"harmony": 0.20, "emotion": 0.25, "contrast": 0.30, "color_vision": 0.25},
}

HARMONY_OFFSETS = {
    HarmonyType.complementary: [180.0],
    HarmonyType.analogous: [30.0],
    HarmonyType.triadic: [120.0, 240.0],
    HarmonyType.monochromatic: [0.0],
}

HARMONY_MIN_CORE_COLORS = {
    HarmonyType.monochromatic: 3,
    HarmonyType.analogous: 3,
    HarmonyType.complementary: 2,
    HarmonyType.triadic: 3,
}

def calculate_solution_scores(
    task: Task,
    palette: Iterable[str],
    harmony_type: HarmonyType | None = None,
) -> dict:
    colors = normalize_palette(palette)
    harmony = calculate_harmony_score(colors, harmony_type or task.harmony_type)
    emotion = calculate_emotion_score(colors, task.emotion_id)
    contrast = None
    color_vision = None

    # Accessibility criteria are part of the expert level only. For levels 1-2
    # the API returns None and the frontend hides these fixed modal rows.
    if task.level_number == 3:
        contrast = calculate_contrast_score(colors)
        color_vision = calculate_color_vision_score(colors)

    total_score = calculate_total_score(
        task.level_number,
        harmony["score"],
        emotion["score"],
        contrast["score"] if contrast else None,
        color_vision["score"] if color_vision else None,
    )

    return {
        "level": task.level_number,
        "weights": LEVEL_WEIGHTS.get(task.level_number, LEVEL_WEIGHTS[1]),
        "harmony": harmony,
        "emotion": emotion,
        "contrast": contrast,
        "color_vision": color_vision,
        "total_score": total_score,
    }


def process_task_submission(task: Task, palette: list, harmony_type: str | None, current_user) -> dict:
    harmony_used = task.harmony_type

    scores = calculate_solution_scores(task, palette, harmony_used)
    detected_harmony = scores["harmony"]["details"].get("detected_harmony")
    if not harmony_used and detected_harmony:
        harmony_used = HarmonyType(detected_harmony)

    saved = store_task_result(task, scores, harmony_used, current_user)
    meta = build_result_meta(scores["total_score"])
    contrast = scores["contrast"]
    color_vision = scores["color_vision"]

    return {
        "saved": saved,
        "total_score": scores["total_score"],
        "conclusion": meta["conclusion"],
        "summary": meta["summary"],
        "weights": scores["weights"],
        "harmony_score": scores["harmony"]["score"],
        "harmony_details": scores["harmony"]["details"],
        "emotion_score": scores["emotion"]["score"],
        "emotion_details": scores["emotion"]["details"],
        "contrast_score": contrast["score"] if contrast else None,
        "contrast_details": contrast["details"] if contrast else None,
        "color_vision_score": color_vision["score"] if color_vision else None,
        "color_vision_details": color_vision["details"] if color_vision else None,
    }


def store_task_result(task: Task, scores: dict, harmony_used: HarmonyType | None, current_user) -> bool:
    if not current_user.is_authenticated:
        return False

    result = Result(
        user_id=current_user.id,
        task_id=task.id,
        score_emotion=scores["emotion"]["score"],
        score_harmony=scores["harmony"]["score"],
        score_contrast=scores["contrast"]["score"] if scores["contrast"] else None,
        score_colorblind=scores["color_vision"]["score"] if scores["color_vision"] else None,
        score_total=scores["total_score"],
        harmony_used=harmony_used,
    )
    db.session.add(result)
    db.session.commit()
    return True


def calculate_harmony_score(
    palette: list[str],
    harmony_type: HarmonyType | None,
    tolerance_degrees: float = DEFAULT_TOLERANCE_DEGREES,
) -> dict:
    if len(palette) < 2:
        return {"score": 0, "details": {"message": "Недостаточно цветов для проверки гармонии."}}

    if harmony_type:
        return calculate_harmony_for_type(palette, harmony_type, tolerance_degrees)

    candidates = {
        harmony.value: calculate_harmony_for_type(palette, harmony, tolerance_degrees)
        for harmony in HARMONY_OFFSETS
    }
    detected_harmony, best_result = max(candidates.items(), key=lambda item: item[1]["score"])
    details = dict(best_result["details"])
    details["detected_harmony"] = detected_harmony
    details["candidates"] = {
        name: result["score"]
        for name, result in candidates.items()
    }
    return {"score": best_result["score"], "details": details}


def calculate_harmony_for_type(
    palette: list[str],
    harmony_type: HarmonyType,
    tolerance_degrees: float,
) -> dict:
    colors = filter_harmony_colors(palette)
    filtered = len(colors) != len(palette)
    if len(colors) < 2 and harmony_type != HarmonyType.monochromatic:
        colors = palette
        filtered = False
    if len(colors) < 2:
        return {
            "score": 0,
            "details": {
                "harmony_type": harmony_type.value,
                "filtered": filtered,
                "used_colors": colors,
                "message": "Недостаточно значимых цветов для проверки гармонии.",
            },
        }

    hsl_values = [
        hsl_dict(color)
        for color in colors
    ]
    expected_offsets = HARMONY_OFFSETS.get(harmony_type, [0.0])
    base_results = [
        calculate_base_harmony_result(
            hsl_values,
            index,
            harmony_type,
            expected_offsets,
            tolerance_degrees,
        )
        for index in range(len(hsl_values))
    ]
    best = max(base_results, key=lambda result: result["core_score"])
    correction = calculate_sl_correction(hsl_values)
    score = clamp_score(best["core_score"] + correction)

    return {
        "score": score,
        "details": {
            "harmony_type": harmony_type.value,
            "base_color": best["base_color"],
            "base_hue": round(best["base_hue"], 2),
            "tolerance_degrees": tolerance_degrees,
            "filtered": filtered,
            "used_colors": [item["color"] for item in hsl_values],
            "hue_score": best["hue_score"],
            "core_score": best["core_score"],
            "core_count": best["core_count"],
            "required_core_count": HARMONY_MIN_CORE_COLORS[harmony_type],
            "sl_correction": correction,
            "checked": best["checked"],
        },
    }


def calculate_base_harmony_result(
    hsl_values: list[dict],
    base_index: int,
    harmony_type: HarmonyType,
    expected_offsets: list[float],
    tolerance_degrees: float,
) -> dict:
    base = hsl_values[base_index]
    checked = []
    matches = 0

    for index, item in enumerate(hsl_values):
        if index == base_index:
            continue
        distance = circular_distance(item["hue"], base["hue"])
        error = min(abs(distance - offset) for offset in expected_offsets)
        matched = error <= tolerance_degrees
        matches += int(matched)
        checked.append({
            "color": item["color"],
            "hue": round(item["hue"], 2),
            "distance": round(distance, 2),
            "matched": matched,
        })

    core_count = 1 + matches
    required_core_count = HARMONY_MIN_CORE_COLORS[harmony_type]
    hue_score = round(matches / max(len(checked), 1) * 100)
    core_score = calculate_core_harmony_score(
        harmony_type,
        core_count,
        required_core_count,
        len(hsl_values),
        hue_score,
    )

    return {
        "base_color": base["color"],
        "base_hue": base["hue"],
        "hue_score": hue_score,
        "core_score": core_score,
        "core_count": core_count,
        "checked": checked,
    }


def calculate_core_harmony_score(
    harmony_type: HarmonyType,
    core_count: int,
    required_core_count: int,
    color_count: int,
    hue_score: int,
) -> int:
    if harmony_type == HarmonyType.monochromatic:
        if color_count < 2:
            return 0
        if color_count == 2:
            return min(hue_score, 70)
        if core_count >= 4:
            return max(hue_score, 95)
        if core_count >= required_core_count:
            return max(hue_score, 85)
        return round(hue_score * core_count / required_core_count)

    if core_count >= required_core_count:
        return 100

    return round(hue_score * core_count / required_core_count)


def filter_harmony_colors(palette: list[str]) -> list[str]:
    return [
        color
        for color in palette
        if is_harmony_relevant_color(color)
    ]


def is_harmony_relevant_color(color: str) -> bool:
    _, saturation, lightness = hex_to_hsl(color)
    return saturation >= 12 and 8 <= lightness <= 94


def hsl_dict(color: str) -> dict:
    hue, saturation, lightness = hex_to_hsl(color)
    return {
        "color": color,
        "hue": hue,
        "saturation": saturation,
        "lightness": lightness,
    }


def calculate_sl_correction(hsl_values: list[dict]) -> int:
    saturations = [item["saturation"] for item in hsl_values]
    lightnesses = [item["lightness"] for item in hsl_values]
    saturation_range = max(saturations) - min(saturations)
    lightness_range = max(lightnesses) - min(lightnesses)
    penalty = min(8, round(saturation_range / 25 + lightness_range / 30))
    return -penalty


def calculate_emotion_score(palette: list[str], emotion_id: int | None) -> dict:
    if not palette:
        return {"score": 0, "details": {"message": "Палитра не содержит валидных HEX-цветов."}}
    if not emotion_id:
        return {"score": 100, "details": {"message": "У задания нет связанной эмоции."}}

    reference_colors = db.session.execute(
        db.select(Color)
        .join(EmotionColor, EmotionColor.color_id == Color.id)
        .where(EmotionColor.emotion_id == emotion_id)
        .limit(120)
    ).scalars().all()

    if not reference_colors:
        return {"score": 50, "details": {"message": "В базе нет эталонных цветов для этой эмоции."}}

    reference_hsl = [(c.hue, c.saturate, c.lightness) for c in reference_colors]
    similarities = []
    for color in palette:
        color_hsl = hex_to_hsl(color)
        nearest = min(hsl_distance(color_hsl, ref) for ref in reference_hsl)
        similarities.append(max(0.0, 1.0 - nearest / 180.0))

    score = round(sum(similarities) / len(similarities) * 100)
    return {
        "score": score,
        "details": {
            "reference_count": len(reference_colors),
            "method": "nearest_hsl_reference",
        },
    }


def calculate_contrast_score(palette: list[str], required_ratio: float = 4.5) -> dict:
    if len(palette) < 4:
        return {"score": 0, "details": {"message": "Для WCAG нужны цвет фона и цвет текста."}}

    background = palette[0]
    text = palette[3]
    ratio = contrast_ratio(text, background)
    score = round(min(ratio / required_ratio, 1.0) * 100)
    passed = ratio >= required_ratio
    return {
        "score": score,
        "details": {
            "text": text,
            "background": background,
            "ratio": round(ratio, 2),
            "required_ratio": required_ratio,
            "passed": passed,
        },
    }


def calculate_color_vision_score(palette: list[str]) -> dict:
    if len(palette) < 2:
        return {"score": 0, "details": {"message": "Недостаточно цветов для симуляции."}}

    simulation_scores = {}
    for vision_type in ("protanopia", "deuteranopia", "tritanopia"):
        simulated = [simulate_color_vision(color, vision_type) for color in palette]
        min_distance = min_pair_distance(simulated)
        simulation_scores[vision_type] = round(min(1.0, min_distance / 70.0) * 100)

    score = round(sum(simulation_scores.values()) / len(simulation_scores))
    return {"score": score, "details": simulation_scores}


def calculate_total_score(
    level: int,
    harmony: int,
    emotion: int,
    contrast: int | None,
    color_vision: int | None,
) -> int:
    weights = LEVEL_WEIGHTS.get(level, LEVEL_WEIGHTS[1])
    score = (
        weights["harmony"] * clamp_score(harmony)
        + weights["emotion"] * clamp_score(emotion)
        + weights["contrast"] * clamp_score(contrast or 0)
        + weights["color_vision"] * clamp_score(color_vision or 0)
    )
    return clamp_score(round(score))


def normalize_palette(palette: Iterable[str]) -> list[str]:
    colors = []
    for color in palette:
        if isinstance(color, str) and is_hex_color(color):
            colors.append(color.upper())
    return colors[:5]


def is_hex_color(value: str) -> bool:
    if len(value) != 7 or value[0] != "#":
        return False
    return all(ch in "0123456789abcdefABCDEF" for ch in value[1:])


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    return (
        int(hex_color[1:3], 16),
        int(hex_color[3:5], 16),
        int(hex_color[5:7], 16),
    )


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    r, g, b = [component / 255.0 for component in hex_to_rgb(hex_color)]
    max_value = max(r, g, b)
    min_value = min(r, g, b)
    lightness = (max_value + min_value) / 2.0

    if max_value == min_value:
        return 0.0, 0.0, lightness * 100.0

    delta = max_value - min_value
    saturation = delta / (2.0 - max_value - min_value) if lightness > 0.5 else delta / (max_value + min_value)

    if max_value == r:
        hue = ((g - b) / delta + (6 if g < b else 0)) / 6.0
    elif max_value == g:
        hue = ((b - r) / delta + 2) / 6.0
    else:
        hue = ((r - g) / delta + 4) / 6.0

    return hue * 360.0, saturation * 100.0, lightness * 100.0


def circular_distance(a: float, b: float) -> float:
    delta = abs(a - b)
    return min(delta, 360.0 - delta)


def hsl_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    hue = circular_distance(a[0], b[0]) / 180.0
    saturation = abs(a[1] - b[1]) / 100.0
    lightness = abs(a[2] - b[2]) / 100.0
    return sqrt((hue * 120.0) ** 2 + (saturation * 40.0) ** 2 + (lightness * 40.0) ** 2)


def relative_luminance(hex_color: str) -> float:
    def linearize(component: int) -> float:
        value = component / 255.0
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    r, g, b = [linearize(component) for component in hex_to_rgb(hex_color)]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground: str, background: str) -> float:
    l1 = relative_luminance(foreground)
    l2 = relative_luminance(background)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def simulate_color_vision(hex_color: str, vision_type: str) -> tuple[int, int, int]:
    rgb_to_lms = (
        (0.31399022, 0.63951294, 0.04649755),
        (0.15537241, 0.75789446, 0.08670142),
        (0.01775239, 0.10944209, 0.87256922),
    )
    lms_to_rgb = (
        (5.47221206, -4.64196010, 0.16963708),
        (-1.12524190, 2.29317094, -0.16789520),
        (0.02980165, -0.19318073, 1.16364789),
    )
    matrices = {
        "protanopia": (
            (0.000000, 2.023440, -2.525810),
            (0.000000, 1.000000, 0.000000),
            (0.000000, 0.000000, 1.000000),
        ),
        "deuteranopia": (
            (1.000000, 0.000000, 0.000000),
            (0.494207, 0.000000, 1.248270),
            (0.000000, 0.000000, 1.000000),
        ),
        "tritanopia": (
            (1.000000, 0.000000, 0.000000),
            (0.000000, 1.000000, 0.000000),
            (-0.395913, 0.801109, 0.000000),
        ),
    }

    linear_rgb = tuple(srgb_to_linear(component / 255.0) for component in hex_to_rgb(hex_color))
    lms = multiply_matrix_vector(rgb_to_lms, linear_rgb)
    simulated_lms = multiply_matrix_vector(matrices[vision_type], lms)
    simulated_rgb = multiply_matrix_vector(lms_to_rgb, simulated_lms)
    return tuple(
        max(0, min(255, round(linear_to_srgb(component) * 255.0)))
        for component in simulated_rgb
    )


def srgb_to_linear(value: float) -> float:
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def linear_to_srgb(value: float) -> float:
    value = max(0.0, min(1.0, value))
    if value <= 0.0031308:
        return value * 12.92
    return 1.055 * (value ** (1.0 / 2.4)) - 0.055


def multiply_matrix_vector(
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(
        sum(matrix[row][col] * vector[col] for col in range(3))
        for row in range(3)
    )


def min_pair_distance(colors: list[tuple[int, int, int]]) -> float:
    min_distance = 441.67
    for index, color in enumerate(colors):
        for other in colors[index + 1:]:
            distance = rgb_distance(color, other)
            min_distance = min(min_distance, distance)
    return min_distance


def rgb_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


def clamp_score(value: int | float) -> int:
    return max(0, min(100, round(value)))


def build_result_meta(total_score: int) -> dict:
    if total_score >= 85:
        return {
            "conclusion": "Отлично",
            "summary": "Палитра согласована с заданием и проходит ключевые проверки.",
        }
    if total_score >= 70:
        return {
            "conclusion": "Хорошо",
            "summary": "Решение в целом корректно, но один или несколько критериев можно усилить.",
        }
    if total_score >= 50:
        return {
            "conclusion": "Удовлетворительно",
            "summary": "Основная идея читается, однако требуется доработка по слабым критериям.",
        }
    return {
        "conclusion": "Необходимо повторить",
        "summary": "Палитру стоит пересобрать с учетом гармонии, эмоции и доступности.",
    }
