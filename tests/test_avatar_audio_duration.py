import base64
import wave

import pytest

from backend.app.engines.base import EngineRequest
from backend.app.engines.modal_remote import ModalEngine


@pytest.mark.parametrize("seconds", [3, 35])
def test_avatar_accepts_complete_short_or_presentation_audio(tmp_path, seconds):
    audio = tmp_path / "speech.wav"
    with wave.open(str(audio), "wb") as stream:
        stream.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        stream.writeframes(b"\0\0" * 16000 * seconds)
    reference = tmp_path / "reference.png"
    reference.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a0x8AAAAASUVORK5CYII="))
    request = EngineRequest(kind="avatar", output_dir=tmp_path / "out",
                            inputs={"audio_path": str(audio), "reference_image": str(reference)})
    payload = ModalEngine("modal_longcat_avatar")._payload(request)
    assert base64.b64decode(payload[1]) == audio.read_bytes()
