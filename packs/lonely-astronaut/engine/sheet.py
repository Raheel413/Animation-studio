import sys
from PIL import Image
fs=sys.argv[2:]; out=sys.argv[1]
ims=[Image.open(f) for f in fs]
w,h=960,540; cols=2; rows=(len(ims)+1)//2
S=Image.new('RGB',(w*cols,h*rows))
for i,im in enumerate(ims):
    im=im.resize((w,h)); S.paste(im,((i%cols)*w,(i//cols)*h))
S.save(out,quality=85)
