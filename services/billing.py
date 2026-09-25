from decimal import Decimal, InvalidOperation
from datetime import date

RULE = {'version':'baseline-2026-09-draft','status':'pending_verification','threshold':200,'window_length':6,'anchor':'preceding_billed_months','include_current':True,'effective_from':None,'effective_to':None}

def number(value):
    try:
        n = Decimal(str(value))
        if not n.is_finite() or n < 0: raise ValueError('Readings and consumption must be finite and nonnegative.')
        return n
    except (InvalidOperation, TypeError): raise ValueError('Enter a valid nonnegative number.')

def months_before(period, count=6):
    d = date.fromisoformat(period + '-01')
    index = d.year * 12 + d.month - 1
    return [f'{(index-i)//12:04d}-{(index-i)%12+1:02d}' for i in range(1,count+1)]

def classify(profile, history, units, period):
    months = months_before(period)
    result = {'category':'unknown','eligibility_status':'unknown','reason_codes':[], 'months_evaluated':[], 'missing_fields':[], 'rule':RULE,'lifeline_status':'unknown: official conditions unverified'}
    required = ['disco','residential','arrangement','load_kw','phase','cycle_confirmed']
    result['missing_fields'] = [k for k in required if profile.get(k) is None or profile.get(k) == '']
    if profile.get('disco') not in (None,'','LESCO') or profile.get('residential') is False or profile.get('arrangement') not in (None,'','non_tou'):
        result.update(category='unsupported',eligibility_status='unsupported',reason_codes=['UNSUPPORTED_CONSUMER_OR_METER']); return result
    if profile.get('load_kw') not in (None,''): number(profile['load_kw'])
    seen = {}
    for row in history:
        month = row['month']; months_before(month)
        if month in seen: raise ValueError('Duplicate history month: ' + month)
        seen[month] = number(row['units'])
    result['months_evaluated'] = [{'month':m,'units':str(seen[m]) if m in seen else None} for m in months]
    failures = [m for m in months if m in seen and seen[m] > 200]
    if units > 200: failures.append(period)
    missing = [m for m in months if m not in seen]
    if result['missing_fields']: result['reason_codes'].append('CONSUMER_SETUP_INCOMPLETE')
    if profile.get('cycle_confirmed') is not True: result['reason_codes'].append('BILLED_CONSUMPTION_OR_CYCLE_UNVERIFIED')
    if failures:
        result['protected_test'] = 'failed'; result['reason_codes'].append('ABOVE_200_IN:' + ','.join(failures))
    elif missing:
        result['protected_test'] = 'unknown'; result['reason_codes'].append('MISSING_HISTORY:' + ','.join(missing))
    else: result['protected_test'] = 'passed'
    if not result['missing_fields'] and profile.get('cycle_confirmed') is True and (failures or not missing):
        result['category'] = 'unprotected' if failures else 'protected'
        result['eligibility_status'] = 'provisional_baseline'
    result['reason_codes'].append('OFFICIAL_LOAD_LIFELINE_AND_WINDOW_RULES_PENDING')
    return result

def calculate_bill(reading, consumer_profile, consumption_history, billing_period, tariff_snapshot, adjustment_context=None):
    if reading.get('confirmed') is not True: raise ValueError('Verify the accepted current reading first.')
    previous, current = number(reading['previous']), number(reading['current'])
    if current < previous: raise ValueError('Current reading is below previous reading. Correct it; rollover/replacement is not supported.')
    units = current - previous
    cycle = None
    if reading.get('previous_date') and reading.get('current_date'):
        cycle = (date.fromisoformat(reading['current_date']) - date.fromisoformat(reading['previous_date'])).days
        if cycle <= 0: raise ValueError('Current reading date must follow previous reading date.')
    eligibility = classify(consumer_profile, consumption_history, units, billing_period)
    result = {'measured_units':str(units),'billed_units':None,'cycle_days':cycle,'multiplier':1,'assumptions':['Standard single-register meter, multiplier 1. No normalization.'], 'eligibility':eligibility,'status':'incomplete','total':None,'line_items':[], 'missing_configuration':['Verified tariff applicability and category mapping','Lifeline and load conditions','Slab benefit, zero-consumption rule, fixed charges, taxes, adjustments and rounding'], 'tariff_version':tariff_snapshot.get('version')}
    if tariff_snapshot.get('status') == 'verified':
        from services.tariffs import configured_charges
        charges, missing = configured_charges(units, consumer_profile, eligibility['category'], billing_period, tariff_snapshot)
        if charges and eligibility['category'] in ('protected', 'unprotected'):
            result.update(charges, status='configured_estimate', billed_units=str(units), missing_configuration=[])
        else:
            result['missing_configuration'] = missing or ['Verified consumer classification']
    # Custom flat scenarios are deliberately separate from official bill estimates.
    if tariff_snapshot.get('kind') == 'custom':
        rate = number(tariff_snapshot['rate'])
        fixed = number(tariff_snapshot['fixed'])
        total = units * rate + fixed
        result.update(status='custom_scenario',total=str(total.quantize(Decimal('.01'))),line_items=[{'label':'Custom flat energy charge','amount':str(units*rate)},{'label':'Custom fixed amount','amount':str(fixed)}])
    return result

def appliance_plan(items, budget=None, rate=None, fixed='0'):
    rows=[]
    for item in items:
        watts,hours,days,qty = [number(item[k]) for k in ('watts','hours','days','quantity')]
        if hours>24 or days>31 or qty != qty.to_integral_value(): raise ValueError('Use hours ≤24, days ≤31 and whole quantities.')
        units=watts*hours*days*qty/1000
        rows.append({**item,'kwh':str(units)})
    total=sum((Decimal(r['kwh']) for r in rows),Decimal(0))
    result={'items':rows,'monthly_kwh':str(total),'estimated_cost':None,'budget_kwh':None,'note':'Nameplate estimates; actual cycling and standby use vary.'}
    if rate is not None:
        r=number(rate); f=number(fixed)
        result['estimated_cost']=str((total*r+f).quantize(Decimal('.01')))
        result['note'] += ' Cost uses your custom flat scenario, not official LESCO billing.'
        if budget is not None and r>0: result['budget_kwh']=str(max(Decimal(0),(number(budget)-f)/r).quantize(Decimal('.01')))
    return result
