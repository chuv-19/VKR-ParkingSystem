import os

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import re
import shutil
from pathlib import Path
from typing import Iterable, List, Tuple, Dict

import cv2
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
KNOWN_PLATES_PATH = PROJECT_DIR / "known_plates.txt"

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

try:
    from paddleocr import PaddleOCR
    _HAS_PADDLE = True
except ImportError:
    PaddleOCR = None
    _HAS_PADDLE = False

try:
    import pytesseract
    _HAS_TESSERACT_PY = True
    if _HAS_TESSERACT_PY and not shutil.which("tesseract"):
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ):
            if Path(candidate).exists():
                pytesseract.pytesseract.tesseract_cmd = candidate
                break
except ImportError:
    pytesseract = None
    _HAS_TESSERACT_PY = False


def _check_tesseract_binary() -> bool:
    if not _HAS_TESSERACT_PY:
        return False
    return bool(shutil.which("tesseract") or getattr(pytesseract.pytesseract, 'tesseract_cmd', None))


RUS_LATIN_MAP = {
    "A": "А", "B": "В", "E": "Е", "K": "К", "M": "М",
    "H": "Н", "O": "О", "P": "Р", "C": "С", "T": "Т",
    "Y": "У", "X": "Х",
}
RUS_TO_LATIN_MAP = {rus: eng for eng, rus in RUS_LATIN_MAP.items()}

RUS_VALID_CHARS = set("АВЕКМНОРСТУХ0123456789")
RUS_LETTERS = set("АВЕКМНОРСТУХ")
DIGIT_CONFUSIONS = {"О": "0", "З": "3", "Ч": "4", "Б": "6", "Ь": "6", "Ъ": "6"}
LETTER_CONFUSIONS = {"0": "О", "3": "З", "4": "Ч", "6": "Б", "8": "В"}

RUS_PLATE_RE = re.compile(r"^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$")
LATIN_PLATE_RE = re.compile(r"^[ABEKMHOPCTYX]\d{3}[ABEKMHOPCTYX]{2}\d{2,3}$")

SCORE_PERFECT = 200

LATIN_DIGIT_CONFUSIONS = {
    "Z": "2",
    "T": "7",
    "Y": "7",
    "S": "5",
    "I": "1",
    "L": "1",
    "Q": "0",
    "D": "0",
}

CORE_PLATE_RE = re.compile(r"^[A-ZА-Я]\d{3}[A-ZА-Я]{2}$")
REGION_RE = re.compile(r"^\d{2,3}$")
COUNTRY_MARKS = {"RUS", "RUSI", "RUS1", "PYС", "РУС"}


def _to_latin_plate(text: str) -> str:
    return "".join(RUS_TO_LATIN_MAP.get(ch, ch) for ch in text)


def _score_plate_text(text: str) -> int:
    text = _post_process_ru_plate_cyr(text)
    if not text:
        return -1000
    if RUS_PLATE_RE.match(text):
        return SCORE_PERFECT
    score = 0
    if 7 <= len(text) <= 9:
        score += 40
    elif 6 <= len(text) <= 10:
        score += 20
    else:
        score -= max(0, len(text) - 10) * 10
    if re.match(r"^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]", text):
        score += 40
    elif re.match(r"^[АВЕКМНОРСТУХ]\d{3}", text):
        score += 25
    if re.search(r"[АВЕКМНОРСТУХ]{2}\d{2,3}$", text):
        score += 20
    digits = sum(1 for c in text if "0" <= c <= "9")
    letters = sum(1 for c in text if c in RUS_LETTERS)
    if digits >= 3:
        score += 10
    if letters >= 3:
        score += 10
    return score


def _post_process_ru_plate_cyr(text: str) -> str:
    text = text.upper().replace(" ", "").replace("-", "").replace(".", "")
    text = text.replace("\n", "").replace("\r", "").replace("_", "")
    for eng, rus in RUS_LATIN_MAP.items():
        text = text.replace(eng, rus)
    for eng, digit in LATIN_DIGIT_CONFUSIONS.items():
        text = text.replace(eng, digit)
    text = "".join(c for c in text if c in RUS_VALID_CHARS)
    if len(text) < 6:
        return text
    t = list(text)
    for i in (1, 2, 3):
        if i < len(t) and t[i] in DIGIT_CONFUSIONS:
            t[i] = DIGIT_CONFUSIONS[t[i]]
    for i in (0, 4, 5):
        if i < len(t) and t[i] in LETTER_CONFUSIONS:
            t[i] = LETTER_CONFUSIONS[t[i]]
    for i in range(6, min(len(t), 9)):
        if t[i] in DIGIT_CONFUSIONS:
            t[i] = DIGIT_CONFUSIONS[t[i]]
    return "".join(t)


