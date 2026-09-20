import json, re
import numpy as np
from PIL import Image

# --- crop bounds (full-render px) ---
CROP = (140, 150, 2350, 850)  # x0,y0,x1,y1
x0,y0,x1,y1 = CROP
cw, ch = x1-x0, y1-y0

# --- beautified composite geometry ---
BORDER   = 96                       # hedge/greenery border thickness
STAGE_W  = 400                      # left inauguration-stage strip
WALKWAY  = 78
HALL_PAD = 40
HALL_L   = BORDER + 26 + STAGE_W + WALKWAY   # hall panel left edge
GX       = HALL_L + HALL_PAD                 # stall grid left inside the hall
GY       = BORDER + 70                        # stall grid top
BAND_GAP = 52
BAND_H   = 280
BAND_TOP = GY + ch + BAND_GAP
HALL_T   = GY - HALL_PAD
HALL_R   = GX + cw + HALL_PAD
HALL_B   = BAND_TOP + BAND_H + HALL_PAD
FINAL_W  = HALL_R + 26 + BORDER
FINAL_H  = HALL_B + 26 + BORDER

items = json.load(open('/tmp/ocr_items.json'))
pat = re.compile(r'^(T|D|G|S|PP|P|PR|R|RU|B)(\d+)$')
cent = {}
merged_ru = None
for i in items:
    t = i['text']
    if pat.match(t) and t not in ('BZ1','GS1'):
        cent[t] = (i['cx'], i['cy'])
    if t == 'RU12RU13':
        merged_ru = (i['cx'], i['cy'])

# --- synthesize missing labels ---
# T1/T2 top-title boxes: OCR read them from the rate table instead of the
# top-left grey boxes; override with the detected dark-grey box centroids.
cent['T1'] = (289, 196)
cent['T2'] = (245, 387)
# R63 = midpoint R62,R64
r62, r64 = cent['R62'], cent['R64']
cent['R63'] = ((r62[0]+r64[0])/2, (r62[1]+r64[1])/2)
# RU12, RU13: row-E RU run RU1..RU11 -> spacing
ru_row = [cent[f'RU{n}'] for n in range(1,12)]
ru_row_sorted = sorted(ru_row, key=lambda p:p[0])
dxs = [ru_row_sorted[k+1][0]-ru_row_sorted[k][0] for k in range(len(ru_row_sorted)-1)]
dx = sum(dxs)/len(dxs)
ru11 = cent['RU11']
cent['RU12'] = (ru11[0]+dx, ru11[1])
cent['RU13'] = (ru11[0]+2*dx, ru11[1])

# --- package + size mapping ---
def pkg_for(label):
    m = re.match(r'^([A-Z]+)(\d+)$', label); pre=m.group(1); n=int(m.group(2))
    if pre=='T': return 'title','3m × 8m' if n==1 else '4m × 6m'
    if pre=='D': return 'diamond','3m × 6m'
    if pre=='G': return 'gold','3m × 5m'
    if pre=='S': return 'silver','3m × 4m'
    if pre=='B': return 'bronze','3m × 5m'
    if pre=='PP': return ('premium-corner','3m × 4m') if n<=5 else ('premium-corner-15','3m × 5m')
    if pre=='P': return 'premium','3m × 4m'
    if pre=='PR': return ('premium-ruby','3m × 3m') if n<=4 else ('premium-ruby-53','3m × 3m')
    if pre=='R': return 'regular','3m × 3m'
    if pre=='RU': return 'ruby','3m × 3m'
    raise ValueError(label)

expected = ['T1','T2','D1','D2'] + [f'G{i}' for i in range(1,5)] + [f'S{i}' for i in range(1,5)] \
    + [f'PP{i}' for i in range(1,8)] + [f'P{i}' for i in range(1,20)] + [f'PR{i}' for i in range(1,9)] \
    + [f'R{i}' for i in range(1,67)] + [f'RU{i}' for i in range(1,33)] + [f'B{i}' for i in range(1,5)]
assert set(expected)==set(cent), set(expected)^set(cent)

