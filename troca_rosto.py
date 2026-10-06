import sys, cv2, pickle, numpy as np, onnxruntime as ort, insightface
from insightface.app import FaceAnalysis
S = sys.argv[1]; video = sys.argv[2]; out_dir = sys.argv[3]; photos = sys.argv[4:]
app = FaceAnalysis(name='buffalo_l', root=S+'/insightface_root', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=-1, det_size=(640,640))
swapper = insightface.model_zoo.get_model(S+'/models/inswapper_128.onnx', providers=['CPUExecutionProvider'])
gfp = ort.InferenceSession(S+'/models/gfpgan_1.4.onnx', providers=['CPUExecutionProvider'])
gin = gfp.get_inputs()[0].name

# identidade da sogra: média das fotos
embs = [max(app.get(cv2.imread(p)), key=lambda f: f.det_score).normed_embedding for p in photos]
src = max(app.get(cv2.imread(photos[0])), key=lambda f: f.det_score)
m = np.mean(embs, 0); src.embedding = m / np.linalg.norm(m) * np.linalg.norm(src.embedding)

res = pickle.load(open(S+'/faces.pkl','rb'))
def ref(rng):
    e=[f['emb'] for i in rng for f in res[i]]; v=np.mean(e,0); return v/np.linalg.norm(v)
boy, girl = ref(range(0,24)), ref(range(120,150))

TPL = np.array([[0.37691676,0.46864664],[0.62285697,0.46912813],[0.50123859,0.61331904],
                [0.39308822,0.72541100],[0.61150205,0.72490465]], np.float32) * 512
def enhance(frame, kps, blend=0.8):
    M = cv2.estimateAffinePartial2D(kps.astype(np.float32), TPL, method=cv2.LMEDS)[0]
    crop = cv2.warpAffine(frame, M, (512,512), borderMode=cv2.BORDER_REPLICATE, flags=cv2.INTER_AREA)
    x = (crop[:,:,::-1].astype(np.float32)/255 - 0.5)/0.5
    y = gfp.run(None, {gin: x.transpose(2,0,1)[None]})[0][0]
    y = ((np.clip(y,-1,1)+1)/2*255).transpose(1,2,0)[:,:,::-1].astype(np.float32)
    y = blend*y + (1-blend)*crop
    mask = np.zeros((512,512), np.float32); mask[24:-24,24:-24] = 1
    mask = cv2.GaussianBlur(mask, (0,0), 12)
    IM = cv2.invertAffineTransform(M); h, w = frame.shape[:2]
    py = cv2.warpAffine(y, IM, (w,h)); pm = cv2.warpAffine(mask, IM, (w,h))[:,:,None]
    return (pm*py + (1-pm)*frame.astype(np.float32)).clip(0,255).astype(np.uint8)

class F: pass
cap = cv2.VideoCapture(video); i = 0; n = 0
while True:
    ok, fr = cap.read()
    if not ok: break
    for d in res[i]:
        sb, sg = float(d['emb']@boy), float(d['emb']@girl)
        if sb > 0.3 and sb > sg:
            t = F(); t.kps = d['kps']; t.bbox = d['bbox']
            fr = swapper.get(fr, t, src, paste_back=True)
            fr = enhance(fr, d['kps']); n += 1
    cv2.imwrite(f"{out_dir}/{i:05d}.png", fr); i += 1
print("frames", i, "swapped", n)
