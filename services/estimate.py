"""February-document scenarios, never an assertion of current billing eligibility."""
from decimal import Decimal, ROUND_HALF_UP
from services.billing import number

def energy_scenarios(units, profile, evidence):
    if profile.get('disco') not in (None,'','LESCO') or profile.get('residential') is False or profile.get('arrangement') not in (None,'','non_tou'):
        return {'available':False,'reason':'This quick estimate supports domestic Non-ToU single-register meters only.'}
    load = number(profile['load_kw']) if profile.get('load_kw') not in (None,'') else None
    if load is not None and (load == 0 or load >= 5):
        return {'available':False,'reason':'The supplied Non-ToU schedule covers sanctioned load below 5 kW. This connection needs a different schedule.'}
    rates=evidence['observed_rates']; rows=[]
    def money(n):return str(n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    def add(label, category, energy, fixed_rate, explanation):
        rows.append({'label':label,'category':category,'energy_cost':money(energy),'fixed_charge':money(load*fixed_rate) if load is not None and fixed_rate is not None else None,'explanation':explanation})
    if units == 0:
        add('No energy consumed','zero',Decimal(0),None,'Minimum monthly charges may still apply; these are not included.')
    else:
        index=next((i for i,upper in enumerate([100,200,300,400,500,600,700]) if units<=upper),7)
        r=number(rates['energy_per_kwh']['unprotected'][index])
        add('Unprotected scenario','unprotected',units*r,number(rates['fixed_per_kw_month']['unprotected'][index]),f'{units} kWh × PKR {r}. No previous-slab benefit.')
        if units<=200:
            a,b=map(number,rates['energy_per_kwh']['protected'])
            amount=min(units,Decimal(100))*a+max(Decimal(0),units-100)*b
            add('If eligible for protected rates','protected',amount,number(rates['fixed_per_kw_month']['protected'][0 if units<=100 else 1]),'First 100 kWh at PKR '+str(a)+'; remaining units at PKR '+str(b)+'. Eligibility needs consumption history.')
        if units<=100:
            rate=number(rates['energy_per_kwh']['lifeline'][0 if units<=50 else 1])
            add('If eligible for lifeline rates','lifeline',units*rate,None,'All units at PKR '+str(rate)+'. Lifeline has separate eligibility conditions; low use alone does not qualify.')
    amounts=[Decimal(r['energy_cost']) for r in rows]
    return {'available':True,'kind':'document_based_scenarios','minimum':money(min(amounts)),'maximum':money(max(amounts)),'scenarios':rows,'source':'Supplied 11 February 2026 decision, Annex A-1, PDF page 14','assumptions':['Domestic Non-ToU single-register connection with sanctioned load below 5 kW.','Measured units treated as an ordinary billing month for this comparison only.'],'excluded':['Fixed/minimum charges are excluded from the headline energy amount.','Taxes, fuel/quarterly adjustments, fees and arrears are excluded.'],'notice':'February 2026 document-based comparison, not a confirmed current bill. Applicability to the selected month remains unverified.'}
