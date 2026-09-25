import unittest
from decimal import Decimal
from services.billing import calculate_bill, classify, months_before, appliance_plan
P={'disco':'LESCO','residential':True,'arrangement':'non_tou','load_kw':'2','phase':'Single','cycle_confirmed':True}
H=[{'month':m,'units':'200'} for m in months_before('2026-09')]
class BillingTests(unittest.TestCase):
    def test_exact_window(self): self.assertEqual(months_before('2026-09'),['2026-08','2026-07','2026-06','2026-05','2026-04','2026-03'])
    def test_boundary(self): self.assertEqual(classify(P,H,Decimal(200),'2026-09')['category'],'protected')
    def test_missing(self): self.assertEqual(classify(P,H[:-1],Decimal(100),'2026-09')['category'],'unknown')
    def test_known_failure(self):
        h=[{'month':'2026-08','units':312}]
        self.assertEqual(classify(P,h,Decimal(100),'2026-09')['category'],'unprotected')
    def test_duplicate(self):
        with self.assertRaises(ValueError): classify(P,H+H,Decimal(100),'2026-09')
    def test_unsupported(self): self.assertEqual(classify({**P,'arrangement':'solar'},H,Decimal(100),'2026-09')['category'],'unsupported')
    def test_no_setup(self): self.assertEqual(classify({},H,Decimal(100),'2026-09')['category'],'unknown')
    def test_zero(self):
        r=calculate_bill({'previous':10,'current':10,'confirmed':True},P,H,'2026-09',{})
        self.assertEqual(r['measured_units'],'0');self.assertIsNone(r['total'])
    def test_negative_difference(self):
        with self.assertRaises(ValueError): calculate_bill({'previous':20,'current':10,'confirmed':True},P,H,'2026-09',{})
    def test_confirmation(self):
        with self.assertRaises(ValueError): calculate_bill({'previous':0,'current':10},P,H,'2026-09',{})
    def test_decimal(self):
        r=calculate_bill({'previous':'00010.1','current':'10.3','confirmed':True},P,H,'2026-09',{'kind':'custom','rate':'2','fixed':'0'})
        self.assertEqual(r['total'],'0.40')
    def test_nonfinite(self):
        with self.assertRaises(ValueError): calculate_bill({'previous':0,'current':'NaN','confirmed':True},P,H,'2026-09',{})
    def test_plan(self):
        r=appliance_plan([{'watts':100,'hours':10,'days':30,'quantity':2}],1000,10)
        self.assertEqual(r['monthly_kwh'],'60');self.assertEqual(r['budget_kwh'],'100.00')
if __name__=='__main__': unittest.main()