def post_process_ru_plate(text: str) -> str:
    """Normalize OCR output to the Latin Russian plate spelling used by the app."""
    return _to_latin_plate(_post_process_ru_plate_cyr(text))


def load_known_plates(path: Path = KNOWN_PLATES_PATH) -> List[str]:
    if not path.is_file():
        return []
    plates = []
    for line in path.read_text(encoding="utf-8").splitlines():
        plate = post_process_ru_plate(line.strip())
        if LATIN_PLATE_RE.match(plate):
            plates.append(plate)
    return plates


def _edit_distance(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(min(
                previous[j] + 1,
                current[j - 1] + 1,
                previous[j - 1] + (ca != cb),
            ))
        previous = current
    return previous[-1]


def snap_to_known_plate(text: str, known_plates: Iterable[str]) -> str:
    plate = post_process_ru_plate(text)
    if not plate:
        return plate

    best_plate = plate
    best_distance = 10**9
    for known in known_plates:
        known = post_process_ru_plate(known)
        if not known:
            continue
        distance = _edit_distance(plate, known)
        if known[0] != plate[0] and (len(plate) < 8 or distance > 2):
            continue
        if distance < best_distance:
            best_distance = distance
            best_plate = known

    max_distance = 2 if len(plate) >= 8 else 3
    if best_distance <= max_distance:
        return best_plate
    return plate


def plate_result_rank(
    result: dict,
    image_shape: Tuple[int, int] | Tuple[int, int, int] | None = None,
    known_plates: Iterable[str] = (),
) -> Tuple[int, int, int, int, int]:
    plate = post_process_ru_plate(result.get("plate_text", "") or result.get("raw_text", ""))
    text_score = _score_plate_text(plate)
    known = {post_process_ru_plate(p) for p in known_plates}
    known_bonus = 40 if plate in known else 0

    x1, y1, x2, y2 = result.get("box", (0, 0, 0, 0))
    area = max(0, x2 - x1) * max(0, y2 - y1)
    position_score = 0
    if image_shape is not None and len(image_shape) >= 2:
        h, w = image_shape[:2]
        if h > 0 and w > 0:
            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            position_score += int(cy * 40)
            if cy >= 0.45:
                position_score += 20
            elif cy < 0.25:
                position_score -= 35
            if 0.03 <= cx <= 0.97:
                position_score += 5

    return (text_score, known_bonus, position_score, area, len(plate))


def _candidate_texts(regions: Iterable[Tuple[str, float]]) -> List[str]:
    region_texts = [text.strip() for text, _ in regions if text and text.strip()]
    region_texts = [
        text for text in region_texts
        if re.sub(r"[^0-9A-Za-zА-Яа-я]", "", text.upper()) not in COUNTRY_MARKS
    ]
    candidates: List[str] = []

    joined = "".join(region_texts)
    if joined:
        candidates.append(joined)
    candidates.extend(text for text in region_texts if len(text) >= 2)

    for i in range(len(region_texts) - 1):
        pair = region_texts[i] + region_texts[i + 1]
        if len(pair) >= 4:
            candidates.append(pair)

    compact_regions = [
        re.sub(r"[^0-9A-Za-zА-Яа-я]", "", text.upper())
        for text in region_texts
    ]
    for core in compact_regions:
        if not CORE_PLATE_RE.match(core):
            continue
        for suffix in compact_regions:
            if REGION_RE.match(suffix):
                candidates.append(core + suffix)

    # OCR often returns an extra country mark, border, or split region. Score all
    # plausible plate-length windows instead of only the whole line.
    expanded: List[str] = []
    for candidate in candidates:
        compact = re.sub(r"[^0-9A-Za-zА-Яа-я]", "", candidate.upper())
        expanded.append(compact)
        for size in (9, 8):
            if len(compact) > size:
                expanded.extend(compact[i:i + size] for i in range(len(compact) - size + 1))

    deduped: List[str] = []
    seen = set()
    for candidate in expanded:
        if candidate and candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def _candidate_texts_with_confidence(regions: Iterable[Tuple[str, float]]) -> List[Tuple[str, float]]:
    region_items = [
        (text.strip(), float(score or 0.0))
        for text, score in regions
        if text and text.strip()
    ]
    region_items = [
        (text, score) for text, score in region_items
        if re.sub(r"[^0-9A-Za-zА-Яа-я]", "", text.upper()) not in COUNTRY_MARKS
    ]
    candidates: List[Tuple[str, float]] = []

    joined = "".join(text for text, _ in region_items)
    if joined:
        joined_conf = min((score for _, score in region_items), default=0.0)
        candidates.append((joined, joined_conf))
    candidates.extend((text, score) for text, score in region_items if len(text) >= 2)

    for i in range(len(region_items) - 1):
        pair = region_items[i][0] + region_items[i + 1][0]
        if len(pair) >= 4:
            candidates.append((pair, min(region_items[i][1], region_items[i + 1][1])))

    compact_regions = [
        (re.sub(r"[^0-9A-Za-zА-Яа-я]", "", text.upper()), score)
        for text, score in region_items
    ]
    for core, core_confidence in compact_regions:
        if not CORE_PLATE_RE.match(core):
            continue
        for suffix, suffix_confidence in compact_regions:
            if REGION_RE.match(suffix):
                candidates.append((core + suffix, min(core_confidence, suffix_confidence)))

    expanded: List[Tuple[str, float]] = []
    for candidate, confidence in candidates:
        compact = re.sub(r"[^0-9A-Za-zА-Яа-я]", "", candidate.upper())
        expanded.append((compact, confidence))
        for size in (9, 8):
            if len(compact) > size:
                expanded.extend(
                    (compact[i:i + size], confidence)
                    for i in range(len(compact) - size + 1)
                )

    best_by_candidate: Dict[str, float] = {}
    for candidate, confidence in expanded:
        if candidate:
            best_by_candidate[candidate] = max(confidence, best_by_candidate.get(candidate, 0.0))
    return list(best_by_candidate.items())


def _preprocess_plate(plate_img: np.ndarray) -> List[Tuple[str, np.ndarray]]:
    """Generate preprocessing variants in priority order for early exit."""
    gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))

    variants: List[Tuple[str, np.ndarray]] = []

    variants.append(("Original", plate_img.copy()))

    enhanced = clahe.apply(gray)
    variants.append(("CLAHE", cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)))

    _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("OTSU", cv2.cvtColor(otsu, cv2.COLOR_GRAY2BGR)))

    adapt = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 15, 4)
    variants.append(("Adaptive", cv2.cvtColor(adapt, cv2.COLOR_GRAY2BGR)))

    _, otsu_inv = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    variants.append(("OTSU Inv", cv2.cvtColor(otsu_inv, cv2.COLOR_GRAY2BGR)))

    denoised = cv2.fastNlMeansDenoising(gray, None, 12, 7, 21)
    _, denoised_otsu = cv2.threshold(clahe.apply(denoised), 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("Denoised", cv2.cvtColor(denoised_otsu, cv2.COLOR_GRAY2BGR)))

    return variants


