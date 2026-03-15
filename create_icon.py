from PIL import Image, ImageDraw
import os, math

SIZE = 1024
img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

def rrect(draw, x1, y1, x2, y2, r, color):
    draw.rectangle([x1+r, y1, x2-r, y2], fill=color)
    draw.rectangle([x1, y1+r, x2, y2-r], fill=color)
    for cx, cy in [(x1,y1),(x2-2*r,y1),(x1,y2-2*r),(x2-2*r,y2-2*r)]:
        draw.ellipse([cx, cy, cx+2*r, cy+2*r], fill=color)

# Background
rrect(d, 0, 0, SIZE, SIZE, 180, (10, 10, 18, 255))

# Red circle
cx, cy, cr = SIZE//2, SIZE//2 - 20, 290
d.ellipse([cx-cr, cy-cr, cx+cr, cy+cr], fill=(230, 0, 0, 255))

# Inner glow
d.ellipse([cx-cr+8, cy-cr+8, cx+cr-8, cy+cr-8], outline=(255,80,80,60), width=20)

# Play triangle (white)
tw, th = 145, 168
pts = [(cx-tw//2+28, cy-th//2), (cx+tw//2+28, cy), (cx-tw//2+28, cy+th//2)]
d.polygon(pts, fill=(255, 255, 255, 255))

# Bottom text line as dots
for i, color in enumerate([(230,0,0,180),(180,180,180,120),(120,120,120,80)]):
    dx = SIZE//2 + (i-1)*28
    d.ellipse([dx-5, SIZE-140, dx+5, SIZE-130], fill=color)

img.save('icon_1024.png')
print("icon_1024.png created")
