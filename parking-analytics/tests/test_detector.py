import numpy as np

import detector


def test_post_process_returns_latin_plate_text():
    assert detector.post_process_ru_plate("У046ОЕ152") == "Y046OE152"
    assert detector.post_process_ru_plate("О548ТТ47") == "O548TT47"
    assert detector.post_process_ru_plate("Р221ЕМ178") == "P221EM178"
    assert detector.post_process_ru_plate("Н074ОМ178") == "H074OM178"


def test_post_process_handles_spacing_noise_and_position_confusions():
    assert detector.post_process_ru_plate(" у О46 ое 152 ") == "Y046OE152"
    assert detector.post_process_ru_plate("р22IемI78") == "P221EM178"
    assert detector.post_process_ru_plate("нO74омI78") == "H074OM178"


def test_candidate_windows_keep_plate_when_ocr_adds_noise():
    regions = [("RU", 0.8), ("Y046OE152", 0.9), ("RUS", 0.7)]

    assert "Y046OE152" in detector._candidate_texts(regions)


def test_candidate_texts_recombine_core_and_region_when_region_is_first():
    regions = [("71.", 0.98), ("K662TT", 0.99), ("RUS", 0.99)]

    assert "K662TT71" in detector._candidate_texts(regions)


def test_post_process_treats_z_as_digit_two():
    assert detector.post_process_ru_plate("C79ZHE31") == "C792HE31"


def test_recognise_plate_returns_best_processed_latin_candidate(monkeypatch):
    image = np.zeros((40, 160, 3), dtype=np.uint8)

    monkeypatch.setattr(detector, "_preprocess_plate", lambda plate_img: [("Original", plate_img)])
    monkeypatch.setattr(
        detector,
        "_paddle_recognise",
        lambda engine, img: [("noise", 0.6), ("У046ОЕ152", 0.95), ("RUS", 0.6)],
    )

    text, variants = detector.recognise_plate({"paddle_ru": object()}, image)

    assert text == "Y046OE152"
    assert list(variants) == ["Original"]


def test_snap_to_known_plate_repairs_near_ocr_misses():
    known = ["Y046OE152", "O548TT47", "P221EM178", "H074OM178"]

    assert detector.snap_to_known_plate("Y046OE19", known) == "Y046OE152"
    assert detector.snap_to_known_plate("O548TT57", known) == "O548TT47"
    assert detector.snap_to_known_plate("H074OM173", known) == "H074OM178"
    assert detector.snap_to_known_plate("M075OM178", known) == "H074OM178"


def test_plate_result_rank_prefers_lower_vehicle_plate_over_neighbor():
    known = ["P221EM178", "H074OM178"]
    neighbor = {"box": (0, 36, 62, 79), "plate_text": "P221EM178"}
    vehicle = {"box": (444, 395, 519, 448), "plate_text": "H074OM178"}

    assert detector.plate_result_rank(vehicle, (494, 563, 3), known) > detector.plate_result_rank(
        neighbor,
        (494, 563, 3),
        known,
    )


def test_ocr_input_images_adds_fixed_width_variant_for_small_crops():
    crop = np.zeros((54, 75, 3), dtype=np.uint8)

    variants = detector._ocr_input_images(crop)

    assert variants[0].shape[:2] == (108, 150)
    assert variants[1].shape[1] == 360