def _paddle_recognise(ocr_engine, img: np.ndarray) -> List[Tuple[str, float]]:
    """Run PaddleOCR and return individual text regions with confidence."""
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    try:
        result = ocr_engine.ocr(img_rgb)
    except Exception:
        return []
    if not result:
        return []
    texts: List[str] = []
    scores: List[float] = []
    for item in result:
        texts.extend(item.get("rec_texts", []) or item.get("texts", []))
        scores.extend(item.get("rec_scores", []) or item.get("scores", []))
    return list(zip(texts, scores))


def detect_plate_boxes(model, image: np.ndarray, conf: float = 0.25) -> List[Tuple[int, int, int, int]]:
    results = model.predict(image, conf=conf, verbose=False)
    boxes: List[Tuple[int, int, int, int]] = []
    for r in results:
        if not hasattr(r, "boxes") or r.boxes is None:
            continue
        for box in r.boxes:
            xyxy = box.xyxy[0].cpu().numpy().astype(int)
            boxes.append(tuple(xyxy.tolist()))
    return boxes


def create_ocr_engines():
    engines = {}
    if _HAS_PADDLE:
        try:
            engines["paddle_en"] = PaddleOCR(
                lang="en",
                use_textline_orientation=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                text_rec_score_thresh=0.3,
            )
        except Exception:
            pass
        try:
            engines["paddle_ru"] = PaddleOCR(
                lang="ru",
                use_textline_orientation=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                text_rec_score_thresh=0.3,
            )
        except Exception:
            pass
    if _HAS_TESSERACT_PY and _check_tesseract_binary():
        engines["tesseract"] = "tesseract"
    return engines


