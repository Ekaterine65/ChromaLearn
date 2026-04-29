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

ROLE_WEIGHTS = [0.30, 0.25, 0.20, 0.10, 0.15]
CONTRAST_SURFACE_WEIGHTS = [0.40, 0.35, 0.25]
NORMAL_TEXT_WEIGHT = 0.70
LARGE_TEXT_WEIGHT = 0.30
FAILED_NORMAL_CAP = 60
FAILED_LARGE_CAP = 35

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


def process_task_submission(task: Task, palette: list, current_user) -> dict:
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
    result = Result(
        user_id=current_user.id if current_user.is_authenticated else None,
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
    weighted_sum = 0.0
    weights_used = []
    weighted_matches = []

    for index, color in enumerate(palette):
        color_hsl = hex_to_hsl(color)
        nearest = min(hsl_distance(color_hsl, ref) for ref in reference_hsl)
        similarity = max(0.0, 1.0 - nearest / 120.0)
        weight = ROLE_WEIGHTS[index] if index < len(ROLE_WEIGHTS) else 0.0
        similarities.append({
            "color": color,
            "slot": index,
            "weight": weight,
            "distance": round(nearest, 2),
            "similarity": round(similarity, 4),
        })
        weights_used.append(weight)
        weighted_sum += similarity * weight
        weighted_matches.append(similarity * weight)

    total_weight = sum(weights_used) or 1.0
    base_score = weighted_sum / total_weight * 100
    emotion_core_bonus = calculate_emotion_core_bonus(weighted_matches, total_weight)
    score = clamp_score(round(base_score + emotion_core_bonus))
    return {
        "score": score,
        "details": {
            "reference_count": len(reference_colors),
            "method": "nearest_hsl_reference",
            "role_weights": ROLE_WEIGHTS[:len(palette)],
            "weighted": True,
            "base_score": round(base_score, 2),
            "emotion_core_bonus": round(emotion_core_bonus, 2),
            "matches": similarities,
        },
    }


def calculate_emotion_core_bonus(weighted_matches: list[float], total_weight: float) -> float:
    if len(weighted_matches) < 2:
        return 0.0

    strongest = sorted(weighted_matches, reverse=True)[:2]
    normalized_core = sum(strongest) / total_weight
    return max(0.0, normalized_core - 0.35) * 18.0


def calculate_contrast_score(palette: list[str], required_ratio: float = 4.5) -> dict:
    if len(palette) < 4:
        return {"score": 0, "details": {"message": "Для WCAG нужны цвет фона и цвет текста."}}

    text = palette[3]
    backgrounds = palette[:3]
    surface_names = ["background", "surface", "accent"]
    checks = []
    weighted_sum = 0.0
    total_weight = sum(CONTRAST_SURFACE_WEIGHTS)
    passed_normal_count = 0

    for index, background in enumerate(backgrounds):
        ratio = contrast_ratio(text, background)
        normal_score = contrast_score_from_ratio(ratio, required_ratio)
        large_score = contrast_score_from_ratio(ratio, 3.0)
        surface_score = normal_score * NORMAL_TEXT_WEIGHT + large_score * LARGE_TEXT_WEIGHT
        normal_passed = ratio >= required_ratio
        large_passed = ratio >= 3.0

        if not normal_passed:
            surface_score = min(surface_score, FAILED_NORMAL_CAP)
        if not large_passed:
            surface_score = min(surface_score, FAILED_LARGE_CAP)

        passed_normal_count += int(normal_passed)
        weighted_sum += surface_score * CONTRAST_SURFACE_WEIGHTS[index]
        checks.append({
            "surface": surface_names[index],
            "background": background,
            "ratio": round(ratio, 2),
            "normal_passed": normal_passed,
            "large_passed": large_passed,
            "normal_score": round(normal_score),
            "large_score": round(large_score),
            "surface_score": round(surface_score),
        })

    base_score = weighted_sum / total_weight if total_weight else 0
    normal_pass_factor = passed_normal_count / len(checks) if checks else 0
    score = round(base_score * (0.55 + 0.45 * normal_pass_factor))
    passed_pairs = sum(
        int(check["normal_passed"]) + int(check["large_passed"])
        for check in checks
    )

    return {
        "score": score,
        "details": {
            "text": text,
            "normal_required_ratio": required_ratio,
            "large_required_ratio": 3.0,
            "normal_weight": NORMAL_TEXT_WEIGHT,
            "large_weight": LARGE_TEXT_WEIGHT,
            "failed_normal_cap": FAILED_NORMAL_CAP,
            "failed_large_cap": FAILED_LARGE_CAP,
            "surface_weights": CONTRAST_SURFACE_WEIGHTS,
            "base_score": round(base_score, 2),
            "passed_normal_count": passed_normal_count,
            "normal_pass_factor": round(normal_pass_factor, 2),
            "checks": checks,
            "passed_pairs": passed_pairs,
            "total_pairs": len(checks) * 2,
        },
    }


def contrast_score_from_ratio(ratio: float, required_ratio: float) -> float:
    if required_ratio <= 1.0:
        return 100.0
    normalized = (ratio - 1.0) / (required_ratio - 1.0)
    return max(0.0, min(100.0, normalized * 100.0))


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


def build_color_vision_preview_response(palette: list[str]) -> dict:
    colors = normalize_palette(palette)
    return {
        "palettes": {
            "normal": colors,
            "protanopia": [rgb_to_hex(simulate_color_vision(color, "protanopia")) for color in colors],
            "deuteranopia": [rgb_to_hex(simulate_color_vision(color, "deuteranopia")) for color in colors],
            "tritanopia": [rgb_to_hex(simulate_color_vision(color, "tritanopia")) for color in colors],
        }
    }


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


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{component:02X}" for component in rgb)


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
    saturation = abs(a[1] - b[1]) / 120.0
    lightness = abs(a[2] - b[2]) / 120.0
    return sqrt((hue * 100.0) ** 2 + (saturation * 50.0) ** 2 + (lightness * 70.0) ** 2)


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
    matrices = {
        "protanopia": (
            (0.152286, 1.052583, -0.204868),
            (0.114503, 0.786281, 0.099216),
            (-0.003882, -0.048116, 1.051998),
        ),
        "deuteranopia": (
            (0.367322, 0.860646, -0.227968),
            (0.280085, 0.672501, 0.047413),
            (-0.011820, 0.042940, 0.968881),
        ),
        "tritanopia": (
            (1.255528, -0.076749, -0.178779),
            (-0.078411, 0.930809, 0.147602),
            (0.004733, 0.691367, 0.303900),
        ),
    }

    matrix = matrices.get(vision_type)
    if not matrix:
        return hex_to_rgb(hex_color)

    linear_rgb = tuple(srgb_to_linear(component / 255.0) for component in hex_to_rgb(hex_color))
    simulated_rgb = multiply_matrix_vector(matrix, linear_rgb)
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
