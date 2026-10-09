"""Explicit, versioned rule executor. Missing configuration never becomes zero."""
from decimal import Decimal, ROUND_HALF_UP
from services.billing import number

def configured_charges(units, profile, category, period, snapshot):
    required=['effective_from','effective_to','categories','zero_consumption','taxes','adjustments','rounding','source','eligibility_verified']
    missing=[k for k in required if snapshot.get(k) is None]
    if snapshot.get('status')!='verified' or snapshot.get('eligibility_verified') is not True: missing.append('verified tariff and eligibility conditions')
    if missing: return None,missing
    if not snapshot['effective_from']<=period<=snapshot['effective_to']: return None,['tariff effective period']
    if not snapshot['source'].get('clause'): return None,['source clause']
    config=snapshot['categories'].get(category)
    if config is None: return None,['category rules']
    rows=[]
    def add(label,amount): rows.append({'label':label,'amount':str(amount)});return amount
    if units==0:
        rule=snapshot['zero_consumption'].get(profile.get('phase'))
        if rule is None: return None,['zero consumption phase rule']
        base=add('Zero-consumption configured charge',number(rule))
    else:
        bands=config.get('bands',[])
        matches=[b for b in bands if units>number(b['lower_exclusive']) and (b['upper_inclusive'] is None or units<=number(b['upper_inclusive']))]
        if len(matches)!=1: return None,['unambiguous energy band']
        band=matches[0]
        if band.get('rate') is None or config.get('fixed_per_kw') is None: return None,['energy or fixed rate']
        mode=config.get('energy_mode')
        if mode=='all_units': energy=units*number(band['rate'])
        elif mode=='progressive':
            # Every consumed interval must be priced exactly once, starting at
            # zero. A matching top band alone does not establish valid coverage.
            ordered=sorted(bands,key=lambda b:number(b['lower_exclusive']))
            end=Decimal(0)
            for index,b in enumerate(ordered):
                start=number(b['lower_exclusive'])
                upper=number(b['upper_inclusive']) if b['upper_inclusive'] is not None else None
                if start!=end or (upper is not None and upper<=start):
                    return None,['contiguous non-overlapping progressive bands']
                if upper is None and index!=len(ordered)-1:
                    return None,['open-ended progressive band must be last']
                end=upper
            if end is not None and units>end:
                return None,['complete progressive coverage']
            energy=Decimal(0)
            for b in ordered:
                start=number(b['lower_exclusive']);end=units if b['upper_inclusive'] is None else min(units,number(b['upper_inclusive']))
                if end>start:
                    if b.get('rate') is None:return None,['energy rate']
                    energy+=(end-start)*number(b['rate'])
        else:return None,['energy calculation mode']
        if profile.get('load_kw') is None:return None,['sanctioned load']
        base=add('Energy',energy)+add('Fixed charges',number(config['fixed_per_kw'])*number(profile['load_kw']))
    for adjustment in snapshot['adjustments']:
        if adjustment.get('rate') is None:return None,['adjustment rate']
        if adjustment.get('basis')=='kwh': base+=add(adjustment['label'],units*number(adjustment['rate']))
        elif adjustment.get('basis')=='flat':base+=add(adjustment['label'],number(adjustment['rate']))
        else:return None,['adjustment basis']
    taxable=base
    for tax in snapshot['taxes']:
        if tax.get('basis')!='subtotal_before_taxes' or tax.get('percent') is None:return None,['tax basis or rate']
        base+=add(tax['label'],taxable*number(tax['percent'])/100)
    if snapshot['rounding'] not in ('0.01','1'):return None,['supported rounding quantum']
    return {'total':str(base.quantize(Decimal(snapshot['rounding']),rounding=ROUND_HALF_UP)),'line_items':rows},[]
