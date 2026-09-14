# -*- coding: utf-8 -*-
"""Розпізнавання на справжніх знімках Dota з ручних прогонів."""
from pathlib import Path

import pytest
from PIL import Image

import image_recognition as ir

CORPUS = Path(__file__).parent / "corpus"
ACCEPT_SHOTS = sorted(CORPUS.glob("*_accept.png"))


@pytest.mark.skipif(not ACCEPT_SHOTS, reason="корпус ще не зібрано")
@pytest.mark.parametrize("shot", ACCEPT_SHOTS, ids=lambda p: p.stem)
def test_accept_button_found_on_real_screenshots(shot):
    with Image.open(shot) as frame:
        assert ir.find_green_button(frame.convert("RGB")) is not None
