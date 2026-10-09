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

class InputValidationTests(unittest.TestCase):
    setUp=APITests.setUp
    tearDown=APITests.tearDown
    def test_nonobject_json(self):
        for endpoint in ['/api/calculate','/api/profile','/api/plan','/api/budget']:
            for body in [None,[],5,'text']:
                with self.subTest(endpoint=endpoint,body=body):
                    self.assertEqual(self.client.post(endpoint,json=body).status_code,400)

    def test_nested_calculation_shapes(self):
        valid={'reading':{'source':'manual','previous':'10','current':'20','confirmed':True},'period':'2026-09'}
        for key,value in [('reading',None),('reading',[]),('profile',[]),('history',{}),('history',[None]),('custom',[]),('period',202609)]:
            with self.subTest(key=key,value=value):
                self.assertEqual(self.client.post('/api/calculate',json={**valid,key:value}).status_code,400)
        self.assertEqual(self.client.get('/api/bills').json,[])

    def test_malformed_json(self):
        self.assertEqual(self.client.post('/api/calculate',data='{bad',content_type='application/json').status_code,400)

    def test_precision_overflow_is_client_error_and_not_saved(self):
        body={'reading':{'source':'manual','previous':'0','current':'1e100','confirmed':True},'period':'2026-09','custom':{'rate':'2','fixed':'0'}}
        self.assertEqual(self.client.post('/api/calculate',json=body).status_code,400)
        self.assertEqual(self.client.get('/api/bills').json,[])

    def test_invalid_crop_is_client_error(self):
        import io,json
        for crop in [[],{},[1,2],[0,0,5.5,10],[False,0,10,10],[0,0,0,10]]:
            with self.subTest(crop=crop):
                response=self.client.post('/api/ocr',data={'photo':(io.BytesIO(b'invalid'),'meter.png'),'crop':json.dumps(crop)})
                self.assertEqual(response.status_code,400)

    def test_connection_closes_after_rollback(self):
        import sqlite3
        with self.assertRaises(RuntimeError):
            with module.connection() as db:
                db.execute('INSERT INTO profiles VALUES(?,?)',('rollback','{}'))
                raise RuntimeError('simulated failure')
        with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
        with module.connection() as check:
            self.assertEqual(check.execute('SELECT COUNT(*) FROM profiles').fetchone()[0],0)
