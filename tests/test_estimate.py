import json, unittest
from decimal import Decimal
from pathlib import Path
from services.estimate import energy_scenarios
E=json.loads((Path(__file__).parents[1]/'data/supplied-evidence.json').read_text())
class EstimateTests(unittest.TestCase):
 def estimate(self,n,p=None):return energy_scenarios(Decimal(n),p or {},E)
 def test_example(self):
  r=self.estimate('744');self.assertEqual(r['minimum'],'35116.80');self.assertEqual(len(r['scenarios']),1)
 def test_unknown_category(self):
  r=self.estimate('150');self.assertEqual(len(r['scenarios']),2);self.assertEqual(r['minimum'],'1704.50');self.assertEqual(r['maximum'],'4336.50')
 def test_lifeline_alternative(self):self.assertEqual(len(self.estimate('50')['scenarios']),3)
 def test_decimal_boundary(self):self.assertEqual(self.estimate('200.1')['scenarios'][0]['energy_cost'],'6623.31')
 def test_fixed_not_assumed(self):self.assertIsNone(self.estimate('744')['scenarios'][0]['fixed_charge'])
 def test_fixed_separate(self):
  r=self.estimate('744',{'load_kw':'2'});self.assertEqual(r['minimum'],'35116.80');self.assertEqual(r['scenarios'][0]['fixed_charge'],'1350.00')
 def test_unsupported(self):self.assertFalse(self.estimate('100',{'arrangement':'solar'})['available'])
 def test_load_boundary(self):self.assertFalse(self.estimate('100',{'load_kw':'5'})['available'])
 def test_zero(self):self.assertEqual(self.estimate('0')['minimum'],'0.00')
