import tempfile, unittest
from pathlib import Path
import app as module
class APITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.old=module.DB;module.DB=Path(self.temp.name)/'test.db'
        with module.connection() as db:
            db.executescript('CREATE TABLE bills(id TEXT PRIMARY KEY,profile_id TEXT,input TEXT,result TEXT,confirmed_at TEXT); CREATE TABLE profiles(id TEXT PRIMARY KEY,data TEXT); CREATE TABLE ocr(id TEXT PRIMARY KEY,data TEXT,created TEXT); CREATE TABLE preferences(id TEXT PRIMARY KEY,data TEXT);')
        self.client=module.app.test_client()
    def tearDown(self): module.DB=self.old;self.temp.cleanup()
    def test_manual_audit(self):
        r=self.client.post('/api/calculate',json={'reading':{'source':'manual','previous':'77739','current':'78483','confirmed':True},'period':'2026-09'})
        self.assertEqual(r.status_code,200); self.assertEqual(r.json['measured_units'],'744');self.assertIsNone(r.json['total']); self.assertEqual(r.json['energy_estimate']['minimum'],'35116.80')
        self.assertEqual(len(self.client.get('/api/bills').json),1)
    def test_ocr_requires_audit(self):
        r=self.client.post('/api/calculate',json={'reading':{'source':'ocr','previous':0,'current':100,'confirmed':True},'period':'2026-09'})
        self.assertEqual(r.status_code,400)
    def test_profile(self):
        self.client.post('/api/profile',json={'profile':{'disco':'LESCO'},'history':[]})
        self.assertEqual(self.client.get('/api/profile').json['profile']['disco'],'LESCO')

    def test_budget_guide_api(self):
        r=self.client.post('/api/budget',json={'target':'40000','energy':'35116.80','units':'744','ac_watts':'1500','fridge_kwh':'1.2'})
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.json['guide']['available'])
        self.assertEqual(len(r.json['guide']['items']),5)
