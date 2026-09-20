import json, re
import numpy as np
from PIL import Image

# --- crop bounds (full-render px) ---
CROP = (140, 150, 2350, 850)  # x0,y0,x1,y1
x0,y0,x1,y1 = CROP
cw, ch = x1-x0, y1-y0

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
    mapX = round((cx-x0)/cw*100, 2)
    mapY = round((cy-y0)/ch*100, 2)
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

# crop & save image
img = Image.open('/tmp/roar_new.png').convert('RGB')
crop_img = img.crop(CROP)
crop_img.save('/app/backend/seed/assets/final-layout.png')
CW,CH = crop_img.size
print('cropped image size', CW, CH)

layout = {
 'version':'2027-01-newpdf-v1',
 'imageWidth':CW,'imageHeight':CH,
 'series':series,
 'retiredStalls':[],
 'notes':['New 2027 floor plan from ROAR_EXPO_LAYOUT_COLOR_PRESENTATION_FINAL.pdf. 148 numbered stalls. RU1-RU13 public, RU14-RU32 admin-only. BZ1/GS1 excluded per organizer.'],
 'stalls':stalls,
}
json.dump(layout, open('/app/backend/seed/final_layout.json','w'), indent=2)
print('WROTE final_layout.json with', len(stalls), 'stalls')
import collections
print(dict(collections.Counter(s['packageCode'] for s in stalls)))
print('admin-only ruby:', [s['stallNumber'] for s in stalls if s.get('adminOnly')])
