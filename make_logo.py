from PIL import Image, ImageDraw, ImageFont

img = Image.new('RGB', (512, 512), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype('/System/Library/Fonts/Times.ttc', 320)
except:
    font = ImageFont.load_default()

text = 'AD'
bbox = draw.textbbox((0, 0), text, font=font)
x = (512 - (bbox[2] - bbox[0])) // 2
y = (512 - (bbox[3] - bbox[1])) // 2 - 20

draw.text((x, y), text, fill=(70, 10, 30), font=font)
img.save('logo.png')
print('Done!')
