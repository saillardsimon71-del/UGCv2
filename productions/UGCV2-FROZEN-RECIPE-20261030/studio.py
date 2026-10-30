#!/usr/bin/env python3
"""UGCv2 deterministic assembler of APPROVED video takes.

No LTX, TBDub or implicit generation; only immutable files approved beforehand.
The manifest uses integer frames, so cuts are deterministic and do not
truncate words. Data and rendered videos stay outside the GitHub repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

class Refused(RuntimeError):
    pass

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def command(parts,timeout=400):
    result=subprocess.run(list(map(str,parts)),capture_output=True,text=True,timeout=timeout)
    if result.returncode: raise Refused('Command failed: '+(result.stderr or result.stdout)[-2400:])
    return result.stdout

def probe(path):
    return json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',path]))

def track(media,kind):
    return next((s for s in media['streams'] if s['codec_type']==kind),None)

def positive_int(value):
    return type(value) is int and value>0

def resolve_media(root,relative):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise Refused('Only non-empty paths relative to --media-root are permitted')
    out=(root / relative).resolve()
    if not out.is_relative_to(root.resolve()):
        raise Refused('Media path escapes --media-root')
    if not out.is_file():raise Refused('Required private media missing: '+relative)
    return out

def verified(root,item,label):
    if not isinstance(item,dict):raise Refused(label+' must be an object')
    digest=item.get('sha256')
    if not isinstance(digest,str) or len(digest)!=64 or not all(c in '0123456789abcdef' for c in digest):
        raise Refused(label+' requires a pinned SHA256')
    p=resolve_media(root,item.get('path'))
    if sha256(p)!=digest:raise Refused('REFUSED: '+label+' differs from approved bytes: '+str(p))
    return p

def check_word_boundaries(words,first,last,fps,*,enforce_duration=True):
    """Boundaries cannot begin or end in the middle of a spoken word."""
    if words is None:raise Refused('word_timing required, including for screen-only projects')
    if not isinstance(words,list) or not words:
        raise Refused('word_timing must be a nonempty list of exact timed words')
    previous=0.0
    for i,word in enumerate(words):
        if not isinstance(word,dict) or not isinstance(word.get('text'),str) or not word['text'].strip():
            raise Refused('Missing word text at '+str(i))
        start,end=word.get('start_s'),word.get('end_s')
        if not all(type(v) in (float,int) and math.isfinite(v) for v in (start,end)):
            raise Refused('Invalid word timestamps')
        if not 0 <= start < end or start < previous-1e-5:
            raise Refused('Overlapping or inverted transcript words')
        previous=end
        for boundary in (first/fps,last/fps):
            if start+0.5/fps < boundary < end-0.5/fps:
                raise Refused(f'Boundary {boundary:.3f}s slices word {word["text"]!r} at {start:.3f}–{end:.3f}s')
    if enforce_duration and words[-1]['end_s'] > last/fps + 0.5/fps:
        raise Refused('Transcript extends beyond complete source duration')

def preflight(manifest,root):
    if manifest.get('schema')!='ugcv2.approved-timeline/v1':raise Refused('Unsupported schema; no fallback')
    if manifest.get('allow_regeneration') is not False:raise Refused('allow_regeneration must be false')
    source=verified(root,manifest.get('source'),'source')
    m=probe(source)
    v=track(m,'video');a=track(m,'audio')
    if not v or not a:raise Refused('Source needs video and exact narration track')
    fps=Fraction(v.get('avg_frame_rate','0/1'))
    raw_fps=Fraction(v.get('r_frame_rate','0/1'))
    if fps!=raw_fps or fps.denominator!=1 or not 1 <= int(fps) <= 60:
        raise Refused('Source must use fixed integer fps; normalize outside this locked pipeline')
    fps=int(fps)
    expected_frames=int(v.get('nb_frames') or -1)
    if expected_frames<=0:raise Refused('Source must report exact number of frames')
    width,height=v['width'],v['height']
    slots=manifest.get('shots')
    if not isinstance(slots,list) or not slots:raise Refused('Missing shot timeline')
    begins=[x.get('start_frame') for x in slots]
    ends=[x.get('end_frame') for x in slots]
    if not all(type(x) is int for x in begins+ends):raise Refused('Use exact integer frame boundaries')
    if begins[0]!=0 or ends[-1]!=expected_frames:raise Refused('Timeline must cover full original, no arbitrary crop')
    take_table=manifest.get('takes') or {}
    if not isinstance(take_table,dict):raise Refused('takes must be a dictionary')
    takes={}
    for name,t in take_table.items():
        if t.get('status')!='APPROVED':raise Refused('Take '+name+' is not human approved; cannot assemble')
        p=verified(root,t,'approved take '+name)
        pm=probe(p);pv=track(pm,'video')
        if not pv or pv.get('width')!=width or pv.get('height')!=height:
            raise Refused('Approved take '+name+' must match source full-frame dimensions')
        if Fraction(pv.get('avg_frame_rate','0/1'))!=fps:raise Refused('Approved take has wrong fps')
        nf=int(pv.get('nb_frames') or -1)
        if nf<=0:raise Refused('Approved take frame count is unknown')
        takes[name]=(p,nf)
    actor_count=0
    for i,x in enumerate(slots):
        s,e=begins[i],ends[i]
        if s<0 or e<=s or (i>0 and s!=ends[i-1]):raise Refused('Timeline overlaps or has gaps')
        mode=x.get('mode')
        if mode not in ('screen','full','pip'):raise Refused('Unsupported mode '+repr(mode)+'. Titles require pre-approved composite')
        if mode=='screen':
            if 'take' in x:raise Refused('Screen shot must not reference an actor')
            continue
        actor_count+=1
        key=x.get('take')
        if key not in takes:raise Refused('No approved take for '+str(key))
        offset=x.get('take_offset_frame')
        if type(offset) is not int or offset<0 or offset+(e-s)>takes[key][1]:
            raise Refused('Approved take cannot cover entire actor shot; no loop/pad/retime')
        if mode=='pip':
            rect=x.get('rectangle')
            if not isinstance(rect,list) or len(rect)!=4 or not all(positive_int(z) if j>=2 else type(z) is int and z>=0 for j,z in enumerate(rect)):
                raise Refused('PiP requires exact rectangle [x,y,width,height]')
            xp,yp,w,h=rect
            if xp+w>width or yp+h>height:raise Refused('PiP rectangle extends past frame')
    check_word_boundaries(manifest.get('word_timing'),0,expected_frames,fps)
    if 'speech_boundary_frames' in manifest:
        for frame in manifest['speech_boundary_frames']:
            if type(frame) is not int or frame<0 or frame>expected_frames:raise Refused('Invalid speech boundary frame')
            check_word_boundaries(manifest['word_timing'],frame,frame,fps,enforce_duration=False)
    return {'source':source,'source_sha256':sha256(source),'fps':fps,'frames':expected_frames,
            'size':[width,height],'tracks':len(m['streams']),'approved_take_count':len(takes),
            'actor_shots':actor_count,'source_audio_codec':a.get('codec_name'),
            'paths':[takes[k][0] for k in take_table],'shot_count':len(slots)}

def assemble(manifest,root,dest):
    report=preflight(manifest,root)
    dest=Path(dest)
    if dest.exists():raise Refused('Output already exists: never overwrite approved output')
    if dest.resolve()==report['source'].resolve():raise Refused('Never overwrite source')
    takes=list(manifest.get('takes',{}))
    id_map={name:i+1 for i,name in enumerate(takes)}
    inputs=['-i',str(report['source'])]
    for path in report['paths']:inputs+=['-i',str(path)]
    nodes=[];outputs=[]
    for index,shot in enumerate(manifest['shots']):
        start,end=shot['start_frame'],shot['end_frame'];length=end-start
        base=f'[s{index}]'
        if shot['mode']=='screen':
            nodes.append(f'[0:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS{base}')
        else:
            in_id=id_map[shot['take']];t=shot['take_offset_frame']
            c=f'[take{index}]'
            nodes.append(f'[{in_id}:v]trim=start_frame={t}:end_frame={t+length},setpts=PTS-STARTPTS{c}')
            if shot['mode']=='full':
                nodes.append(f'{c}null{base}')
            else:
                source=f'[orig{index}]';cropped=f'[crop{index}]'
                x,y,w,h=shot['rectangle']
                nodes.append(f'[0:v]trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS{source}')
                nodes.append(f'{c}scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1{cropped}')
                nodes.append(f'{source}{cropped}overlay={x}:{y}:shortest=1:eof_action=pass:repeatlast=0{base}')
        outputs.append(base)
    nodes.append(''.join(outputs)+f'concat=n={len(outputs)}:v=1:a=0,format=yuv420p[outv]')
    dest.parent.mkdir(exist_ok=True,parents=True)
    try:
        command(['ffmpeg','-nostdin','-v','error','-xerror','-n',*inputs,
                 '-filter_complex',';'.join(nodes),'-map','[outv]','-map','0:a:0',
                 '-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',
                 '-c:a','copy','-movflags','+faststart',dest],timeout=1800)
        final=probe(dest);v=track(final,'video');a=track(final,'audio')
        if int(v.get('nb_frames') or -1)!=report['frames'] or (v['width'],v['height'])!=tuple(report['size']):
            raise Refused('Final MP4 changed timeline/frame dimensions')
        if not a or a['codec_name']!=report['source_audio_codec']:
            raise Refused('Audio codec has changed')
        def audiohash(file):
            return command(['ffmpeg','-v','error','-i',file,'-map','0:a:0','-f','streamhash','-hash','SHA256','-'])
        if audiohash(report['source'])!=audiohash(dest):raise Refused('Narration changed after assembly')
        command(['ffmpeg','-v','error','-xerror','-i',dest,'-f','null','-'],timeout=500)
        return {**{k:v for k,v in report.items() if k not in ('source','paths')},
                'status':'TECHNICALLY_VALID_HUMAN_QA_REQUIRED', 'output_sha256':sha256(dest),
                'audio_decoded_hash_identical':True,'gpu_calls':0,'original_video_duration_kept':True}
    except BaseException:
        dest.unlink(missing_ok=True)
        raise

def main():
    p=argparse.ArgumentParser(description='UGCv2 fail-closed approved-take assembler (no AI)')
    p.add_argument('command',choices=('check','assemble'))
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--media-root',type=Path,required=True)
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    if args.command=='assemble' and not args.output:p.error('assemble requires --output')
    try:
        manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
        report=preflight(manifest,args.media_root) if args.command=='check' else assemble(manifest,args.media_root,args.output)
        print(json.dumps({k:str(v) if isinstance(v,Path) else v for k,v in report.items() if k!='paths'},indent=2,ensure_ascii=False))
    except (Refused,ValueError,KeyError,FileNotFoundError,subprocess.TimeoutExpired) as e:
        print('REFUSED: '+str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
