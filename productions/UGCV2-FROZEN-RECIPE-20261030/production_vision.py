import math
from pathlib import Path

import cv2
import numpy as np

from studio import Refused


def analyze_scenes(source):
    import mediapipe as mp
    capture = cv2.VideoCapture(str(source))
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    result = []
    with mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=.35) as detector:
        for index in range(frames):
            ok, frame = capture.read()
            if not ok:
                raise Refused('SCENE_DECODE_FAILED')
            small = cv2.resize(frame, (960, 540))
            detected = detector.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)).detections or []
            if len(detected) > 1:
                mode = 'uncertain_multiple_people'
            elif not detected:
                mode = 'screen_candidate'
            else:
                box = detected[0].location_data.relative_bounding_box
                mode = 'full' if box.width * box.height > .035 else 'pip_rectangle_unqualified'
            if result and result[-1]['mode'] == mode:
                result[-1]['end_frame'] = index + 1
            else:
                result.append({'start_frame': index, 'end_frame': index + 1, 'mode': mode})
    capture.release()
    return {'scenes': result, 'frames': frames, 'detector': 'mediapipe_full_range_sparse_v2',
            'face_search_every_frame': True, 'semantics_qualified': False,
            'limitations': ['Face absence does not prove person absence, especially under titles.',
                            'No generic rectangular PiP or title matte has been qualified.',
                            'Screen/demo/interface/title candidates remain unchanged until classified.']}


def background_transform(first, second):
    gray = [cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) for frame in (first, second)]
    height, width = gray[0].shape
    mask = np.full((height, width), 255, np.uint8)
    mask[:, round(width * .26):round(width * .76)] = 0
    mask[round(height * .70):] = 0
    orb = cv2.ORB_create(nfeatures=5000)
    k1, d1 = orb.detectAndCompute(gray[0], mask)
    k2, d2 = orb.detectAndCompute(gray[1], mask)
    if d1 is None or d2 is None:
        raise Refused('BACKGROUND_UNMEASURABLE')
    matches = [m for m in cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2) if m.distance < 35]
    if len(matches) < 20:
        raise Refused('BACKGROUND_TOO_FEW_MATCHES')
    a = np.float32([k1[m.queryIdx].pt for m in matches])
    b = np.float32([k2[m.trainIdx].pt for m in matches])
    matrix, inliers = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=3)
    if matrix is None or int(inliers.sum()) < 20:
        raise Refused('BACKGROUND_UNMEASURABLE')
    return {'scale': math.hypot(matrix[0, 0], matrix[0, 1]),
            'translation_px': matrix[:, 2].tolist(), 'inliers': int(inliers.sum())}


def frame_at(path, number):
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, number)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise Refused('MEASUREMENT_FRAME_MISSING: ' + str(path))
    return frame


def take_diagnostics(before, after, previous=None):
    first, last = frame_at(before, 0), frame_at(before, 99)
    transform = background_transform(first, last)
    if abs(transform['scale'] - 1) > .02 or max(abs(v) for v in transform['translation_px']) > 12:
        raise Refused('LTX_BACKGROUND_DRIFT: ' + str(transform))
    pasted = background_transform(first, frame_at(after, 0))
    if abs(pasted['scale'] - 1) > .02:
        raise Refused('TBDUB_BACKGROUND_DRIFT')
    result = {'ltx_background': transform, 'tbdub_background': pasted,
              'phonetic_lipsync': 'UNQUALIFIED', 'face_identity': 'UNQUALIFIED',
              'naturalness': 'UNQUALIFIED', 'deliverable': False}
    if previous:
        seam = background_transform(frame_at(previous, 99), frame_at(after, 0))
        result['seam_background'] = seam
        if abs(seam['scale'] - 1) > .02:
            raise Refused('CONTINUATION_BACKGROUND_DRIFT')
    return result
