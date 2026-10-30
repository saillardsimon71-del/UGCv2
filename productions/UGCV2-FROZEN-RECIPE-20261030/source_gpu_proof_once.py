#!/usr/bin/env python3
"""One short private comparison: source motion -> FaceFusion -> background -> TBDub.

This is deliberately NOT the qualified unattended URL->MP4 pipeline.
- Exactly one FaceFusion A10G invocation and one TBDub L40S invocation.
- No LTX, no Chatterbox, no retries or new video generation.
- All media and receipts remain in the existing private Modal volume.
- A technical success never means the visual result is approved.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import shutil
import sys
import tempfile
import wave
from pathlib import Path

import cv2
import numpy as np
import modal

from production_state import PrivateVolume, RunLock, RunState, save_json
from production_workers import model_call
from source_media import replace_background, require_frames
from source_production import ROOT, verify_recipe
from studio import Refused, command, probe, sha256, track

BASE=Path(__file__).resolve().parent
PLAN_PATH=ROOT/'docs/SOURCE_GPU_PROOF_PLAN.json'
INPUT_PREFIX='source-proof-inputs/source-performance-v1'
RUN_ID='source-performance-4s-once-20261030'
OUTPUT_PREFIX='source-proof-results/'+RUN_ID
EXPECTED_PLAN_SHA='8c5ebc4b0f0f2f6befd5dfbe894c1cc1902398ba'

def check_plan():
    if sha256(PLAN_PATH)!=EXPECTED_PLAN_SHA:
        raise Refused('Proof manifest changed since user authorized bounded test')
    plan=json.loads(PLAN_PATH.read_text(encoding='utf-8'))
    recipe=verify_recipe()
    if (plan['schema']!='ugcv2.single-gpu-proof-plan/v1'
        or plan['duration_s']!=4 or plan['frames']!=100
        or plan['source_window_relative_s']!=[7.6,11.6]
        or plan['new_voice_calls']!=0 or plan['ltx_calls']!=0
        or plan['max_face_calls']!=1 or plan['max_lips_calls']!=1
        or plan['max_reserved_gpu_seconds']!=3000
        or plan['timeouts_s']!={'FaceFusion_A10G':1800,'TBDub_L40S':1200}
        or recipe['reference']['mp4_sha256']!='346b8a25aa0722094f57e51aef3d41a97e1966f7ad1d04c4517c8fbbe5b7297d'):
        raise Refused('Proof parameters are not the pre-approved 4s plan')
    if plan['avatar_sha256']!=recipe['avatar']['sha256']:
        raise Refused('Default identity mismatch')
    if recipe['motion_source']!='original_video':
        raise Refused('Image-generation approach is prohibited')
    return plan,recipe

def locate_unique_sha(root,wanted,kind):
    matches=[]
    for candidate in root.rglob('*'):
        if candidate.is_file() and sha256(candidate)==wanted:
            matches.append(candidate)
    if len(matches)!=1:
        raise Refused(f'Expected one private {kind} file matching SHA; found {len(matches)}')
    return matches[0]

def source_inputs(volume,cache,plan):
    if not volume.pull(INPUT_PREFIX,cache):
        raise Refused('Private prepared source/voice reference absent')
    source=locate_unique_sha(cache,plan['source_sha256'],'source 4s MP4')
    voice=locate_unique_sha(cache,plan['voice_sha256'],'approved French voice WAV')
    if source.suffix.lower() not in ('.mp4','.mov'):
        raise Refused('Unexpected original video container')
    require_frames(source,100)
    sv=track(probe(source),'video')
    if (sv['width'],sv['height'])!=(1920,1080):
        raise Refused('Incorrect source dimensions (expected reference 1080p)')
    with wave.open(str(voice),'rb') as w:
        dur=w.getnframes()/w.getframerate()
        if not 3.90<=dur<=4.01:
            raise Refused(f'French voice does not fill exact 4s window: {dur:.3f}s')
        if w.getnchannels() not in (1,2) or w.getsampwidth() != 2:
            raise Refused('French reference is not 16-bit PCM')
    return source,voice

def save_report(root,report):
    save_json(root/'proof-report.json',report)

def decode_b64(data,target,wanted=None):
    target.write_bytes(base64.b64decode(data,validate=True))
    if not target.is_file() or target.stat().st_size<100000:
        raise Refused('Invalid generated MP4')
    if wanted is not None and sha256(target)!=wanted:
        raise Refused('GPU output SHA256 mismatch')

def ensure_media(path,frames=100):
    require_frames(path,frames)
    command(['ffmpeg','-nostdin','-v','error','-xerror','-i',path,'-f','null','-'],timeout=180)

def photo(original,output):
    im=cv2.imread(str(original))
    if im is None or not cv2.imwrite(str(output),im,[cv2.IMWRITE_JPEG_QUALITY,98]):
        raise Refused('Approved reference photo cannot be encoded')

def normalize_pcm(voice,path):
    command(['ffmpeg','-y','-nostdin','-v','error','-i',voice,
             '-ac','1','-ar','16000','-c:a','pcm_s16le',path],timeout=80)
    with wave.open(str(path),'rb') as w:
        if w.getnchannels()!=1 or w.getframerate()!=16000:
            raise Refused('TBDub reference audio format mismatch')
        if not 3.90<=w.getnframes()/16000<=4.01:
            raise Refused('TBDub voice lost content or duration')

def compare_audio(reference,output):
    # Compare decoded PCM with no shift. AAC encoding itself is lossy.
    def pcm(file):
        with tempfile.TemporaryDirectory() as dir:
            p=Path(dir)/'track.raw'
            command(['ffmpeg','-y','-nostdin','-v','error','-i',file,'-map','0:a:0',
                     '-ac','1','-ar','48000','-c:a','pcm_s16le','-f','s16le',p])
            return np.fromfile(p,dtype='<i2').astype(np.float64)
    a,b=pcm(reference),pcm(output)
    n=min(len(a),len(b))
    if abs(len(a)-len(b))>2000:
        raise Refused('Final voice length changed')
    if n<170000:
        raise Refused('Final voice too short')
    if float(np.std(a[:n]))<100:
        raise Refused('Voice input contains insufficient sound')
    cor=float(np.corrcoef(a[:n],b[:n])[0,1])
    if not np.isfinite(cor) or cor<.97:
        raise Refused(f'Audio timing differs from approved reference: r={cor:.4f}')
    return {'correlation_zero_shift':round(cor,6),'source_pcm_samples':len(a),
            'output_pcm_samples':len(b),'no_time_stretch':True}

def make_preview(video,path):
    command(['ffmpeg','-y','-nostdin','-v','error','-ss','2.0','-i',video,
             '-frames:v','1','-q:v','2',path],timeout=90)

def run():
    plan,recipe=check_plan()
    if modal.Workspace.from_context().hydrate().name!=plan.get('workspace','lucj76861'):
        raise Refused('Wrong Modal workspace')
    vol=PrivateVolume()
    with tempfile.TemporaryDirectory(prefix='ugcv2-source-4s-') as temp:
        root=Path(temp)
        target=root/'result'
        # Pull the existing run checkpoint first, before reserving any GPU.
        existed=vol.pull(OUTPUT_PREFIX,target)
        target.mkdir(parents=True,exist_ok=True)
        source,voice=source_inputs(vol,root/'prepared',plan)
        config={'proof_plan_sha256':EXPECTED_PLAN_SHA,'source_sha256':sha256(source),
                'voice_sha256':sha256(voice),'recipe_sha256':sha256(BASE/'source_recipe.json'),
                'run_id':RUN_ID,'identity_calls':1,'tbdub_calls':1,'ltx_calls':0,'chatterbox_calls':0}
        state=RunState(target,config,max_gpu_seconds=3000,
                       checkpoint=lambda p:vol.push(OUTPUT_PREFIX,p))
        state.data.setdefault('call_limits',{'identity':1,'tbdub':1})
        state.flush()
        report={'status':'RUNNING_PRIVATE_DIAGNOSTIC','source_sha256':sha256(source),
                'french_voice_sha256':sha256(voice),'new_voice_calls':0,'ltx_calls':0,
                'human_review_required':True,'publish_allowed':False,
                'same_motion_timeline':True,'duration_seconds':4,'frames':100}
        with RunLock(target/'run.lock'):
            original=target/'original-source-4s.mp4'
            if not state.cached('input',{'source':sha256(source),'voice':sha256(voice)}):
                shutil.copyfile(source,original)
                shutil.copyfile(voice,target/'approved-voice-4s.wav')
                state.complete('input',{'source':sha256(source),'voice':sha256(voice)},
                               [original,target/'approved-voice-4s.wav'])
            else:
                if sha256(original)!=sha256(source):raise Refused('Original changed')

            avatar=target/'avatar-reference.jpg'
            if not state.cached('avatar',recipe['avatar']):
                photo(ROOT/recipe['avatar']['path'],avatar)
                state.complete('avatar',recipe['avatar'],[avatar])
            identity=target/'identity-facefusion-4s.mp4'
            face_receipt=target/'facefusion-receipt.json'
            identity_key={'original':sha256(original),'portrait':sha256(avatar),'worker':recipe['workers']['deploy/modal_fr60_faceswap_selected.py']}
            if not state.cached('identity',identity_key):
                from deploy import modal_fr60_faceswap_selected as face
                result=model_call(state,'proof/identity/1',face,face.face_swap_explicit_one,
                        (base64.b64encode(original.read_bytes()).decode(),
                         base64.b64encode(avatar.read_bytes()).decode()),1800)
                decode_b64(result['video_base64'],identity,result['metadata']['sha256'])
                ensure_media(identity)
                save_json(face_receipt,{k:v for k,v in result['metadata'].items() if k!='log_tail'})
                state.data['calls']['proof/identity/1']['status']='SAVED'
                state.complete('identity',identity_key,[identity,face_receipt],
                               {'sha256':sha256(identity),'status':'FACE_CHANGED_GPU_TECHNICAL'})
                print('FACEFUSION_PASS_COMPLETE',flush=True)

            background=target/'new-background-4s.mp4'
            matte=target/'person-matte-4s.mkv'
            back_receipt=target/'background-receipt.json'
            back_key={'identity':sha256(identity),'background_sha256':recipe['background']['sha256']}
            if not state.cached('background',back_key):
                data=replace_background(identity,ROOT/recipe['background']['path'],background,matte)
                save_json(back_receipt,data)
                ensure_media(background)
                state.complete('background',back_key,[background,matte,back_receipt],data)
                print('BACKGROUND_PASS_COMPLETE',flush=True)

            audio16=target/'speech16k-4s.wav'
            if not state.cached('speech',{'voice':sha256(voice)}):
                normalize_pcm(voice,audio16)
                state.complete('speech',{'voice':sha256(voice)},[audio16])
            from deploy import modal_tbdub_fr_worker as lips
            preflight=target/'tbdub-preflight.json'
            preview=target/'preflight-face.mp4'
            pf_key={'video':sha256(background),'voice':sha256(audio16)}
            if not state.cached('face_preflight',pf_key):
                with lips.app.run(name='ugcv2-source-proof-cpu-preflight',environment_name='main'):
                    x=lips.preflight.remote(base64.b64encode(background.read_bytes()).decode(),
                                            base64.b64encode(audio16.read_bytes()).decode())
                if x.get('status')!='CPU_FACE_PREFLIGHT_PASSED':
                    raise Refused('TBDUB_CPU_FACE_PREFLIGHT_REJECTED')
                decode_b64(x.pop('preview_base64'),preview)
                save_json(preflight,x)
                state.complete('face_preflight',pf_key,[preflight,preview])
                print('FACE_PREFLIGHT_PASSED',flush=True)

            dubbed=target/'tbdub-4s.mp4'
            lip_receipt=target/'tbdub-receipt.json'
            dub_key={'video':sha256(background),'voice':sha256(audio16),
                     'worker':recipe['workers']['deploy/modal_tbdub_fr_worker.py']}
            if not state.cached('lips',dub_key):
                result=model_call(state,'proof/tbdub/1',lips,lips.render_student_four_seconds,
                           (base64.b64encode(background.read_bytes()).decode(),
                            base64.b64encode(audio16.read_bytes()).decode()),1200)
                decode_b64(result['video_base64'],dubbed,result['metadata']['video_sha256'])
                ensure_media(dubbed)
                save_json(lip_receipt,{k:v for k,v in result['metadata'].items() if 'base64' not in k})
                state.data['calls']['proof/tbdub/1']['status']='SAVED'
                state.complete('lips',dub_key,[dubbed,lip_receipt],
                               {'status':'LIPS_SYNC_TECHNICAL_NOT_PERCEPTUALLY_APPROVED','sha256':sha256(dubbed)})
                print('TBDUB_PASS_COMPLETE',flush=True)

            final=target/'UGCv2_SOURCE_PERFORMANCE_4s_PRIVATE_DIAGNOSTIC.mp4'
            mux_key={'dub':sha256(dubbed),'audio':sha256(voice)}
            if not state.cached('mux',mux_key):
                command(['ffmpeg','-y','-nostdin','-v','error','-xerror','-i',dubbed,
                         '-i',voice,'-map','0:v:0','-map','1:a:0','-c:v','libx264',
                         '-crf','18','-preset','fast','-pix_fmt','yuv420p','-r','25',
                         '-frames:v','100','-c:a','aac','-b:a','192k','-ar','48000',
                         '-movflags','+faststart',final],timeout=420)
                ensure_media(final)
                audio_check=compare_audio(voice,final)
                save_json(target/'mux-receipt.json',audio_check)
                state.complete('mux',mux_key,[final,target/'mux-receipt.json'],audio_check)

            image_files=[]
            for tag,item in [('before',original),('identity',identity),
                             ('new-background',background),('after-tbdub',final)]:
                p=target/f'review-{tag}.jpg'
                if not p.is_file():make_preview(item,p)
                image_files.append(p)
            report.update(status='DIAGNOSTIC_PRIVATE_UNVALIDATED',
                 video_sha256=sha256(final),video_frames=100,
                 media_prefix=OUTPUT_PREFIX,
                 facefusion_calls=1,tbdub_calls=1,
                 gpu_reservations_seconds=sum(v['reserved_seconds'] for v in state.data['calls'].values()),
                 audio=compare_audio(voice,final),
                 source_motion_perceptual_review='REQUIRED',
                 identity_complete_perceptual_review='REQUIRED',
                 background_matte_perceptual_review='REQUIRED',
                 lipsync_perceptual_review='REQUIRED',
                 final_mp4_private_name=final.name)
            save_report(target,report)
            vol.push(OUTPUT_PREFIX,target)
            print(json.dumps(report,indent=2),flush=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('action',choices=('run',))
    a=ap.parse_args()
    try:run()
    except BaseException as e:
        # Human-facing error appears in Actions; previous good GPU artifacts
        # and reservations remain in private Modal even on a later failure.
        print('PROOF_BLOCKED_OR_FAILED: '+type(e).__name__+': '+str(e),file=sys.stderr,flush=True)
        return 2
    return 0

if __name__=='__main__':sys.exit(main())
