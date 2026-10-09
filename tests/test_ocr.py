import io
import unittest
from unittest.mock import patch
from PIL import Image
from services.ocr import extract


class OCRTests(unittest.TestCase):
    def image(self):
        output=io.BytesIO()
        Image.new('RGB',(200,100),'white').save(output,format='PNG')
        return output.getvalue()

    def test_crop_and_candidate_metadata(self):
        response={'text':['123.45','SERIAL','999','12.3456'],'conf':['80','60','40','20']}
        with patch('pytesseract.image_to_data',return_value=response),patch('pytesseract.get_tesseract_version',return_value='test'):
            result=extract(self.image(),[10,10,100,50],2)
        self.assertEqual(result['crop'],[10,10,100,50])
        self.assertEqual([c['value'] for c in result['candidates']],['123.45','999']*2)
        self.assertTrue(result['crop_preview'].startswith('data:image/png;base64,'))
        self.assertIn('unverified',[c['register_label'] for c in result['candidates']])

    def test_out_of_bounds_crop_rejected_before_engine(self):
        with patch('pytesseract.image_to_data') as engine:
            with self.assertRaises(ValueError):extract(self.image(),[100,0,150,20])
            engine.assert_not_called()

    def test_pixel_limit_rejected_before_image_load(self):
        with patch('PIL.Image.open') as opened:
            source=opened.return_value.__enter__.return_value
            source.format='PNG';source.width=5000;source.height=5000
            with self.assertRaises(ValueError):extract(b'fake')
            source.load.assert_not_called()