stalls=[]
for label in expected:
    cx,cy = cent[label]
    mapX = round((GX + (cx-x0))/FINAL_W*100, 2)
    mapY = round((GY + (cy-y0))/FINAL_H*100, 2)
    code,size = pkg_for(label)
    rec = {'stallNumber':label,'packageCode':code,'size':size,'mapX':mapX,'mapY':mapY}
    # per-stall admin-only: RU14..RU32 admin only; RU1..RU13 public
    if code=='ruby':
        n=int(label[2:])
        if n>=14: rec['adminOnly']=True
    stalls.append(rec)

# sanity: mapX/mapY within 0..100
bad=[s for s in stalls if not(0<=s['mapX']<=100 and 0<=s['mapY']<=100)]
print('out-of-range:',bad)

series=[
 {'prefix':'T','packageCode':'title','separator':''},
 {'prefix':'D','packageCode':'diamond','separator':''},
 {'prefix':'G','packageCode':'gold','separator':''},
 {'prefix':'S','packageCode':'silver','separator':''},
 {'prefix':'PP','packageCode':'premium-corner','separator':''},
 {'prefix':'P','packageCode':'premium','separator':''},
 {'prefix':'PR','packageCode':'premium-ruby','separator':''},
 {'prefix':'R','packageCode':'regular','separator':''},
 {'prefix':'RU','packageCode':'ruby','separator':''},
 {'prefix':'B','packageCode':'bronze','separator':''},
]

# --- beautified composite render (grid & pin coords unchanged) ---
from PIL import ImageDraw, ImageFont, ImageFilter

ASSETS = '/app/backend/seed/assets'
img = Image.open('/tmp/roar_new.png').convert('RGB')
crop_img = img.crop(CROP)

def _font(sz):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', sz)
    except Exception: return ImageFont.load_default()

def cover(im, w, h):
    w, h = int(w), int(h)
    iw, ih = im.size
    s = max(w/iw, h/ih)
    im2 = im.resize((max(1,int(iw*s)), max(1,int(ih*s))), Image.LANCZOS)
    l = (im2.width - w)//2; t = (im2.height - h)//2
    return im2.crop((l, t, l+w, t+h))

def paste_rounded(base, im, box, radius, outline=None, ow=6):
    bx0, by0, bx1, by1 = [int(v) for v in box]
    w, h = bx1-bx0, by1-by0
    tile = cover(im, w, h)
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w-1, h-1], radius=radius, fill=255)
    base.paste(tile, (bx0, by0), mask)
    if outline:
        ImageDraw.Draw(base).rounded_rectangle([bx0, by0, bx1, by1], radius=radius, outline=outline, width=ow)

def pill(dr, cx, cy, text, fill, font):
    tb = dr.textbbox((0,0), text, font=font); tw, th = tb[2]-tb[0], tb[3]-tb[1]
    px, py = 40, 20
    x0, y0, x1, y1 = cx-tw/2-px, cy-th/2-py, cx+tw/2+px, cy+th/2+py
    dr.rounded_rectangle([x0, y0, x1, y1], radius=(y1-y0)/2, fill=fill)
    dr.text((cx-tw/2-tb[0], cy-th/2-tb[1]), text, fill='#ffffff', font=font)

# 1) ground + greenery border
canvas = Image.new('RGB', (FINAL_W, FINAL_H), '#e9dfc7')
hedge = Image.open(f'{ASSETS}/dec_hedge.jpg').convert('RGB')
canvas.paste(cover(hedge, FINAL_W, FINAL_H), (0, 0))                 # full hedge
d = ImageDraw.Draw(canvas)
d.rounded_rectangle([BORDER, BORDER, FINAL_W-BORDER, FINAL_H-BORDER],  # inner ground
                    radius=40, fill='#ece3cf')

# 2) soft shadow + hall panel (white, holds the stall grid + zones)
shadow = Image.new('RGBA', (FINAL_W, FINAL_H), (0,0,0,0))
ImageDraw.Draw(shadow).rounded_rectangle([HALL_L+10, HALL_T+14, HALL_R+10, HALL_B+16], radius=46, fill=(60,45,20,90))
shadow = shadow.filter(ImageFilter.GaussianBlur(14))
canvas.paste(shadow, (0,0), shadow)
d.rounded_rectangle([HALL_L, HALL_T, HALL_R, HALL_B], radius=46, fill='#ffffff', outline='#c9b892', width=5)

