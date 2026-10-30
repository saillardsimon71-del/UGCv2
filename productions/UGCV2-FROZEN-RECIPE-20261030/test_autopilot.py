"""CPU-only regression tests. All media is synthetic, never user/YouTube assets."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from studio import Refused,preflight,assemble
from planner import create_plan,split_safe

class ApprovedTakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.tmp.name)
        src=cls.root/'source.mp4';take=cls.root/'actor.mp4'
        def ff(c):subprocess.run(c,check=True,capture_output=True)
        ff(['ffmpeg','-y','-v','error','-f','lavfi','-i',
            'testsrc2=size=320x180:rate=25:duration=4',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=4',
            '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(src)])
        ff(['ffmpeg','-y','-v','error','-f','lavfi','-i',
            'color=c=red:size=320x180:rate=25:duration=3',
            '-c:v','libx264','-pix_fmt','yuv420p',str(take)])
        cls.src,cls.take=src,take

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def manifest(self):
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        return {'schema':'ugcv2.approved-timeline/v1','allow_regeneration':False,
                'source':{'path':'source.mp4','sha256':sha(self.src)},
                'word_timing':[{'start_s':.25,'end_s':.55,'text':'Bonjour'},
                               {'start_s':3.40,'end_s':3.76,'text':'terminé'}],
                'takes':{'approved':{'path':'actor.mp4','sha256':sha(self.take),'status':'APPROVED'}},
                'shots':[{'start_frame':0,'end_frame':25,'mode':'screen'},
                         {'start_frame':25,'end_frame':75,'mode':'full',
                          'take':'approved','take_offset_frame':0},
                         {'start_frame':75,'end_frame':100,'mode':'pip','take':'approved',
                          'take_offset_frame':50,'rectangle':[256,0,64,64]}]}

    def test_assemble_preserves_decoded_audio(self):
        man=self.manifest()
        self.assertEqual(preflight(man,self.root)['frames'],100)
        output=self.root/'result.mp4'
        report=assemble(man,self.root,output)
        self.assertEqual(report['status'],'TECHNICALLY_VALID_HUMAN_QA_REQUIRED')
        self.assertTrue(report['audio_decoded_hash_identical'])
        self.assertEqual(report['gpu_calls'],0)
        self.assertGreater(output.stat().st_size,10000)
        with self.assertRaises(Refused):assemble(man,self.root,output)

    def test_decline_unapproved_and_modified_take(self):
        m=self.manifest();m['takes']['approved']['status']='generated'
        with self.assertRaisesRegex(Refused,'not human approved'):preflight(m,self.root)
        m=self.manifest();m['takes']['approved']['sha256']='a'*64
        with self.assertRaisesRegex(Refused,'differs from approved bytes'):preflight(m,self.root)

    def test_decline_gaps_and_missing_media(self):
        m=self.manifest();m['shots'][1]['start_frame']=26
        with self.assertRaisesRegex(Refused,'gaps'):preflight(m,self.root)
        m=self.manifest();m['takes']['approved']['path']='does-not-exist.mp4'
        with self.assertRaisesRegex(Refused,'missing'):preflight(m,self.root)

    def test_decline_word_midcut(self):
        m=self.manifest();m['speech_boundary_frames']=[10]
        with self.assertRaisesRegex(Refused,'slices word'):preflight(m,self.root)

    def test_decline_traversal(self):
        m=self.manifest();m['takes']['approved']['path']='../outside.mp4'
        with self.assertRaisesRegex(Refused,'escapes'):preflight(m,self.root)

    def test_decline_unverified_fallback(self):
        m=self.manifest();m['shots'][1]['take']='new_generation'
        with self.assertRaisesRegex(Refused,'No approved take'):preflight(m,self.root)

class PlannerTests(unittest.TestCase):
    def test_split_between_complete_words(self):
        words=[{'start_s':i*.5+.02,'end_s':i*.5+.27,'text':f'w{i}'} for i in range(12)]
        ranges=split_safe(0,150,words,25,100)
        self.assertEqual(ranges[0][0],0)
        self.assertEqual(ranges[-1][1],150)
        self.assertLessEqual(max(e-s for s,e in ranges),100)
        self.assertGreater(len(ranges),1)

    def test_refuse_no_speech_gaps(self):
        with self.assertRaisesRegex(Refused,'No word-safe cut'):
            split_safe(0,125,[{'start_s':0.,'end_s':5.,'text':'unbroken'}],25,100)

    def test_plan_is_blocked_until_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
                'color=black:s=160x90:r=25:d=8',
                '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=8',
                '-c:v','libx264','-c:a','aac','-shortest',str(src)],check=True)
            words=[{'start_s':i*.5+.02,'end_s':i*.5+.25,'text':f'w{i}'} for i in range(16)]
            scenes=[{'start_frame':0,'end_frame':25,'mode':'screen'},
                    {'start_frame':25,'end_frame':175,'mode':'full'},
                    {'start_frame':175,'end_frame':200,'mode':'pip','rectangle':[100,0,60,60]}]
            plan=create_plan(src,hashlib.sha256(src.read_bytes()).hexdigest(),words,scenes)
            self.assertGreaterEqual(len(plan['pending_takes']),3)
            self.assertEqual(plan['shots'][0]['mode'],'screen')
            with self.assertRaisesRegex(Refused,'No approved take'):preflight(plan,Path(tmp))

    def test_refuse_incomplete_scene_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
                'color=black:s=160x90:r=25:d=2',
                '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2',
                '-c:v','libx264','-c:a','aac','-shortest',str(src)],check=True)
            with self.assertRaisesRegex(Refused,'FULL source'):
                create_plan(src,hashlib.sha256(src.read_bytes()).hexdigest(),
                    [{'start_s':0,'end_s':1,'text':'one'}],
                    [{'start_frame':3,'end_frame':50,'mode':'screen'}])

if __name__=='__main__':unittest.main()
