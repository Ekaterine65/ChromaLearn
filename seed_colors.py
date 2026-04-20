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
    python seed_colors.py translate-use-cases — перевести подсказки use_case
    python seed_colors.py unseed    — очистить (только Color/Emotion/EmotionColor)
"""

import sys
import os
import re
import unicodedata
import json

import pandas as pd
from deep_translator import GoogleTranslator

PARQUET_PATH = os.path.join(os.path.dirname(__file__), "color_pedia.parquet")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "seed_colors_report.txt")
TRANSLATION_CACHE_PATH = os.path.join(os.path.dirname(__file__), "seed_translation_cache.json")
TRANSLATE_BATCH_SIZE = 100
USE_CASE_MAX_CHARS = 220


class SeedLog:
    def __init__(self, path: str):
        self.path = path
        self.lines: list[str] = []

    def add(self, text: str = "") -> None:
        self.lines.append(text)

    def section(self, title: str) -> None:
        self.add("")
        self.add("=" * 80)
        self.add(title)
        self.add("=" * 80)

    def write(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))
            f.write("\n")


class TranslationCache:
    def __init__(self, path: str):
        self.path = path
        self.items: dict[str, str] = {}
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.items = json.load(f)

    def get(self, source: str) -> str | None:
        return self.items.get(source)

    def set(self, source: str, translated: str) -> None:
        self.items[source] = translated

    def write(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2, sort_keys=True)


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


def normalize_translation(value: str) -> str | None:
    value = re.sub(r"\s+", " ", (value or "").strip())
    if not value:
        return None
    return value[:1].upper() + value[1:]


def shorten_use_case(value: str | None) -> str | None:
    value = re.sub(r"\s+", " ", (value or "").strip())
    if not value:
        return None
    if len(value) <= USE_CASE_MAX_CHARS:
        return value

    sentence_match = re.match(r"^(.+?[.!?])\s", value)
    if sentence_match:
        sentence = sentence_match.group(1).strip()
        if len(sentence) <= USE_CASE_MAX_CHARS:
            return sentence

    return value[:USE_CASE_MAX_CHARS].rsplit(" ", 1)[0].rstrip(".,;:") + "."


def has_cyrillic(value: str | None) -> bool:
    return bool(value and re.search(r"[А-Яа-яЁё]", value))


def iter_translate_batches(texts: list[str]):
    batch: list[str] = []
    for text in texts:
        if len(batch) >= TRANSLATE_BATCH_SIZE:
            yield batch
            batch = []

        batch.append(text)

    if batch:
        yield batch


def translate_texts_ru(
    texts: list[str],
    cache: TranslationCache | None = None,
) -> dict[str, str]:
    if not texts:
        return {}

    translated: dict[str, str] = {}
    texts_to_translate: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if text in seen:
            continue
        seen.add(text)
        cached = cache.get(text) if cache else None
        if cached:
            translated[text] = cached
        else:
            texts_to_translate.append(text)

    if not texts_to_translate:
        return translated

    translator = GoogleTranslator(source="en", target="ru")
    for batch in iter_translate_batches(texts_to_translate):
        for source in batch:
            try:
                value = translator.translate(source)
            except Exception:
                continue

            text = normalize_translation(value)
            if not text:
                continue
            translated[source] = text
            if cache:
                cache.set(source, text)
        if cache:
            cache.write()

    return translated


def seed():
    # Ленивый импорт — чтобы не падать если flask не настроен
    from app import app
    from models import db, Color, Emotion, EmotionColor
    report = SeedLog(REPORT_PATH)
    translation_cache = TranslationCache(TRANSLATION_CACHE_PATH)
    report.section("ChromaLearn seed_colors report")

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
    report.add(f"Dataset: {PARQUET_PATH}")
    report.add(f"Rows: {len(df)}")
    report.add(f"Columns: {list(df.columns)}")

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

        new_colors: list[dict] = []

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

            use_case = shorten_use_case(str(row.get("Use Case", "") or ""))

            new_colors.append({
                "name": name,
                "hex": hex_norm,
                "red": r,
                "green": g,
                "blue": b,
                "hue": hue,
                "saturate": sat,
                "lightness": light,
                "use_case": use_case,
            })
            existing_hex.add(hex_norm)
            colors_added += 1

        for data in new_colors:
            color = Color(**data)
            db.session.add(color)
            hex_to_color[data["hex"]] = color

        db.session.flush()  # получаем id у новых цветов
        print(f"   ✓ Добавлено: {colors_added} | Пропущено (дубли/невалидные): {colors_skipped}")
        report.section("Colors")
        report.add(f"Added: {colors_added}")
        report.add(f"Skipped duplicates/invalid: {colors_skipped}")
        report.add("Use Case translation: skipped during main seed")

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

        new_keywords: list[tuple[str, str]] = []
        for kw in sorted(all_keywords):
            if not is_valid_emotion(kw):
                emotions_skipped += 1
                continue
 
            name_norm = kw.strip().capitalize()
            dedup_key = normalize_name(name_norm)
 
            if dedup_key in existing_keys:
                emotions_skipped += 1
                continue
 
            new_keywords.append((kw, name_norm))
            existing_keys.add(dedup_key)

        translations = translate_texts_ru(
            [name for _, name in new_keywords],
            translation_cache,
        )

        emotions_translated = 0
        emotions_without_translation = 0
        emotions_missing: list[str] = []
        for kw, name_norm in new_keywords:
            name_ru = translations.get(name_norm)
            emotion = Emotion(
                name=name_norm,
                name_ru=name_ru,
            )
            db.session.add(emotion)
            existing_emotions[name_norm] = emotion
            emotions_added += 1
            if name_ru:
                emotions_translated += 1
            else:
                emotions_without_translation += 1
                emotions_missing.append(name_norm)

        db.session.flush()
        print(f"   ✓ Добавлено: {emotions_added} | Переведено: {emotions_translated} | Без перевода: {emotions_without_translation} | Пропущено (дубли): {emotions_skipped}")
        report.section("Associations")
        report.add(f"Added: {emotions_added}")
        report.add(f"Translated: {emotions_translated}")
        report.add(f"Without translation: {emotions_without_translation}")
        report.add(f"Skipped duplicates/invalid: {emotions_skipped}")
        if emotions_missing:
            report.add("")
            report.add("Associations without translation:")
            for value in sorted(emotions_missing):
                report.add(f"- {value}")

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
        report.section("EmotionColor links")
        report.add(f"Added: {links_added}")
        report.add(f"Skipped duplicates/not found: {links_skipped}")

        # Итог 
        def count(model):
            return db.session.execute(
                db.select(db.func.count()).select_from(model)
            ).scalar()

        color_count = count(Color)
        emotion_count = count(Emotion)
        emotion_color_count = count(EmotionColor)

        print("\n" + "═" * 50)
        print(f"  Color        : {color_count}")
        print(f"  Emotion      : {emotion_count}")
        print(f"  EmotionColor : {emotion_color_count}")
        print("═" * 50)
        report.section("Totals")
        report.add(f"Color: {color_count}")
        report.add(f"Emotion: {emotion_count}")
        report.add(f"EmotionColor: {emotion_color_count}")
        report.write()
        print(f"  Отчет        : {REPORT_PATH}")
        print("\n Готово!")


def unseed():
    from app import app
    from models import db, Color, Emotion, EmotionColor, Result, Task

    with app.app_context():
        deleted_r = db.session.execute(db.delete(Result)).rowcount
        deleted_t = db.session.execute(db.delete(Task)).rowcount
        deleted_ec = db.session.execute(db.delete(EmotionColor)).rowcount
        deleted_e  = db.session.execute(db.delete(Emotion)).rowcount
        deleted_c  = db.session.execute(db.delete(Color)).rowcount
        db.session.commit()
        print(
            "✓ Удалено: "
            f"Result={deleted_r}, Task={deleted_t}, "
            f"EmotionColor={deleted_ec}, Emotion={deleted_e}, Color={deleted_c}"
        )


def translate_use_cases(limit: int = 500):
    from app import app
    from models import db, Color

    report = SeedLog(REPORT_PATH)
    translation_cache = TranslationCache(TRANSLATION_CACHE_PATH)
    report.section("ChromaLearn use_case translation report")

    with app.app_context():
        candidates = db.session.execute(
            db.select(Color).where(Color.use_case.is_not(None), Color.use_case != "").order_by(Color.id)
        ).scalars()

        colors: list[Color] = []
        source_by_color: dict[int, str] = {}
        texts_to_translate: set[str] = set()
        scanned = 0
        already_ru = 0
        empty_source = 0

        for color in candidates:
            scanned += 1
            if has_cyrillic(color.use_case):
                already_ru += 1
                continue

            source = shorten_use_case(color.use_case)
            if not source:
                empty_source += 1
                continue

            colors.append(color)
            source_by_color[color.id] = source
            if not translation_cache.get(source):
                texts_to_translate.add(source)

            if len(colors) >= limit:
                break

        translations = translate_texts_ru(
            sorted(texts_to_translate),
            translation_cache,
        )

        updated = 0
        skipped = 0
        missing: set[str] = set()
        for color in colors:
            source = source_by_color.get(color.id)
            if not source:
                skipped += 1
                continue
            translated = translation_cache.get(source) or translations.get(source)
            if translated:
                color.use_case = translated
                updated += 1
            else:
                skipped += 1
                missing.add(source)

        db.session.commit()
        translation_cache.write()

        report.add(f"Limit: {limit}")
        report.add(f"Scanned colors: {scanned}")
        report.add(f"Already translated/skipped before selection: {already_ru}")
        report.add(f"Empty source/skipped before selection: {empty_source}")
        report.add(f"Selected untranslated colors: {len(colors)}")
        report.add(f"Updated use_case: {updated}")
        report.add(f"Skipped use_case: {skipped}")
        if missing:
            report.add("")
            report.add("Use Case values without translation:")
            for value in sorted(missing):
                report.add(f"- {value}")
        report.write()

        print(f"✓ Переведено use_case: {updated} | Выбрано: {len(colors)} | Уже были на русском: {already_ru} | Пропущено: {skipped}")
        print(f"  Отчет: {REPORT_PATH}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "unseed":
        unseed()
    elif len(sys.argv) > 1 and sys.argv[1] == "translate-use-cases":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 500
        translate_use_cases(limit=limit)
    else:
        seed()

