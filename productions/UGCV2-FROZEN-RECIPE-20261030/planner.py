#!/usr/bin/env python3
"""CPU-only shot planner: respect word boundaries, scene cuts, 4s proven recipe.

Input: fixed-fps source, word-level alignment and visual scene timeline.
Output: PENDING actor shot list; no generation and no implicit approval.
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from fractions import Fraction
from studio import Refused, check_word_boundaries, probe, sha256, track

def split_safe(start,end,words,fps,cap=100):
    if type(start) is not int or type(end) is not int or not 0<=start<end:raise Refused('Bad actor scene range')
    if not isinstance(words,list) or not words:raise Refused('Word timings mandatory to cut actor scenes')
    result=[];pos=start
    while pos<end:
        candidate_end=min(pos+cap,end)
        if candidate_end==end:
            result.append((pos,end));break
        # Intra-shot cuts must land between complete words, never inside a
        # phoneme. A safe pause also preserves the cadence for later lip-sync.
        gaps=[]
        word_intervals=[(float(w['start_s'])*fps,float(w['end_s'])*fps,str(w['text'])) for w in words]
        for (_,previous_end,_),(next_start,_,_) in zip(word_intervals,word_intervals[1:]):
            if next_start-previous_end<1:continue
            midpoint=round((previous_end+next_start)/2)
            if pos+max(10,cap//3) <= midpoint <= candidate_end:
                gaps.append((midpoint,next_start-previous_end))
        if word_intervals:
            previous_end=word_intervals[-1][1]
            if previous_end+1 <= candidate_end and previous_end>=pos:
                midpoint=max(pos+max(10,cap//3),round((previous_end+candidate_end)/2))
                if midpoint<=candidate_end:gaps.append((midpoint,candidate_end-previous_end))
        if not gaps:
            raise Refused(f'No word-safe cut in actor range frame {pos}..{candidate_end}. Stop rather than clip speech.')
        cut=max(gaps,key=lambda x:(x[0],x[1]))[0]
        if cut<=pos:raise Refused('Planner could not make progress')
        result.append((pos,cut));pos=cut
    return result

def create_plan(source,source_sha,word_timing,scene_map,cap=100):
    source=Path(source)
    if sha256(source)!=source_sha:raise Refused('Source SHA does not match original')
    m=probe(source);v=track(m,'video');a=track(m,'audio')
    if not v or not a:raise Refused('Source must have speech audio and video')
    fps=Fraction(v['avg_frame_rate'])
    if fps.denominator!=1 or fps!=Fraction(v['r_frame_rate']):raise Refused('Constant integer fps source required')
    fps=int(fps)
    nf=int(v.get('nb_frames') or 0)
    if nf<1:raise Refused('Source frame count unavailable')
    if not scene_map or scene_map[0]['start_frame']!=0 or scene_map[-1]['end_frame']!=nf:
        raise Refused('Scene map must cover FULL source beginning and end')
    check_word_boundaries(word_timing,0,nf,fps)
    plan=[];pending=[];end=0
    for scene in scene_map:
        start,stop=scene['start_frame'],scene['end_frame']
        if type(start) is not int or type(stop) is not int or start!=end or stop<=start:
            raise Refused('Scene map gaps, overlaps or non-frame cuts')
        mode=scene.get('mode')
        if mode=='screen':plan.append({'start_frame':start,'end_frame':stop,'mode':'screen'})
        elif mode in ('full','pip'):
            if mode=='pip':
                rect=scene.get('rectangle')
                if not isinstance(rect,list) or len(rect)!=4 or not all(type(z) is int and z>=0 for z in rect):
                    raise Refused('PiP needs exact rectangle')
                if not rect[2] or not rect[3]:raise Refused('PiP size missing')
                if rect[0]+rect[2]>v['width'] or rect[1]+rect[3]>v['height']:
                    raise Refused('PiP exceeds source picture')
            for left,right in split_safe(start,stop,word_timing,fps,cap):
                clip={'start_frame':left,'end_frame':right,'mode':mode,
                      'take':f'take_{len(pending):04d}', 'take_offset_frame':0}
                if mode=='pip':clip['rectangle']=rect
                plan.append(clip)
                pending.append({'id':clip['take'],'source_start_s':round(left/fps,3),
                     'source_end_s':round(right/fps,3),'render_duration_s':round(cap/fps,3),
                     'reference':'last_approved_native_frame_if_same_presenter',
                     'recipe':'LTX-2.5 4s > TBDub Student 4s',
                     'status':'PENDING_APPROVAL_NOT_AUTOMATICALLY_DELIVERABLE'})
        else:
            raise Refused(f'Unsupported scene type {mode!r}; title overlay cannot silently expose old presenter')
        end=stop
    return {'schema':'ugcv2.approved-timeline/v1','allow_regeneration':False,
            'source':{'path':source.name,'sha256':source_sha},
            'word_timing':word_timing,'shots':plan,'takes':{},
            'pending_takes':pending,'maximum_ltx_seconds':cap/fps,
            'input_video_frames':nf,'fps':fps,'status':'PLANNED_NO_GPU_NO_APPROVED_NEW_TAKES',
            'privacy':'Source and actor media stay outside public GitHub repository'}

def main():
    p=argparse.ArgumentParser(description='Generate blocking actor shot plan (CPU, no model)')
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--words',required=True,type=Path)
    p.add_argument('--scenes',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--maximum-frames',type=int,default=100)
    x=p.parse_args()
    try:
        if x.output.exists():raise Refused('Cannot overwrite an existing plan')
        if not 30<=x.maximum_frames<=100:raise Refused('Cannot exceed tested four-second recipe')
        words=json.loads(x.words.read_text())
        scenes=json.loads(x.scenes.read_text())
        plan=create_plan(x.source,sha256(x.source),words,scenes,x.maximum_frames)
        x.output.parent.mkdir(parents=True,exist_ok=True)
        x.output.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n')
        print(f'PLANNED: {len(plan["shots"])} source shots, {len(plan["pending_takes"])} new takes BLOCKED pending QC')
    except (Refused,ValueError,KeyError,FileNotFoundError) as e:
        print('REFUSED: '+str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
