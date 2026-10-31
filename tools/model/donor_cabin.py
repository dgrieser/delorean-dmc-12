"""Reference-led cabin details, in metres: X forward, Y left, Z up.

Studio 12 supplies the Recaro cushions, seams, carpet shelf and rear panels.
The donor's seat rails, belt mounts and cabin envelope remain the anchors.
"""
from collections import defaultdict, Counter
import numpy as np
from donor_doors import plate
from donor_hinges import cylinder


def tube(path, radius, closed=False, sides=8):
    path = np.asarray(path, float)
    tangent = np.roll(path, -1, axis=0) - np.roll(path, 1, axis=0)
    if not closed:
        tangent[0] = path[1]-path[0]
        tangent[-1] = path[-1]-path[-2]
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-12)
    # Parallel transport avoids a twist where a seal turns from pillar to roof.
    axis = np.eye(3)[np.argmin(abs(tangent[0]))]
    frames = []
    for t in tangent:
        axis = axis-t*np.dot(axis,t)
        axis /= max(np.linalg.norm(axis),1e-12)
        frames.append(axis.copy())
    u = np.array(frames); v = np.cross(tangent,u)
    angles = np.arange(sides)*2*np.pi/sides
    normal = u[:,None,:]*np.cos(angles)[None,:,None]+v[:,None,:]*np.sin(angles)[None,:,None]
    vertices = (path[:,None,:]+normal*radius).reshape(-1,3)
    faces=[]
    for i in range(len(path) if closed else len(path)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            c=((i+1)%len(path))*sides+(j+1)%sides; d=((i+1)%len(path))*sides+j
            faces.extend([(a,b,c),(a,c,d)])
    faces=np.array(faces)
    tri=vertices[faces]; norm=normal.reshape(-1,3)[faces]
    if np.sum(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*norm[:,0])<0:
        tri=tri[:,::-1];norm=norm[:,::-1]
    return tri.reshape(-1,3),norm.reshape(-1,3)


def pillow(center, size, frame=np.eye(3), power=.38, resolution=(24,64)):
    """Smooth upholstered volume; analytic normals keep the broad faces soft."""
    rings,segments=resolution
    lat=np.linspace(-np.pi/2+1e-5,np.pi/2-1e-5,rings+1)
    lon=np.arange(segments)*2*np.pi/segments
    def sp(x,p):return np.sign(x)*np.abs(x)**p
    a,b=np.meshgrid(lat,lon,indexing='ij')
    q=np.stack([sp(np.cos(a),power)*sp(np.cos(b),power),
                sp(np.cos(a),power)*sp(np.sin(b),power),sp(np.sin(a),power)],axis=-1)
    vertices=q*np.array(size)/2
    # A superellipsoid is the Lp sphere with p=2/power.
    normals=sp(q,2/power-1)/np.array(size)
    normals/=np.maximum(np.linalg.norm(normals,axis=-1,keepdims=True),1e-12)
    vertices=vertices@np.asarray(frame).T+center;normals=normals@np.asarray(frame).T
    f=[]
    for i in range(rings):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments;c=b+segments;d=a+segments
            f.extend([(a,b,c),(a,c,d)])
    f=np.array(f)
    tri=vertices.reshape(-1,3)[f];n=normals.reshape(-1,3)[f]
    if np.sum(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*n[:,0])<0:tri=tri[:,::-1];n=n[:,::-1]
    return tri.reshape(-1,3),n.reshape(-1,3)


class Parts:
    def __init__(self):self.parts=defaultdict(list)
    def add(self,name,mesh):self.parts[name].append(mesh)
    def result(self):
        return {k:(np.concatenate([p[0] for p in v]),np.concatenate([p[1] for p in v])) for k,v in self.parts.items()}
    def seam(self,path,stitch=True,closed=False,thread_path=None,radius=.0011):
        self.add('piping',tube(path,radius,closed))
        if not stitch:return
        p=np.asarray(thread_path if thread_path is not None else path)
        if closed:p=np.concatenate([p,p[:1]])
        lengths=np.linalg.norm(np.diff(p,axis=0),axis=1);distance=np.r_[0,np.cumsum(lengths)]
        for d in np.arange(.002,distance[-1]-.002,.0042):
            a=np.array([np.interp(d,distance,p[:,i]) for i in range(3)])
            b=np.array([np.interp(d+.0021,distance,p[:,i]) for i in range(3)])
            self.add('thread',cylinder(a,b,.00035,5))


def seats():
    p=Parts()
    angle=np.deg2rad(23)
    right=np.array([0,1,0]);up=np.array([-np.sin(angle),0,np.cos(angle)]);front=np.cross(right,up)
    frame=np.column_stack([front,right,up])
    def skin_depth(u,v,ru,rv,depth,power):
        """Exact positive face of the cushion's Lp surface, for sewn details."""
        power_n=2/power
        return depth*max(0,1-abs(u/ru)**power_n-abs(v/rv)**power_n)**(1/power_n)
    for side in [-1,1]:
        y=side*.40
        # Existing source rails place the cushion at 0.36 m, clear of handbrake/console.
        p.add('plastic',pillow([-.105,y,.332],[.52,.465,.095],power=.32,resolution=(12,40)))
        p.add('leather',pillow([-.07,y,.385],[.51,.345,.095],power=.35))
        for sy in [-1,1]:
            p.add('leather',pillow([-.09,y+sy*.202,.414],[.53,.105,.145],power=.56))
            # Follow the softly raised outer cushion, not a straight floating seam.
            def edge(dy):return [[x,y+sy*(.202+dy),.414+skin_depth(x+.09,dy,.265,.0525,.0725,.56)+.0004]
                                 for x in np.linspace(-.33,.15,65)]
            p.seam(edge(.035),thread_path=edge(.032))
        def base_ring(z):
            scale=(1-abs((z-.385)/.0475)**(2/.35))**(.35/2)
            return [[-.07+.255*scale*np.sign(np.cos(a))*abs(np.cos(a))**.35,
                     y+.1725*scale*np.sign(np.sin(a))*abs(np.sin(a))**.35,z]
                    for a in np.linspace(0,2*np.pi,128,endpoint=False)]
        p.seam(base_ring(.425),closed=True,thread_path=base_ring(.4265))
        base=np.array([-.355,y,.405])
        def point(d,w,h):return base+front*d+right*w+up*h
        # Rear shell, center insert and full-height rounded bolsters are separate cushions.
        p.add('leather',pillow(point(-.015,0,.24),[.105,.442,.51],frame,power=.35))
        p.add('leather',pillow(point(.038,0,.235),[.087,.294,.465],frame,power=.31))
        for sy in [-1,1]:
            p.add('leather',pillow(point(.064,sy*.186,.242),[.155,.103,.502],frame,power=.51))
            def bolster_edge(w):return [point(.064+skin_depth(w-sy*.186,h-.242,.0515,.251,.0775,.51)+.0004,w,h)
                                        for h in np.linspace(.025,.475,80)]
            p.seam(bolster_edge(sy*.205),thread_path=bolster_edge(sy*.202))
        # Recessed horizontal quilting across the insert, as in studio 12.
        for h in [.165,.208,.251,.398]:
            def seam_row(height):return [point(.038+skin_depth(w,height-.235,.147,.2325,.0435,.31)+.0003,w,height)
                                        for w in np.linspace(-.14,.14,64)]
            p.seam(seam_row(h),thread_path=seam_row(h+.0025),radius=.0006)
        # Embroidered wordmark between the middle stitch rows (studio 12).
        corners=[point(.083,w,h) for w,h in [(-.043,.220),(.043,.220),(.043,.235),(-.043,.235)]]
        vertices=np.array([corners[i] for i in [0,1,2,0,2,3]])
        p.add('badge',(vertices,np.tile(front,(6,1))))
        # Separate headrest on two visible metal posts, with piping around its end panels.
        for w in [-.088,.088]:
            p.add('metal',cylinder(point(-.01,w,.47),point(-.01,w,.57),.005,16))
            p.add('plastic',pillow(point(-.01,w,.497),[.025,.029,.012],frame,power=.4,resolution=(8,24)))
        p.add('leather',pillow(point(.002,0,.59),[.13,.32,.177],frame,power=.35))
        for sy in [-1,1]:
            t=np.linspace(0,2*np.pi,90,endpoint=False)
            def headrest_ring(w):
                scale=(1-(abs(w)/.16)**(2/.35))**(.35/2)
                return [point(.002+.065*scale*np.sign(np.cos(a))*abs(np.cos(a))**.35,w,
                              .59+.0885*scale*np.sign(np.sin(a))*abs(np.sin(a))**.35) for a in t]
            p.seam(headrest_ring(sy*.150),closed=True,thread_path=headrest_ring(sy*.148))
        # Recline wheel and rail release retain their physical location beside the cushion.
        for sy in [-1,1]:
            c=point(-.015,sy*.244,.048)
            p.add('plastic',cylinder(c-right*.012,c+right*.012,.031,32))
            for a in np.arange(24)*2*np.pi/24:
                q=c+np.array([np.cos(a)*.030,0,np.sin(a)*.030])
                p.add('plastic',cylinder(q-right*.013,q+right*.013,.002,6))
        p.add('plastic',pillow(point(-.015,side*.239,.31),[.045,.020,.073],frame,power=.38,resolution=(12,32)))
        # Belt receiver: rounded housing, recessed mouth and red release button.
        p.add('plastic',pillow([-.28,side*.124,.445],[.058,.025,.067],power=.35,resolution=(12,32)))
        p.add('metal',plate([-.28,side*.124,.478],[1,0,0],[0,1,0],.036,.018,.003,.003))
        p.add('red',plate([-.266,side*.124,.481],[1,0,0],[0,1,0],.023,.017,.004,.002))
        p.add('piping',plate([-.291,side*.124,.481],[1,0,0],[0,1,0],.010,.012,.004,.001))
        p.add('metal',tube([[.14,y-.16,.305],[.23,y-.16,.305],[.25,y,.31],[.23,y+.16,.305],[.14,y+.16,.305]],.005))
    return p.result()


def rear_cabin():
    p=Parts()
    # Carpet shelf and split removable rear bulkhead panels. All remain below glass.
    p.add('carpet',plate([-.84,0,.595],[1,0,0],[0,1,0],.30,1.31,.018,.014))
    for side in [-1,1]:
        y=side*.325
        p.add('carpet',plate([-.984,y,.733],[0,1,0],[0,0,1],.642,.265,.018,.012))
        p.add('carpet',plate([-.839,y,.606],[1,0,0],[0,1,0],.269,.622,.010,.009))
        # Binding around removable carpet panels and discreet upper fasteners.
        p.seam([[-.973,y-.31,.611],[-.973,y-.31,.85],[-.973,y+.31,.85],[-.973,y+.31,.611]],False)
        for yy in [y-.28,y+.28]:
            p.add('plastic',cylinder([-.971,yy,.837],[-.964,yy,.837],.008,16))
            p.add('metal',cylinder([-.963,yy,.837],[-.961,yy,.837],.003,12))
    p.add('carpet',plate([-.67,0,.575],[0,1,0],[0,0,1],1.29,.055,.016,.008))
    return p.result()


def sill_details():
    p=Parts()
    for side in [-1,1]:
        y=side*.738
        # Match the fixed jamb's rising inner return, not the lower exterior seam.
        cross=np.array([0,1,-side*.391]);cross/=np.linalg.norm(cross)
        normal=np.cross([1,0,0],cross);center=np.array([.035,y,.351])
        p.add('plastic',plate(center,[1,0,0],cross,.76,.088,.006,.008))
        # Five longitudinal raised ribs on the step plate, visible in studio 12.
        for dy in np.linspace(-.031,.031,5):
            p.add('plastic',tube([center+[-.361,0,0]+cross*dy+normal*.0045,
                                  center+[.361,0,0]+cross*dy+normal*.0045],.0015))
        for x in [-.322,.392]:
            c=center+np.array([x-.035,0,0])+normal*.003
            p.add('metal',cylinder(c,c+normal*.002,.0032,12))
    return p.result()


def rear_plate():
    """Studio Michigan plate, with real thickness, dark backing and fixings."""
    p=Parts();u=np.array([0,-1,0]);up=np.array([.28,0,.96]);normal=np.cross(u,up)
    center=np.array([-2.014,0,.776])
    p.add('plastic',plate(center-normal*.005,u,up,.318,.165,.009,.008))
    p.add('plate',plate(center,u,up,.3048,.1524,.002,.005))
    for x in [-.098,.098]:
        c=center+u*x+up*.052+normal*.0012
        p.add('metal',cylinder(c,c+normal*.003,.003,12))
    return p.result()


def glass_seals(source, component, radius):
    """Use welded glass boundaries; no guessed rectangles across curved apertures."""
    faces=source['loops'][source['tris']]
    faces=faces[source['comp'][faces[:,0]]==component]
    used=np.unique(faces)
    v,inv=np.unique(np.round(source['v'][used],5),axis=0,return_inverse=True)
    remap=np.empty(len(source['v']),int);remap[used]=inv;faces=remap[faces]
    edges=Counter(tuple(sorted(e)) for f in faces for e in zip(f,np.roll(f,-1)))
    adjacent=defaultdict(list)
    for (a,b),count in edges.items():
        if count==1:adjacent[a].append(b);adjacent[b].append(a)
    if not adjacent or any(len(x)!=2 for x in adjacent.values()):
        raise ValueError(f'Invalid glass seal boundary: {component}')
    pieces=[];unseen=set(adjacent)
    while unseen:
        start=min(unseen);current=start;prev=-1;ids=[]
        while True:
            ids.append(current);unseen.discard(current)
            nxt=next(i for i in adjacent[current] if i!=prev)
            if nxt==start:break
            prev,current=current,nxt
        path=v[ids]
        # Gentle corner rounding, preserving boundary position within millimetres.
        dense=[]
        for a,b,c in zip(np.roll(path,1,axis=0),path,np.roll(path,-1,axis=0)):
            aa=b+(a-b)*min(.12,.008/max(np.linalg.norm(a-b),1e-9))
            cc=b+(c-b)*min(.12,.008/max(np.linalg.norm(c-b),1e-9))
            for t in np.linspace(0,1,4):dense.append((1-t)**2*aa+2*t*(1-t)*b+t*t*cc)
        pieces.append(tube(dense,radius,True,10))
    return np.concatenate([x[0] for x in pieces]),np.concatenate([x[1] for x in pieces])


def door_pull(skin):
    """Looped strap on the armrest. Geometry follows its door, including closed pose."""
    p=Parts();side=np.sign(skin[0][:,1].mean())
    # The mounting pad touches the inner armrest at Y=0.69, Z=0.59.
    p.add('plastic',plate([.02,side*.685,.592],[1,0,0],[0,0,1],.052,.026,.008,.006))
    t=np.linspace(0,2*np.pi,65)
    # A flexible loop rather than a rigid rectangular handle. A separate pivot
    # lets the viewer keep it hanging as the door opens.
    center=np.column_stack([.02+.017*np.sin(t),side*(.674-.012*(1-np.cos(t))),.592-.100*(1-np.cos(t))])
    # A 20 mm flat leather ribbon, closed at the mounting pad.
    a=center+np.array([.009,0,0]);b=center-np.array([.009,0,0]);tri=[]
    for i in range(len(t)-1):tri.extend([[a[i],b[i],b[i+1]],[a[i],b[i+1],a[i+1]]])
    tri=np.array(tri);n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    p.add('leather',(np.concatenate([tri,tri[:,::-1]]).reshape(-1,3),np.concatenate([np.repeat(n,3,axis=0),np.repeat(-n,3,axis=0)])))
    p.seam(a,thread_path=a-[.002,0,0]);p.seam(b,thread_path=b+[.002,0,0])
    return p.result()
