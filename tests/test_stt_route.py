from routes.stt import _infer_suffix


def test_infer_suffix_prefers_filename_extension():
    assert _infer_suffix("recording.webm", "audio/mp4") == ".webm"


def test_infer_suffix_uses_content_type_for_mobile_audio():
    assert _infer_suffix("recording", "audio/mp4") == ".m4a"
    assert _infer_suffix("recording", "audio/ogg") == ".ogg"
