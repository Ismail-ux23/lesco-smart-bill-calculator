import json, sqlite3, uuid, os
from contextlib import contextmanager
from decimal import DecimalException
from werkzeug.exceptions import BadRequest, UnsupportedMediaType
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from services.billing import calculate_bill, appliance_plan
from services.ocr import extract
from services.estimate import energy_scenarios
from services.budget import schedule, budget_plan, local_today, daily_appliance_guide
from services.billing import number
BASE=Path(__file__).resolve().parent
app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=10*1024*1024
DB=Path(os.environ.get('LESCO_DB_PATH',str(BASE/'data'/'lesco.sqlite3')))
@contextmanager
def connection():
    db=sqlite3.connect(DB)
    db.row_factory=sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()


def request_object():
    try:
        data=request.get_json()
    except (BadRequest, UnsupportedMediaType):
        raise ValueError('Send a valid JSON object.') from None
    if not isinstance(data,dict):
        raise ValueError('Send a JSON object.')
    return data


def object_field(data,key,default=None):
    value=data.get(key,default)
    if not isinstance(value,dict):
        raise ValueError(key+' must be an object.')
    return value


def object_list(value,label):
    if not isinstance(value,list) or any(not isinstance(item,dict) for item in value):
        raise ValueError(label+' must be a list of objects.')
    return value
with connection() as db:
    db.executescript('''CREATE TABLE IF NOT EXISTS profiles(id TEXT PRIMARY KEY, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS ocr(id TEXT PRIMARY KEY, data TEXT NOT NULL, created TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS bills(id TEXT PRIMARY KEY, profile_id TEXT, input TEXT NOT NULL, result TEXT NOT NULL, confirmed_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS preferences(id TEXT PRIMARY KEY, data TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS observations(id TEXT PRIMARY KEY, data TEXT NOT NULL);''')
    db.execute('INSERT OR IGNORE INTO observations VALUES(?,?)', ('user-reported-744-kwh',json.dumps({'kind':'user_reported_bill','units':'744','total':'48837.00','billing_month':None,'source':'User reported actual bill total in conversation; bill line items not supplied','verified':False})))
def now(): return datetime.now(timezone.utc).isoformat()
@app.errorhandler(KeyError)
@app.errorhandler(TypeError)
@app.errorhandler(ValueError)
def invalid(e): return jsonify(error=str(e)),400
@app.errorhandler(DecimalException)
def numeric_range(e): return jsonify(error='Numbers exceed supported calculation precision.'),400
@app.errorhandler(413)
def large(e): return jsonify(error='Photo must be smaller than 10 MB.'),413
@app.get('/')
def home(): return render_template('index.html')
@app.get('/api/tariff')
def tariff(): return jsonify(json.loads((BASE/'data/tariff.json').read_text()))
@app.post('/api/ocr')
def ocr():
    if 'photo' not in request.files: raise ValueError('Choose a meter photo.')
    crop=json.loads(request.form['crop']) if request.form.get('crop') else None
    try: result=extract(request.files['photo'].read(),crop,int(request.form.get('precision',3)))
    except (ImportError, RuntimeError, OSError) as e: return jsonify(error='OCR unavailable. Install the documented dependencies and Tesseract, or use the labelled manual-reading fallback.',detail=str(e)),503
    oid=str(uuid.uuid4()); preview=result.pop('crop_preview')
    with connection() as db: db.execute('INSERT INTO ocr VALUES(?,?,?)',(oid,json.dumps(result),now()))
    return jsonify(id=oid,**result,crop_preview=preview)
@app.route('/api/profile',methods=['GET','POST'])
def profile():
    if request.method=='GET':
        with connection() as db: row=db.execute('SELECT data FROM profiles WHERE id=?',('default',)).fetchone()
        return jsonify(json.loads(row['data']) if row else {})
    data=request_object()
    with connection() as db: db.execute('INSERT OR REPLACE INTO profiles VALUES(?,?)',('default',json.dumps(data)))
    return jsonify(saved=True)
