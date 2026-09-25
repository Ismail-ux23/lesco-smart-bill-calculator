import unittest
from datetime import date
from services.budget import schedule,budget_plan
class BudgetTests(unittest.TestCase):
 def test_before(self):self.assertEqual(schedule(date(2026,9,14))['days_remaining'],1)
 def test_on_issue(self):self.assertEqual(schedule(date(2026,9,15))['days_remaining'],0)
 def test_after(self):self.assertEqual(schedule(date(2026,9,25))['next_issue_date'],'2026-10-15')
 def test_year(self):self.assertEqual(schedule(date(2026,12,31))['next_issue_date'],'2027-01-15')
 def test_unknown_reserve(self):
  r=budget_plan('40000','35116.80',today=date(2026,9,25));self.assertEqual(r['remaining'],'4883.20');self.assertEqual(r['daily_allowance'],'244.16');self.assertIsNone(r['reserve'])
 def test_over(self):self.assertEqual(budget_plan('30000','35116.80')['over_by'],'5116.80')
 def test_zero_days(self):self.assertIsNone(budget_plan(40000,35116.8,today=date(2026,9,15))['daily_allowance'])
 def test_reserve(self):self.assertEqual(budget_plan(40000,35116.8,4000)['remaining'],'883.20')

from services.budget import daily_appliance_guide
from decimal import Decimal
class GuideTests(unittest.TestCase):
 def test_shared_allowance(self):
  r=daily_appliance_guide(40000,744,None,19,'47.20')
  self.assertGreater(r['ac_minutes'],0)
  self.assertLessEqual(Decimal(r['allocated_kwh']),Decimal(r['daily_kwh'])+Decimal('.01'))
  self.assertEqual(len(r['items']),5)
 def test_essential_shortfall(self):
  r=daily_appliance_guide(1000,744,None,19,'47.20')
  self.assertEqual(r['ac_minutes'],0);self.assertGreater(Decimal(r['essential_shortfall']),0)
 def test_no_days(self):self.assertFalse(daily_appliance_guide(40000,744,None,0,'47.20')['available'])
 def test_reprice_all_units(self):
  r=daily_appliance_guide(3000,199,None,10,'47.20')
  self.assertEqual(r['daily_kwh'],'0.00')
 def test_reserve(self):
  a=daily_appliance_guide(40000,744,None,19,'47.20');b=daily_appliance_guide(40000,744,4000,19,'47.20')
  self.assertLess(b['ac_minutes'],a['ac_minutes'])
