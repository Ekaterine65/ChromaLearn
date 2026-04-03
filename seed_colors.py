"""
seed_colors.py — заполнение таблиц Color, Emotion, EmotionColor
из датасета boltuix/color-pedia (color_pedia.parquet).

Скачать датасет:
    pip install huggingface_hub
    python -c "from huggingface_hub import hf_hub_download; hf_hub_download(repo_id='boltuix/color-pedia', filename='color_pedia.parquet', repo_type='dataset', local_dir='.')"

Или вручную с https://huggingface.co/datasets/boltuix/color-pedia/tree/main
Положить color_pedia.parquet рядом с этим файлом (или указать путь в PARQUET_PATH).

Запуск:
    python seed_colors.py           — заполнить
    python seed_colors.py unseed    — очистить (только Color/Emotion/EmotionColor)
"""

import sys
import os
import re
import unicodedata

import pandas as pd

PARQUET_PATH = os.path.join(os.path.dirname(__file__), "color_pedia.parquet")


# Словарь эмодзи для ключевых слов датасета 
KEYWORD_EMOJI: dict[str, str] = {
    # Энергия / сила
    "passionate":   "🔥",
    "intense":      "⚡",
    "bold":         "💪",
    "powerful":     "💥",
    "strong":       "🦾",
    "energetic":    "⚡",
    "dynamic":      "🌀",
    "vibrant":      "🌈",
    "fiery":        "🔥",
    "fierce":       "🐯",
    "dominant":     "👑",
    "aggressive":   "⚔️",
    "dramatic":     "🎭",
    "exciting":     "🎉",
    "stimulating":  "💡",
    "active":       "🏃",
    "lively":       "🎊",
    "adventurous":  "🧭",
    "daring":       "🎯",
    "confident":    "😎",
    "determined":   "🎯",
    "ambitious":    "🚀",
    "courageous":   "🦁",
    "bold":         "💪",

    # Спокойствие / мир
    "calm":         "🌊",
    "peaceful":     "☮️",
    "serene":       "🏔️",
    "tranquil":     "🍃",
    "relaxing":     "😌",
    "soothing":     "💆",
    "gentle":       "🌸",
    "soft":         "🌸",
    "tender":       "🤍",
    "mild":         "🌤️",
    "quiet":        "🤫",
    "still":        "🌿",
    "harmonious":   "☯️",
    "balanced":     "⚖️",
    "stable":       "🏛️",
    "grounded":     "🌱",
    "steady":       "⚓",

    # Радость / счастье
    "happy":        "😊",
    "joyful":       "😄",
    "cheerful":     "☀️",
    "playful":      "🎈",
    "fun":          "🎉",
    "optimistic":   "🌟",
    "uplifting":    "🎆",
    "warm":         "🌞",
    "sunny":        "☀️",
    "bright":       "✨",
    "positive":     "➕",
    "delightful":   "🌼",
    "whimsical":    "🦋",
    "festive":      "🎊",
    "radiant":      "🌟",

    # Печаль / меланхолия
    "sad":          "😢",
    "melancholic":  "🌧️",
    "gloomy":       "🌑",
    "dark":         "🖤",
    "mysterious":   "🌙",
    "moody":        "🌫️",
    "somber":       "🪦",
    "deep":         "🌊",
    "heavy":        "⛓️",
    "brooding":     "🌩️",

    # Природа
    "natural":      "🌿",
    "earthy":       "🌍",
    "organic":      "🍀",
    "fresh":        "🌱",
    "lush":         "🌴",
    "verdant":      "🍃",
    "floral":       "🌺",
    "forest":       "🌲",
    "botanical":    "🌿",
    "ocean":        "🌊",
    "aquatic":      "🐬",
    "marine":       "🌊",
    "sky":          "🌤️",
    "airy":         "💨",

    # Роскошь / элегантность
    "luxurious":    "💎",
    "elegant":      "👗",
    "sophisticated":"🎩",
    "refined":      "✨",
    "royal":        "👑",
    "majestic":     "🦁",
    "opulent":      "💰",
    "rich":         "💎",
    "prestigious":  "🏆",
    "glamorous":    "💫",
    "graceful":     "🩰",
    "classic":      "🎻",
    "timeless":     "⌛",
    "regal":        "👑",

    # Минимализм / чистота
    "clean":        "🧹",
    "pure":         "🤍",
    "minimal":      "◻️",
    "simple":       "⬜",
    "crisp":        "❄️",
    "clear":        "💧",
    "fresh":        "🌱",
    "neutral":      "⚪",
    "subtle":       "🌫️",
    "understated":  "🔇",
    "light":        "☁️",
    "airy":         "💨",

    # Романтика
    "romantic":     "🌹",
    "loving":       "❤️",
    "sensual":      "🌹",
    "intimate":     "💕",
    "tender":       "🤍",
    "sweet":        "🍬",
    "charming":     "✨",
    "dreamy":       "💭",
    "feminine":     "🌸",

    # Профессионализм / доверие
    "trustworthy":  "🤝",
    "reliable":     "🛡️",
    "professional": "💼",
    "corporate":    "🏢",
    "authoritative":"⚖️",
    "secure":       "🔒",
    "dependable":   "🤝",
    "honest":       "🤝",

    # Творчество
    "creative":     "🎨",
    "artistic":     "🖌️",
    "imaginative":  "💭",
    "innovative":   "💡",
    "unique":       "🦄",
    "expressive":   "🎭",
    "inspired":     "✨",
    "spiritual":    "🕊️",
    "mystical":     "🔮",
    "magical":      "🪄",
    "enchanting":   "✨",

    # Прочее
    "cool":         "😎",
    "modern":       "🏙️",
    "retro":        "🕹️",
    "vintage":      "📷",
    "industrial":   "⚙️",
    "urban":        "🏙️",
    "rustic":       "🏡",
    "cozy":         "🛋️",
    "inviting":     "🚪",
    "welcoming":    "🤗",
    "nurturing":    "🌱",
    "healing":      "💚",
    "revitalizing": "⚡",
    "refreshing":   "💧",
    "invigorating": "🌬️",
    "exotic":       "🌺",
    "tropical":     "🌴",
    "bold":         "💪",
    "striking":     "⚡",
    "captivating":  "👁️",
    "alluring":     "💫",
    "intriguing":   "🔍",
}