# 3) the stall grid (unchanged pixels, pins map onto this)
canvas.paste(crop_img, (GX, GY))

# 4) inauguration stage on the left (outside the hall) + walkway
stage_h = int(ch*0.86)
stage_box = (BORDER+26, HALL_T + (HALL_B-HALL_T-stage_h)//2, BORDER+26+STAGE_W, HALL_T + (HALL_B-HALL_T-stage_h)//2 + stage_h)
# walkway strip between stage and hall
d.rounded_rectangle([stage_box[2]+14, stage_box[1]+stage_h*0.30, HALL_L+4, stage_box[1]+stage_h*0.48],
                    radius=10, fill='#d9cba6')
paste_rounded(canvas, Image.open(f'{ASSETS}/dec_stage.jpg').convert('RGB'), stage_box, 26, outline='#8e6d1c', ow=5)
pill(d, (stage_box[0]+stage_box[2])/2, stage_box[3]-46, 'STAGE', '#b91c1c', _font(42))

# 5) play zone (left) + food court (right) inside the hall bottom band
gap = 40
mid = GX + cw/2
play_box = (GX, BAND_TOP, mid-gap/2, BAND_TOP+BAND_H)
food_box = (mid+gap/2, BAND_TOP, GX+cw, BAND_TOP+BAND_H)
paste_rounded(canvas, Image.open(f'{ASSETS}/dec_playzone.jpg').convert('RGB'), play_box, 30, outline='#7c4bd0', ow=5)
paste_rounded(canvas, Image.open(f'{ASSETS}/dec_foodcourt.jpg').convert('RGB'), food_box, 30, outline='#d97a24', ow=5)
pill(d, (play_box[0]+play_box[2])/2, (play_box[1]+play_box[3])/2, 'PLAY ZONE', '#6d28d9', _font(46))
pill(d, (food_box[0]+food_box[2])/2, (food_box[1]+food_box[3])/2, 'FOOD COURT', '#ea6a12', _font(46))

# 6) entry / exit hints on the hall's left edge
ef = _font(30)
d.text((HALL_L+18, GY-6), 'ENTRY', fill='#c0392b', font=ef)
d.text((HALL_L+18, BAND_TOP-42), 'EXIT', fill='#c0392b', font=ef)

canvas.save(f'{ASSETS}/final-layout.png')
CW, CH = canvas.size
print('final image size', CW, CH)

# informational zones (not bookable)
def _rec(label, box):
    zx0,zy0,zx1,zy1 = box
    return {'label':label,'x':round((zx0+zx1)/2/CW*100,2),'y':round((zy0+zy1)/2/CH*100,2),
            'w':round((zx1-zx0)/CW*100,2),'h':round((zy1-zy0)/CH*100,2)}
zone_records = [_rec('STAGE',stage_box), _rec('PLAY ZONE',play_box), _rec('FOOD COURT',food_box)]

layout = {
 'version':'2027-01-newpdf-v4-beauty',
 'imageWidth':CW,'imageHeight':CH,
 'series':series,
 'retiredStalls':[],
 'zones':zone_records,
 'notes':['Beautified 2027 floor plan (AI-decorated). 148 numbered stalls, grid & pin mapping unchanged. RU1-RU13 public, RU14-RU32 admin-only. BZ1/GS1 excluded. Greenery border, illustrated STAGE on the left, PLAY ZONE + FOOD COURT illustrations in the hall.'],
 'stalls':stalls,
}
json.dump(layout, open('/app/backend/seed/final_layout.json','w'), indent=2)
print('WROTE final_layout.json with', len(stalls), 'stalls')
import collections
print(dict(collections.Counter(s['packageCode'] for s in stalls)))
print('admin-only ruby:', [s['stallNumber'] for s in stalls if s.get('adminOnly')])
