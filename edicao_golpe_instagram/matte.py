import sys, subprocess, numpy as np, onnxruntime as ort, json
model, src, out_fg, out_a = sys.argv[1:5]
info = json.loads(subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",src]))["streams"][0]
W,H = info["width"], info["height"]
so=ort.SessionOptions(); so.intra_op_num_threads=4
sess = ort.InferenceSession(model, so)
dec = subprocess.Popen(["ffmpeg","-v","error","-i",src,"-vf","fps=30","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
frames=[]
while True:
    b=dec.stdout.read(W*H*3)
    if len(b)<W*H*3: break
    frames.append(np.frombuffer(b,np.uint8).reshape(H,W,3))
ds=np.array([0.5],np.float32)
rec=[np.zeros([1,1,1,1],np.float32)]*4
def run(f,rec):
    x=(f.astype(np.float32)/255).transpose(2,0,1)[None]
    fgr,pha,*rec = sess.run(None,{"src":x,"r1i":rec[0],"r2i":rec[1],"r3i":rec[2],"r4i":rec[3],"downsample_ratio":ds})
    return fgr,pha,rec
for f in frames[:20]: _,_,rec=run(f,rec)   # warm up recurrent state
encf = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r","30","-i","-","-c:v","ffv1",out_fg],stdin=subprocess.PIPE)
enca = subprocess.Popen(["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","gray","-s",f"{W}x{H}","-r","30","-i","-","-c:v","ffv1",out_a],stdin=subprocess.PIPE)
for f in frames:
    fgr,pha,rec=run(f,rec)
    encf.stdin.write((np.clip(fgr[0].transpose(1,2,0),0,1)*255+0.5).astype(np.uint8).tobytes())
    enca.stdin.write((np.clip(pha[0,0],0,1)*255+0.5).astype(np.uint8).tobytes())
encf.stdin.close(); enca.stdin.close(); encf.wait(); enca.wait()
print(src, len(frames), W, H, flush=True)