FALLBACK_EMOJI = "🎨"


def keyword_to_emoji(word: str) -> str:
    """Возвращает эмодзи для ключевого слова (регистронезависимо)."""
    return KEYWORD_EMOJI.get(word.lower().strip(), FALLBACK_EMOJI)


def parse_keywords(raw: str) -> list[str]:
    """
    Парсит поле Keywords датасета в список чистых слов.
    'Powerful, Passionate, Bold, Deep.' → ['Powerful', 'Passionate', 'Bold', 'Deep']
    """
    if not raw or not isinstance(raw, str):
        return []
    parts = re.split(r"[,\.]+", raw)
    result = []
    for p in parts:
        word = p.strip()
        if word and len(word) >= 2:
            result.append(word)
    return result


def hex_to_rgb(hex_code: str) -> tuple[int, int, int]:
    """#RRGGBB → (R, G, B)"""
    h = hex_code.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def normalize_name(word: str) -> str:
    """
    Нормализует слово для дедупа
    """
    nfkd = unicodedata.normalize("NFKD", word)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().strip()
  
def is_valid_emotion(word: str) -> bool:
    """
    Отфильтровывает мусор из Keywords:
    - только ASCII-буквы и дефис (никаких цифр, спецсимволов, диакритики)
    - длина от 3 до 40 символов
    """
    stripped = word.strip()
    if not stripped or len(stripped) < 3 or len(stripped) > 40:
        return False
    if not re.match(r"^[A-Za-z][A-Za-z\-]*$", stripped):
        return False
    return True

def normalize_hex(hex_code: str) -> str:
    """Приводим к верхнему регистру с #."""
    return "#" + hex_code.lstrip("#").upper()