@app.post('/api/calculate')
def calculate():
    data=request_object(); reading=object_field(data,'reading')
    object_field(data,'profile',{})
    object_list(data.get('history',[]),'history')
    if not isinstance(data.get('period'),str): raise ValueError('period must be a YYYY-MM string.')
    if data.get('custom') is not None: object_field(data,'custom')
    if reading.get('source') not in ('manual','ocr'): raise ValueError('Select OCR or explicit manual fallback.')
    if reading['source']=='ocr':
        with connection() as db: row=db.execute('SELECT data FROM ocr WHERE id=?',(reading.get('ocr_id'),)).fetchone()
        if not row: raise ValueError('Run OCR before saving an OCR reading.')
        reading['ocr_audit']=json.loads(row['data'])
    snapshot=json.loads((BASE/'data/tariff.json').read_text())
    if data.get('custom'): snapshot={**data['custom'],'version':'user-custom-flat-v1','kind':'custom'}
    result=calculate_bill(reading,data.get('profile',{}),data.get('history',[]),data['period'],snapshot,{})
    if not data.get('custom'):
        evidence=json.loads((BASE/'data/supplied-evidence.json').read_text())
        result['energy_estimate']=energy_scenarios(number(result['measured_units']),data.get('profile',{}),evidence)
        data['estimate_evidence']=evidence
    result['calendar']=schedule()
    result['calculated_at']=now()
    reading['current_date']=reading.get('current_date') or local_today().isoformat()
    reading['current_date_source']='user' if data['reading'].get('current_date_source')=='user' else 'automatic calculation date; not verified meter-read date'
    reading['corrected_value'] = reading['current']
    reading['confirmation_timestamp'] = now()
    bid=str(uuid.uuid4())
    with connection() as db: db.execute('INSERT INTO bills VALUES(?,?,?,?,?)',(bid,'default',json.dumps({**data,'tariff_snapshot':snapshot}),json.dumps(result),now()))
    return jsonify(id=bid,**result)
@app.get('/api/bills')
def bills():
    with connection() as db: rows=db.execute('SELECT * FROM bills ORDER BY confirmed_at DESC LIMIT 100').fetchall()
    return jsonify([{'id':r['id'],'confirmed_at':r['confirmed_at'],'input':json.loads(r['input']),'result':json.loads(r['result'])} for r in rows])
@app.post('/api/plan')
def plan():
    d=request_object(); return jsonify(appliance_plan(object_list(d['items'],'items'),d.get('budget'),d.get('rate'),d.get('fixed','0')))
@app.get('/api/dashboard')
def dashboard():
    with connection() as db:
        row=db.execute('SELECT data FROM observations WHERE id=?',('user-reported-744-kwh',)).fetchone()
        pref=db.execute('SELECT data FROM preferences WHERE id=?',('bill-limit',)).fetchone()
    return jsonify(calendar=schedule(),observation=json.loads(row['data']) if row else None,budget=json.loads(pref['data']) if pref else {})
@app.post('/api/budget')
def budget():
    data=request_object()
    plan=budget_plan(data['target'],data['energy'],data.get('reserve'))
    if data.get('units') is not None:
        evidence=json.loads((BASE/'data/supplied-evidence.json').read_text())
        highest=max(number(v) for v in evidence['observed_rates']['energy_per_kwh']['unprotected'])
        plan['guide']=daily_appliance_guide(data['target'],data['units'],data.get('reserve'),plan['days_remaining'],highest,data.get('ac_watts','1500'),data.get('fridge_kwh','1.2'))
    with connection() as db:
        db.execute('INSERT OR REPLACE INTO preferences VALUES(?,?)',('bill-limit',json.dumps({'target':data['target'],'reserve':data.get('reserve')})))
    return jsonify(plan)
if __name__=='__main__': app.run(host='127.0.0.1',port=5055,debug=False)
