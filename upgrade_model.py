import json, math, pathlib, sys
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'guai_guai_source')
models=root/'src/main/resources/assets/guaiguai/models/block'
faces=[]
def face(mat,p,uv=None):
    faces.append((mat,p,uv or [(0,0),(1,0),(1,1),(0,1)]))
xs=[-1,-.75,-.5,-.25,0,.25,.5,.75,1]
ts=[0,.06,.14,.24,.36,.5,.64,.76,.86,.94,1]
def point(s,t,front):
    arch=math.sin(math.pi*t)**.60
    width=4.90+.20*arch-.16*math.sin(math.pi*t)**3
    x=8+s*width
    y=.36+12.25*t+.12*s*s*math.sin(math.pi*t)-.11*s*s*t
    z=5.35+4.55*t
    puff=.105+2.30*arch*(max(0,1-s*s)**.58)+.12*arch
    z+=(-1.12 if front else .84)*puff
    return (x,y,z)
for j in range(len(ts)-1):
    lo,hi=ts[j:j+2]
    for i in range(len(xs)-1):
        a,b=xs[i:i+2]
        for front,mat in [(True,'front'),(False,'back')]:
            p=[point(a,hi,front),point(b,hi,front),point(b,lo,front),point(a,lo,front)]
            uv=[((1-a)/2,1-hi),((1-b)/2,1-hi),((1-b)/2,1-lo),((1-a)/2,1-lo)] if front else [((1+a)/2,1-hi),((1+b)/2,1-hi),((1+b)/2,1-lo),((1+a)/2,1-lo)]
            if not front:p=p[::-1];uv=uv[::-1]
            face(mat,p,uv)
    for s in [-1,1]:
        p=[point(s,hi,True),point(s,hi,False),point(s,lo,False),point(s,lo,True)]
        uv=[(0,1-hi),(1,1-hi),(1,1-lo),(0,1-lo)]
        if s==-1:p=p[::-1];uv=uv[::-1]
        face('side',p,uv)
for t in [0,1]:
    for i in range(len(xs)-1):
        a,b=xs[i:i+2]
        p=[point(a,t,True),point(a,t,False),point(b,t,False),point(b,t,True)]
        if t==0:p=p[::-1]
        face('seal',p)
def strip(rows,mat,thickness):
    for i in range(len(rows)-1):
        a,b=rows[i:i+2]
        for j in range(len(a)-1):
            p=[a[j],a[j+1],b[j+1],b[j]]
            q=[(x,y+thickness[0],z+thickness[1]) for x,y,z in p]
            uv=[(j/(len(a)-1),i/(len(rows)-1)),((j+1)/(len(a)-1),i/(len(rows)-1)),((j+1)/(len(a)-1),(i+1)/(len(rows)-1)),(j/(len(a)-1),(i+1)/(len(rows)-1))]
            face(mat,p,uv);face(mat,q[::-1],uv[::-1])
            if i==0:face(mat,[p[1],p[0],q[0],q[1]])
            if i==len(rows)-2:face(mat,[p[3],p[2],q[2],q[3]])
            if j==0:face(mat,[p[0],p[3],q[3],q[0]])
            if j==len(a)-2:face(mat,[p[2],p[1],q[1],q[2]])
strip([[(8+5.08*s,13.18+.10*s*s,10.08+.03*s*s) for s in xs],[(8+4.90*s,12.56-.11*s*s,9.79) for s in xs]],'seal',(0,.13))
strip([[(8+5.18*s,0,4.43+.12*s*s) for s in xs],[(8+5.12*s,.015,4.92+.035*s*s) for s in xs],[(8+4.90*s,.27,5.35) for s in xs]],'seal',(.09,0))
def wood():
    x0,x1=5.7,10.3
    A=(0,13.3);B=(0,14.05);C=(8.0,10.70);D=(8.0,10.05)
    for x,rev in [(x0,False),(x1,True)]:
        p=[(x,y,z) for y,z in [A,B,C,D]]
        face('wood',p[::-1] if rev else p)
    for i in range(4):
        a,b=[A,B,C,D][i],[A,B,C,D][(i+1)%4]
        face('wood',[(x0,*a),(x1,*a),(x1,*b),(x0,*b)])
wood()
obj=['# GuaiGuai v0.1.3 - inflated snack pouch','mtllib pouch.mtl','o pouch']
idx=1
for mat,p,uv in faces:
    obj.append('usemtl '+mat)
    for v in p:
        assert all(0<=c<=16 for c in v),v
        obj.append('v '+' '.join(f'{c/16:.7f}' for c in v))
    for u,v in uv:obj.append(f'vt {u:.7f} {v:.7f}')
    for tri in [(0,1,2),(0,2,3)]:obj.append('f '+' '.join(f'{idx+k}/{idx+k}' for k in tri))
    idx+=4
(models/'pouch.obj').write_text('\n'.join(obj)+'\n')
(models/'pouch.mtl').write_text(''.join(f'newmtl {m}\nKa 0 0 0\nKd 1 1 1\nmap_Kd #{m}\n\n' for m in ['front','back','side','seal','wood']))
for color in ['green','yellow','red','blue','purple','black']:
    p=models/(color+'_guaiguai.json');m=json.loads(p.read_text());m.pop('elements',None)
    m.update(loader='neoforge:obj',model='guaiguai:models/block/pouch.obj',automatic_culling=False,shade_quads=True,flip_v=False,emissive_ambient=False)
    p.write_text(json.dumps(m,indent=2)+'\n')
p=root/'src/main/java/tw/zonezero/guaiguai/AuraBlock.java';s=p.read_text();s=s.replace('2.9, 0, 4, 13.1, 14, 13.5','2.8, 0, 3.4, 13.2, 14, 14.1').replace('2.9, 0, 2.5, 13.1, 14, 12','2.8, 0, 1.9, 13.2, 14, 12.6').replace('2.5, 0, 2.9, 12, 14, 13.1','1.9, 0, 2.8, 12.6, 14, 13.2').replace('4, 0, 2.9, 13.5, 14, 13.1','3.4, 0, 2.8, 14.1, 14, 13.2');p.write_text(s)
for name in ['build.gradle','src/main/resources/META-INF/neoforge.mods.toml']:
    p=root/name;p.write_text(p.read_text().replace('0.1.1','0.1.3'))
p=root/'README_zh_TW.txt';p.write_text(p.read_text()+'\n\nv0.1.3：加厚曲面袋身，保留薄封口及貼地底封口；保留六色原貼圖、創造頁面及 60 秒效果間隔。\n')
print('Generated',len(faces)*2,'triangles; all vertices within 1 block.')