def _tesseract_ocr(img: np.ndarray) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    whitelist = "ABCDEFGHIJKLMNOPQRSTUVWXYZАВЕКМНОРСТУХ0123456789"
    for psm in (7, 8, 13):
        config = f"--psm {psm} -c tessedit_char_whitelist={whitelist}"
        try:
            text = pytesseract.image_to_string(gray, lang="rus+eng", config=config)
        except pytesseract.pytesseract.TesseractError:
            try:
                text = pytesseract.image_to_string(gray, config=config)
            except Exception:
                continue
        text = text.strip()
        if text:
            return text
    return ""


def _ocr_input_images(crop: np.ndarray) -> List[np.ndarray]:
    if crop.size == 0:
        return []

    images = [
        cv2.resize(crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    ]
    h, w = crop.shape[:2]
    if 0 < w < 180:
        target_w = 360
        target_h = max(1, int(h * target_w / w))
        images.append(cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_CUBIC))
    return images


def recognise_plate(engines: dict, plate_img: np.ndarray) -> Tuple[str, Dict[str, np.ndarray]]:
    if not engines or plate_img.size == 0:
        return "", {}

    variants = _preprocess_plate(plate_img)
    variant_dict = {name: img for name, img in variants}
    best_text = ""
    best_processed = ""
    best_rank = (-1000, -1, -1.0)

    paddle_keys = [k for k in engines if k.startswith("paddle")]

    for name, img in variants:
        for engine_key in paddle_keys:
            engine = engines[engine_key]
            regions = _paddle_recognise(engine, img)
            for candidate, confidence in _candidate_texts_with_confidence(regions):
                processed = _post_process_ru_plate_cyr(candidate)
                score = _score_plate_text(processed)
                rank = (score, len(processed), confidence)
                if rank > best_rank:
                    best_rank = rank
                    best_text = candidate
                    best_processed = processed

    if best_rank[0] < SCORE_PERFECT:
        # No extra fallback needed here; tesseract will still be tried below.
        pass

    if best_rank[0] < SCORE_PERFECT and "tesseract" in engines:
        for name, img in variants:
            if best_rank[0] >= 120:
                break
            text = _tesseract_ocr(img)
            if text and len(text) >= 4:
                processed = _post_process_ru_plate_cyr(text)
                score = _score_plate_text(processed)
                rank = (score, len(processed), 0.0)
                if rank > best_rank:
                    best_rank = rank
                    best_text = text
                    best_processed = processed

    if best_rank[0] > 0 and best_processed and len(best_processed) > len(best_text) * 0.8:
        return _to_latin_plate(best_processed), variant_dict

    return best_text, variant_dict


def draw_boxes(image: np.ndarray, boxes: List[Tuple[int, int, int, int]],
               color: Tuple[int, int, int] = (0, 255, 0), thickness: int = 2) -> np.ndarray:
    result = image.copy()
    for (x1, y1, x2, y2) in boxes:
        cv2.rectangle(result, (x1, y1), (x2, y2), color, thickness)
    return result


