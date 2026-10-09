"""Synthetic fixtures only. These are NOT LESCO tariffs."""
import unittest
from decimal import Decimal
from services.tariffs import configured_charges
class TariffTests(unittest.TestCase):
    def fixture(self):
        return {'status':'verified','eligibility_verified':True,'effective_from':'2026-01','effective_to':'2026-12','source':{'clause':'SYNTHETIC TEST ONLY'},'rounding':'0.01','zero_consumption':{'Single':'5'},'taxes':[{'label':'Synthetic tax','basis':'subtotal_before_taxes','percent':'10'}],'adjustments':[],'categories':{'protected':{'energy_mode':'progressive','fixed_per_kw':'2','bands':[{'lower_exclusive':0,'upper_inclusive':100,'rate':'1'},{'lower_exclusive':100,'upper_inclusive':200,'rate':'2'}]}}}
    def test_progressive(self):
        r,missing=configured_charges(Decimal(150),{'load_kw':2},'protected','2026-09',self.fixture())
        self.assertEqual(r['total'],'224.40');self.assertEqual(missing,[])
    def test_null_not_zero(self):
        s=self.fixture();s['categories']['protected']['fixed_per_kw']=None
        r,m=configured_charges(Decimal(150),{'load_kw':2},'protected','2026-09',s)
        self.assertIsNone(r);self.assertTrue(m)
    def test_expiry(self):
        r,m=configured_charges(Decimal(150),{'load_kw':2},'protected','2027-01',self.fixture())
        self.assertIsNone(r)
    def test_verified_zero(self):
        s=self.fixture();s['zero_consumption']['Single']='0'
        r,m=configured_charges(Decimal(0),{'phase':'Single'},'protected','2026-09',s)
        self.assertEqual(r['total'],'0.00')

class ProgressiveCoverageTests(unittest.TestCase):
    fixture=TariffTests.fixture
    def test_gap_below_selected_band_cannot_undercharge(self):
        s=self.fixture();s['categories']['protected']['bands'][0]['upper_inclusive']=50
        result,missing=configured_charges(Decimal(150),{'load_kw':2},'protected','2026-09',s)
        self.assertIsNone(result);self.assertIn('contiguous non-overlapping progressive bands',missing)

    def test_overlap_below_selected_band_cannot_double_charge(self):
        s=self.fixture();s['categories']['protected']['bands']=[
            {'lower_exclusive':0,'upper_inclusive':100,'rate':'1'},
            {'lower_exclusive':50,'upper_inclusive':100,'rate':'2'},
            {'lower_exclusive':100,'upper_inclusive':200,'rate':'3'}]
        result,missing=configured_charges(Decimal(150),{'load_kw':2},'protected','2026-09',s)
        self.assertIsNone(result);self.assertTrue(missing)

    def test_unordered_complete_bands_still_work(self):
        s=self.fixture();s['categories']['protected']['bands'].reverse()
        result,missing=configured_charges(Decimal(150),{'load_kw':2},'protected','2026-09',s)
        self.assertEqual(result['total'],'224.40');self.assertEqual(missing,[])
