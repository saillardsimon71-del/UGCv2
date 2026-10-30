#!/usr/bin/env python3
"""Initialize a private catalog of user-approved Work media.

No network, no Git upload, no GPU. All files pinned by SHA-256.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from zipfile import ZipFile
from golden import ASSETS,GOLDEN_SHA,validate,digest

def init(work_zip:Path,approved:Path,target:Path):
    validate(work_zip,approved)
    target=target.resolve()
    if target.exists():
        raise RuntimeError('Refusing to overwrite a frozen catalog: '+str(target))
    target.parent.mkdir(parents=True,exist_ok=True)
    # Make a sibling temporary directory so no partially-populated catalog
    # becomes visible if source verification or copying fails.
    with tempfile.TemporaryDirectory(prefix='.ugcv2-freeze-',dir=target.parent) as tmp:
        stage=Path(tmp)/'catalog'
        stage.mkdir()
        with ZipFile(work_zip,'r') as archive:
            for filename,wanted_sha in ASSETS.items():
                source=archive.open(filename)
                output=stage/filename
                output.parent.mkdir(parents=True,exist_ok=True)
                with output.open('xb') as out:
                    shutil.copyfileobj(source,out,1024*1024)
                if digest(output)!=wanted_sha:
                    raise RuntimeError('Unapproved source: '+filename)
        final=stage/'approved_6p52s.mp4'
        shutil.copyfile(approved,final)
        if digest(final)!=GOLDEN_SHA:
            raise RuntimeError('Work master differs from approved MP4')
        report={
          'schema':'ugcv2.frozen-work/v1',
          'status':'LOCKED_PRODUCTION_REFERENCES_NOT_GENERATED',
          'approved_movie':{'path':'approved_6p52s.mp4','sha256':GOLDEN_SHA},
          'approved_sources':{k:{'path':k,'sha256':v} for k,v in ASSETS.items()},
          'missing_first_native_ltx':'First native LTX master not in uploaded Work zip',
          'no_model_calls':True,'no_remote_storage':True,
          'next_generated_takes_require_separate_quality_approval':True,
        }
        (stage/'catalog.json').write_text(json.dumps(report,indent=2)+'\n')
        os.rename(stage,target)
    return {'catalog':str(target),'approved_movie_sha256':GOLDEN_SHA,
            'approved_file_count':len(ASSETS)+1,'no_gpu':True}

def main():
    p=argparse.ArgumentParser(description='Freeze exact approved Work files privately')
    p.add_argument('--work-zip',type=Path,required=True)
    p.add_argument('--approved-mp4',type=Path,required=True)
    p.add_argument('--private-target',type=Path,required=True)
    a=p.parse_args()
    try:print(json.dumps(init(a.work_zip,a.approved_mp4,a.private_target),indent=2))
    except Exception as e:
        print('REFUSED: '+str(e),file=sys.stderr);return 2
    return 0
if __name__=='__main__':sys.exit(main())