def seed():
    # Ленивый импорт — чтобы не падать если flask не настроен
    from app import app
    from models import db, Color, Emotion, EmotionColor

    if not os.path.exists(PARQUET_PATH):
        print(f"❌ Файл не найден: {PARQUET_PATH}")
        print()
        print("Скачайте датасет одним из способов:")
        print()
        print("  Способ 1 (huggingface_hub):")
        print("    pip install huggingface_hub")
        print("    python -c \"from huggingface_hub import hf_hub_download; \\")
        print("      hf_hub_download(repo_id='boltuix/color-pedia',")
        print("        filename='color_pedia.parquet', repo_type='dataset', local_dir='.')\"")
        print()
        print("  Способ 2 (вручную):")
        print("    https://huggingface.co/datasets/boltuix/color-pedia/tree/main")
        print("    Скачайте color_pedia.parquet и положите рядом с seed_colors.py")
        sys.exit(1)

    print(f"Читаем {PARQUET_PATH} ...")
    df = pd.read_parquet(PARQUET_PATH)
    print(f"   Строк в датасете: {len(df)}")
    print(f"   Колонки: {list(df.columns)}")

    with app.app_context():

        # 1. Цвета (Color) 
        print("\n Загружаем цвета...")

        # Собираем уже существующие hex в БД (дедуп)
        existing_hex: set[str] = {
            row.hex for row in db.session.execute(db.select(Color)).scalars()
        }

        colors_added = 0
        colors_skipped = 0
        # Карта hex → Color-объект для построения EmotionColor
        hex_to_color: dict[str, Color] = {
            row.hex: row
            for row in db.session.execute(db.select(Color)).scalars()
        }

        for _, row in df.iterrows():
            raw_hex = str(row.get("HEX Code", "") or "").strip()
            if not raw_hex or not re.match(r"^#?[0-9A-Fa-f]{6}$", raw_hex):
                colors_skipped += 1
                continue

            hex_norm = normalize_hex(raw_hex)

            if hex_norm in existing_hex:
                colors_skipped += 1
                continue

            # RGB
            try:
                r = int(row["R"])
                g = int(row["G"])
                b = int(row["B"])
            except (KeyError, ValueError, TypeError):
                r, g, b = hex_to_rgb(hex_norm)

            # HSL 
            try:
                hue = float(row["Hue"])
                sat = float(row["Saturation"])
                light = float(row["Lightness"])
            except (KeyError, ValueError, TypeError):
                hue = sat = light = None

            name = str(row.get("Color Name", "") or "").strip() or None
            if name and len(name) > 200:
                name = name[:200].rstrip()

            use_case = str(row.get("Use Case", "") or "").strip() or None

            color = Color(
                name=name,
                hex=hex_norm,
                red=r,
                green=g,
                blue=b,
                hue=hue,
                saturate=sat,
                lightness=light,
                use_case=use_case,
            )
            db.session.add(color)
            existing_hex.add(hex_norm)
            hex_to_color[hex_norm] = color
            colors_added += 1

        db.session.flush()  # получаем id у новых цветов
        print(f"   ✓ Добавлено: {colors_added} | Пропущено (дубли/невалидные): {colors_skipped}")

        # 2. Эмоции (Emotion)
        print("\n Извлекаем эмоции из Keywords...")

        existing_emotions: dict[str, Emotion] = {
            row.name: row
            for row in db.session.execute(db.select(Emotion)).scalars()
        }

        emotions_added = 0
        emotions_skipped = 0

        all_keywords: set[str] = set()
        for _, row in df.iterrows():
            for kw in parse_keywords(str(row.get("Keywords", "") or "")):
                all_keywords.add(kw)

        existing_keys: set[str] = {normalize_name(k) for k in existing_emotions}

        for kw in sorted(all_keywords):
            if not is_valid_emotion(kw):
                emotions_skipped += 1
                continue
 
            name_norm = kw.strip().capitalize()
            dedup_key = normalize_name(name_norm)
 
            if dedup_key in existing_keys:
                emotions_skipped += 1
                continue
 
            emoji_char = keyword_to_emoji(kw)
            emotion = Emotion(name=name_norm, emoji=emoji_char)
            db.session.add(emotion)
            existing_emotions[name_norm] = emotion
            existing_keys.add(dedup_key)
            emotions_added += 1

        db.session.flush()
        print(f"   ✓ Добавлено: {emotions_added} | Пропущено (дубли): {emotions_skipped}")

        # 3. EmotionColor 
        print("\n Строим связи EmotionColor...")

        existing_pairs: set[tuple[int, int]] = {
            (row.emotion_id, row.color_id)
            for row in db.session.execute(db.select(EmotionColor)).scalars()
        }

        emotion_lower: dict[str, Emotion] = {
            k.lower(): v for k, v in existing_emotions.items()
        }

        links_added = 0
        links_skipped = 0

        for _, row in df.iterrows():
            raw_hex = str(row.get("HEX Code", "") or "").strip()
            if not raw_hex:
                continue
            hex_norm = normalize_hex(raw_hex)
            color = hex_to_color.get(hex_norm)
            if not color or not color.id:
                continue

            keywords = parse_keywords(str(row.get("Keywords", "") or ""))
            for kw in keywords:
                emotion = emotion_lower.get(kw.lower().strip())
                if not emotion or not emotion.id:
                    links_skipped += 1
                    continue

                pair = (emotion.id, color.id)
                if pair in existing_pairs:
                    links_skipped += 1
                    continue

                db.session.add(EmotionColor(emotion=emotion, color=color))
                existing_pairs.add(pair)
                links_added += 1

        db.session.commit()
        print(f"   ✓ Добавлено: {links_added} | Пропущено (дубли/не найдены): {links_skipped}")

        # Итог 
        def count(model):
            return db.session.execute(
                db.select(db.func.count()).select_from(model)
            ).scalar()

        print("\n" + "═" * 50)
        print(f"  Color        : {count(Color)}")
        print(f"  Emotion      : {count(Emotion)}")
        print(f"  EmotionColor : {count(EmotionColor)}")
        print("═" * 50)
        print("\n Готово!")


def unseed():
    from app import app
    from models import db, Color, Emotion, EmotionColor

    with app.app_context():
        deleted_ec = db.session.execute(db.delete(EmotionColor)).rowcount
        deleted_e  = db.session.execute(db.delete(Emotion)).rowcount
        deleted_c  = db.session.execute(db.delete(Color)).rowcount
        db.session.commit()
        print(f"✓ Удалено: EmotionColor={deleted_ec}, Emotion={deleted_e}, Color={deleted_c}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "unseed":
        unseed()
    else:
        seed()