class ANPRProcessor:
    def __init__(self, model_path: str):
        if YOLO is None:
            raise ImportError(
                "ultralytics is required for detection. Install dependencies with 'uv sync'."
            )
        self.model = YOLO(str(model_path))
        self.ocr_engines = create_ocr_engines()
        self.known_plates = load_known_plates()

    def process_image_boxes(
        self,
        img: np.ndarray,
        boxes: List[Tuple[int, int, int, int]],
        margin: int = 12,
    ) -> List[dict]:
        if img is None or img.size == 0:
            return []

        h, w = img.shape[:2]
        results = []

        for (x1, y1, x2, y2) in boxes:
            best_candidate = {
                "raw_text": "",
                "processed": "",
                "variants": {},
                "rank": (-1000, -1),
            }

            for crop_margin in (0, margin, margin * 2):
                x1m = max(0, x1 - crop_margin)
                y1m = max(0, y1 - crop_margin)
                x2m = min(w, x2 + crop_margin)
                y2m = min(h, y2 + crop_margin)
                candidate_crop = img[y1m:y2m, x1m:x2m]
                for crop_enlarged in _ocr_input_images(candidate_crop):
                    raw_text, variants = recognise_plate(self.ocr_engines, crop_enlarged)
                    processed = snap_to_known_plate(raw_text, self.known_plates)
                    rank = (_score_plate_text(processed), len(processed))
                    if rank > best_candidate["rank"]:
                        best_candidate = {
                            "raw_text": raw_text,
                            "processed": processed,
                            "variants": variants,
                            "rank": rank,
                        }
                    if best_candidate["rank"][0] >= SCORE_PERFECT:
                        break
                if best_candidate["rank"][0] >= SCORE_PERFECT:
                    break

            crop = img[
                max(0, y1 - margin):min(h, y2 + margin),
                max(0, x1 - margin):min(w, x2 + margin),
            ]
            result = {
                "box": (x1, y1, x2, y2),
                "crop": crop,
                "raw_text": best_candidate["raw_text"],
                "plate_text": best_candidate["processed"],
                "variants": best_candidate["variants"],
            }
            result["rank"] = plate_result_rank(result, img.shape, self.known_plates)
            results.append(result)

        results.sort(key=lambda result: result["rank"], reverse=True)
        return results

    def process(self, image_path: str, margin: int = 20) -> List[dict]:
        img = cv2.imread(str(image_path))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")

        h, w = img.shape[:2]
        boxes = detect_plate_boxes(self.model, img, conf=0.15)
        results = []

        for (x1, y1, x2, y2) in boxes:
            x1m = max(0, x1 - margin)
            y1m = max(0, y1 - margin)
            x2m = min(w, x2 + margin)
            y2m = min(h, y2 + margin)
            crop = img[y1m:y2m, x1m:x2m]

            best_candidate = {
                "raw_text": "",
                "processed": "",
                "variants": {},
                "rank": (-1000, -1),
            }

            for crop_margin in (0, 8, margin, 40):
                x1m = max(0, x1 - crop_margin)
                y1m = max(0, y1 - crop_margin)
                x2m = min(w, x2 + crop_margin)
                y2m = min(h, y2 + crop_margin)
                candidate_crop = img[y1m:y2m, x1m:x2m]
                for crop_enlarged in _ocr_input_images(candidate_crop):
                    raw_text, variants = recognise_plate(self.ocr_engines, crop_enlarged)
                    processed = snap_to_known_plate(raw_text, self.known_plates)
                    rank = (_score_plate_text(processed), len(processed))
                    if rank > best_candidate["rank"]:
                        best_candidate = {
                            "raw_text": raw_text,
                            "processed": processed,
                            "variants": variants,
                            "rank": rank,
                        }
                    if best_candidate["rank"][0] >= SCORE_PERFECT:
                        break
                if best_candidate["rank"][0] >= SCORE_PERFECT:
                    break

            raw_text = best_candidate["raw_text"]
            processed = best_candidate["processed"]
            variants = best_candidate["variants"]

            if len(processed) < 6:
                tight_x1 = max(0, x1 + 3)
                tight_y1 = max(0, y1 + 3)
                tight_x2 = min(w, x2 - 3)
                tight_y2 = min(h, y2 - 3)
                if tight_x2 > tight_x1 and tight_y2 > tight_y1:
                    tight_crop = img[tight_y1:tight_y2, tight_x1:tight_x2]
                    for tight_enlarged in _ocr_input_images(tight_crop):
                        raw_text2, variants2 = recognise_plate(self.ocr_engines, tight_enlarged)
                        proc2 = post_process_ru_plate(raw_text2)
                        if _score_plate_text(proc2) > _score_plate_text(processed):
                            raw_text = raw_text2
                            processed = proc2
                            variants = variants2
                        if _score_plate_text(processed) >= SCORE_PERFECT:
                            break

            result = {
                "box": (x1, y1, x2, y2),
                "crop": crop,
                "raw_text": raw_text,
                "plate_text": processed,
                "variants": variants,
            }
            result["rank"] = plate_result_rank(result, img.shape, self.known_plates)
            results.append(result)

        results.sort(key=lambda result: result["rank"], reverse=True)
        return results
