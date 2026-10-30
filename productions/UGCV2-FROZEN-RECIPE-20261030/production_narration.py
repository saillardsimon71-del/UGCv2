import math
import re
import unicodedata
from pathlib import Path

from studio import Refused, check_word_boundaries, command

ASR_MODEL = 'Systran/faster-whisper-small'
ASR_REVISION = '536b0662742c02347bc0e980a01041f333bce120'
TRANSLATION_MODEL = 'Helsinki-NLP/opus-mt-en-fr'
TRANSLATION_REVISION = 'dd7f6540a7a48a7f4db59e5c0b9c42c8eea67f18'


def tokens(text):
    text = unicodedata.normalize('NFKD', text.lower().replace('’', "'"))
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.findall(r'[a-z0-9]+', text)


def verify_transcript(expected, words, seconds):
    if tokens(expected) != tokens(' '.join(w['text'] for w in words)):
        raise Refused('NARRATION_TEXT_MISMATCH: missing, added or changed words, including first/last word')
    check_word_boundaries(words, 0, math.ceil(seconds * 25), 25)
    if words[0]['start_s'] < .02 or seconds - words[-1]['end_s'] < .04:
        raise Refused('NARRATION_EDGE_UNCERTAIN: insufficient audio guard around first/last word')


def transcribe(audio, cache, language=None):
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download
    path = snapshot_download(ASR_MODEL, revision=ASR_REVISION, cache_dir=str(cache))
    model = WhisperModel(path, device='cpu', compute_type='int8', cpu_threads=4)
    segments, info = model.transcribe(str(audio), language=language, word_timestamps=True,
                                     vad_filter=False, beam_size=5, condition_on_previous_text=True)
    output = []
    for seg in segments:
        words = [{'text': w.word.strip(), 'start_s': w.start, 'end_s': w.end,
                  'probability': w.probability} for w in (seg.words or []) if w.word.strip()]
        if not words or any(w['end_s'] <= w['start_s'] for w in words):
            raise Refused('ASR_ALIGNMENT_UNCERTAIN: missing/zero-length words')
        output.append({'text': seg.text.strip(), 'start_s': seg.start, 'end_s': seg.end,
                       'words': words, 'avg_logprob': seg.avg_logprob})
    if not output:
        raise Refused('ASR_EMPTY: no intelligible narration')
    return {'language': info.language, 'language_probability': info.language_probability,
            'segments': output, 'model': ASR_MODEL, 'revision': ASR_REVISION}


def translate_segments(transcript, cache):
    language = transcript['language']
    if language not in ('en', 'fr'):
        raise Refused('TRANSLATION_LANGUAGE_UNSUPPORTED: only English/French qualified for this adapter')
    segments = transcript['segments']
    if language == 'fr':
        return [{**s, 'fr_text': s['text']} for s in segments]
    import torch
    from transformers import MarianMTModel, MarianTokenizer
    tokenizer = MarianTokenizer.from_pretrained(TRANSLATION_MODEL, revision=TRANSLATION_REVISION,
                                                cache_dir=str(cache))
    model = MarianMTModel.from_pretrained(TRANSLATION_MODEL, revision=TRANSLATION_REVISION,
                                          cache_dir=str(cache), use_safetensors=False)
    result = []
    for segment in segments:
        encoded = tokenizer(segment['text'], return_tensors='pt', truncation=False)
        if encoded['input_ids'].shape[-1] > 450:
            raise Refused('TRANSLATION_BLOCK_TOO_LONG: split at sentence boundaries before synthesis')
        with torch.inference_mode():
            translated = model.generate(**encoded, num_beams=4, max_new_tokens=512)
        if translated.shape[-1] >= 512:
            raise Refused('TRANSLATION_TRUNCATED: decoder token budget reached')
        text = tokenizer.decode(translated[0], skip_special_tokens=True).strip()
        if not text:
            raise Refused('TRANSLATION_EMPTY')
        result.append({**segment, 'fr_text': text})
    return result


def duration_map(blocks, source_seconds):
    result = []
    source_position = output_position = 0.0
    for block in blocks:
        start, end, spoken = (float(block[k]) for k in ('start_s', 'end_s', 'audio_duration_s'))
        if not 0 <= source_position <= start < end <= source_seconds or spoken <= 0:
            raise Refused('NARRATION_MAPPING_INVALID')
        output_position += start - source_position
        duration = math.ceil(max(end - start, spoken + .12) * 25) / 25
        result.append({**block, 'output_start_s': output_position,
                       'output_end_s': output_position + duration, 'audio_speed': 1,
                       'picture_speed': (end - start) / duration})
        source_position = end
        output_position += duration
    if result:
        result[-1]['trailing_source_s'] = source_seconds - source_position
    return result


def extract_audio(source, target, rate=16000, channels=1):
    command(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', source, '-map', '0:a:0',
             '-ar', str(rate), '-ac', str(channels), '-c:a', 'pcm_s16le', target])
    return Path(target)
