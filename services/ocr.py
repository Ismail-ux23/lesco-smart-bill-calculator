import io, re

def validate_crop(crop):
    if crop is None: return None
    if not isinstance(crop,list) or len(crop)!=4: raise ValueError('Crop must contain x, y, width and height.')
    values=[]
    for value in crop:
        if isinstance(value,bool): raise ValueError('Crop coordinates must be whole numbers.')
        try:
            number=float(value)
            if not number.is_integer(): raise ValueError()
            values.append(int(number))
        except (ValueError,TypeError,OverflowError): raise ValueError('Crop coordinates must be finite whole numbers.') from None
    x,y,width,height=values
    if min(x,y)<0 or min(width,height)<=0: raise ValueError('Crop origin must be nonnegative and dimensions positive.')
    return values


def extract(image_bytes, crop=None, precision=3):
    crop=validate_crop(crop)
    if not isinstance(precision,int) or isinstance(precision,bool) or not 0 <= precision <= 6: raise ValueError('Register precision must be between 0 and 6.')
    import cv2
    import numpy as np
    import pytesseract
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = 20000000
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            if source.format not in ('JPEG','PNG','WEBP'): raise ValueError('Use a JPEG, PNG or WebP photo.')
            if source.width*source.height>Image.MAX_IMAGE_PIXELS: raise ValueError('Image exceeds 20 million pixels.')
            source.load()
            img=ImageOps.exif_transpose(source).convert('RGB')
    except Exception as exc: raise ValueError('Invalid or oversized image: ' + str(exc))
    w,h=img.size
    if crop:
        x,y,cw,ch=[int(v) for v in crop]
        if min(x,y)<0 or min(cw,ch)<=0 or x+cw>w or y+ch>h: raise ValueError('Crop must be inside the oriented image.')
    else:
        # Display-shaped contour proposal; remains untrusted until user inspection.
        gray=cv2.cvtColor(np.array(img),cv2.COLOR_RGB2GRAY)
        contours,_=cv2.findContours(cv2.Canny(gray,50,150),cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        boxes=[cv2.boundingRect(c) for c in contours]
        boxes=[b for b in boxes if 2<b[2]/max(b[3],1)<10 and b[2]*b[3]>w*h*.005 and b[2]*b[3]<w*h*.5]
        x,y,cw,ch=max(boxes,key=lambda b:b[2]*b[3]) if boxes else (0,0,w,h)
    img=img.crop((x,y,x+cw,y+ch))
    img.thumbnail((2000,1000))
    arr=cv2.cvtColor(np.array(img),cv2.COLOR_RGB2GRAY)
    arr=cv2.resize(arr,None,fx=2,fy=2)
    arr=cv2.createCLAHE(clipLimit=2.0,tileGridSize=(8,8)).apply(arr)
    variants=[arr,cv2.threshold(arr,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)[1]]
    candidates=[]; raw=[]
    for variant in variants:
        data=pytesseract.image_to_data(variant,config='--psm 6',output_type=pytesseract.Output.DICT)
        raw.append(' '.join(data['text']))
        for i,t in enumerate(data['text']):
            if re.fullmatch((r'\d{1,12}' + (r'(?:\.\d{1,'+str(precision)+r'})?' if precision else '')),t):
                candidates.append({'raw_text':t,'value':t,'confidence':float(data['conf'][i]),'register_label':'unverified'})
    buffer=io.BytesIO(); img.save(buffer,format='PNG')
    import base64
    return {'raw_text':'\n'.join(raw),'engine':'Tesseract','engine_version':str(pytesseract.get_tesseract_version()),'candidates':candidates,'crop':[x,y,cw,ch],'crop_preview':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),'warning':'Check the kWh register, decimal point and crop. Candidates may include serial numbers. Confidence is not a probability.'}
