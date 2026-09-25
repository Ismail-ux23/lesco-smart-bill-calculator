from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo
from datetime import datetime
from services.billing import number

def local_today():
    return datetime.now(ZoneInfo('Asia/Karachi')).date()

def schedule(today=None):
    today=today or local_today()
    year,month=today.year,today.month
    if today.day>15:
        month+=1
        if month==13:year,month=year+1,1
    issue=date(year,month,15)
    return {'today':today.isoformat(),'next_issue_date':issue.isoformat(),'days_remaining':(issue-today).days,'issue_day':15,'timezone':'Asia/Karachi','note':'Issuance is on the 15th as you specified. It does not establish the meter-reading cutoff.'}

def budget_plan(target, energy, reserve=None, today=None):
    target=number(target);energy=number(energy)
    if target<=0:raise ValueError('Enter a bill limit greater than zero.')
    reserve=number(reserve) if reserve not in (None,'') else None
    calendar=schedule(today)
    room=target-energy-(reserve if reserve is not None else Decimal(0))
    def money(n):return str(n.quantize(Decimal('.01'),rounding=ROUND_HALF_UP))
    return {**calendar,'target':money(target),'energy_used':money(energy),'reserve':money(reserve) if reserve is not None else None,'remaining':money(max(Decimal(0),room)),'over_by':money(max(Decimal(0),-room)),'daily_allowance':money(max(Decimal(0),room)/calendar['days_remaining']) if calendar['days_remaining'] else None,'basis':'Energy-only planning illustration' if reserve is None else 'Energy plus your chosen charge reserve','notice':'This is a spending plan, not a bill forecast or guaranteed cap. Current-cycle usage and the actual meter-reading cutoff are not established. No unit allowance is inferred from your past bill.'}

def daily_appliance_guide(target, units, reserve, days, maximum_rate, ac_watts='1500', fridge_kwh='1.2'):
    """Conservative base-energy plan: price ALL cycle units at source maximum.
    This reserves for band repricing; it is not a tax-inclusive tariff forecast.
    Appliance figures are editable example assumptions, never measured facts.
    """
    target,units,rate,watts,fridge=map(number,(target,units,maximum_rate,ac_watts,fridge_kwh))
    if rate<=0 or watts<=0:raise ValueError('Rates and AC power must be positive.')
    if days<=0:return {'available':False,'reason':'No days remain to issuance. Start a new planning window after checking the meter-reading date.'}
    held=number(reserve) if reserve not in (None,'') else Decimal(0)
    daily=max(Decimal(0),(target-held)/rate-units)/days
    essential=fridge+Decimal('.48')+Decimal('.20')
    spare=max(Decimal(0),daily-essential)
    # Round appliance run time down to whole minutes, so rounding cannot overspend.
    from decimal import ROUND_DOWN
    ac_minutes=min(Decimal(1440),(spare*1000/watts*60).to_integral_value(rounding=ROUND_DOWN))
    ac_energy=ac_minutes/60*watts/1000
    def fmt(v):return str(v.quantize(Decimal('.01'),rounding=ROUND_DOWN))
    return {'available':True,'daily_kwh':fmt(daily),'planning_rate':str(rate),'essential_shortfall':fmt(max(Decimal(0),essential-daily)),
        'allocated_kwh':fmt(essential+ac_energy),'ac_minutes':int(ac_minutes),
        'items':[{'icon':'🧊','title':'Refrigerator','text':f'Keep connected all day; budget {fridge} kWh/day for cycling. This is an example daily-energy assumption, not 24 hours of continuous compressor power.'},
                 {'icon':'🌀','title':'Fan','text':'One 60 W fan for 8 hours/day: 0.48 kWh.'},
                 {'icon':'💡','title':'Lights','text':'Four 10 W LED bulbs for 5 hours/day: 0.20 kWh.'},
                 {'icon':'❄️','title':'Air conditioner','text':f'Up to {int(ac_minutes)//60} h {int(ac_minutes)%60} min/day at an assumed average {watts} W, after the fridge, fan and lights allocation.'},
                 {'icon':'🔌','title':'Other appliances','text':'TV, iron, pump, washing machine and other loads are not included. Deduct their energy from the AC allowance or revise the plan.'}],
        'warning':'This example household exceeds the energy allowance before any AC use. Increase the target or revise appliance assumptions; do not switch off refrigeration to force a match.' if daily<essential else 'These appliances share one daily allowance; their allocations are not independent maximums.',
        'basis':f'Entire planned cycle priced at the February document’s highest residential Non-ToU energy rate, Rs. {rate}/kWh, to allow for crossing bands. Taxes and adjustments are not calculated; any reserve is your assumption.'}
