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


def pillow(center, size, frame=np.eye(3), power=.38, resolution=(24,64), levels=None):
    """Closed upholstered volume with smooth analytic normals.

    Optional normalized height samples resolve closely spaced stitch channels
    without uniformly increasing the tessellation of every cushion.
    """
    rings,segments=resolution
    lat=np.linspace(-np.pi/2,np.pi/2,rings+1)
    if levels is not None:
        levels=np.asarray(levels)
        lat=np.arcsin(np.sign(levels)*np.abs(levels)**(1/power))
        rings=len(levels)-1
    lon=np.arange(segments)*2*np.pi/segments
    def sp(x,p):return np.sign(x)*np.abs(x)**p
    a,b=np.meshgrid(lat,lon,indexing='ij')
    q=np.stack([sp(np.cos(a),power)*sp(np.cos(b),power),
                sp(np.cos(a),power)*sp(np.sin(b),power),sp(np.sin(a),power)],axis=-1)
    # Exact poles close the volume; even a tiny angular gap grows visibly
    # under the fractional exponent used for broad upholstered faces.
    q[0]=[0,0,-1];q[-1]=[0,0,1]
    vertices=q*np.array(size)/2
    # A superellipsoid is the Lp sphere with p=2/power.
    normals=sp(q,2/power-1)/np.array(size)
    normals/=np.maximum(np.linalg.norm(normals,axis=-1,keepdims=True),1e-12)
    vertices=vertices@np.asarray(frame).T+center;normals=normals@np.asarray(frame).T
    f=[]
    for i in range(rings):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments;c=b+segments;d=a+segments
            if i>0:f.append((a,b,c))
            if i<rings-1:f.append((a,c,d))
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


SEAT_BASE_X, SEAT_BASE_Z = -.26, .31
SEAT_ANGLE = np.deg2rad(31)
SEAT_UP = np.array([-np.sin(SEAT_ANGLE), 0, np.cos(SEAT_ANGLE)])
SEAT_BADGE_H = .234
SEAT_DRIVER_FORWARD = .10


def seat_badge_uv(v):
    base = np.column_stack([SEAT_BASE_X+np.where(v[:, 1]>0, SEAT_DRIVER_FORWARD, 0), np.sign(v[:, 1])*.4,
                            np.full(len(v), SEAT_BASE_Z)])
    return np.column_stack([(v[:, 1]-base[:, 1])/.086+.5,
                            ((v-base)@SEAT_UP-SEAT_BADGE_H)/.015])


def seat_profile(z, knots):
    """Cubic Hermite profile and derivative, shared by skin and sewn details."""
    x, y = np.asarray(knots).T
    slopes = np.gradient(y, x)
    z = np.asarray(z)
    i = np.clip(np.searchsorted(x, z)-1, 0, len(x)-2)
    span = x[i+1]-x[i]
    t = np.clip((z-x[i])/span, 0, 1)
    value = ((2*t**3-3*t*t+1)*y[i] + (t**3-2*t*t+t)*span*slopes[i]
             + (-2*t**3+3*t*t)*y[i+1] + (t**3-t*t)*span*slopes[i+1])
    derivative = ((6*t*t-6*t)*y[i]/span + (3*t*t-4*t+1)*slopes[i]
                  + (-6*t*t+6*t)*y[i+1]/span + (3*t*t-2*t)*slopes[i+1])
    return value, derivative


def seat_surround():
    """One upholstered shoulder/bolster frame, with a recessed center aperture.

    Paired rounded outlines carry a variable-depth oval section: deep lumbar
    wings taper into the shallow shoulder bridge visible in studio 04 and 12.
    """
    def outline(half_width, bottom, top, radius):
        points = []
        centers = [(half_width-radius, top-radius), (-half_width+radius, top-radius),
                   (-half_width+radius, bottom+radius), (half_width-radius, bottom+radius)]
        for j, center in enumerate(centers):
            angles = np.linspace(j*np.pi/2, (j+1)*np.pi/2, 16, endpoint=False)
            points.extend(np.array(center)+radius*np.column_stack([np.cos(angles), np.sin(angles)]))
            end = np.array(center)+radius*np.array([np.cos((j+1)*np.pi/2), np.sin((j+1)*np.pi/2)])
            nxt = np.array(centers[(j+1)%4])+radius*np.array([np.cos((j+1)*np.pi/2), np.sin((j+1)*np.pi/2)])
            points.extend(end+(nxt-end)*np.linspace(0,1,24,endpoint=False)[:,None])
        return np.array(points)
    outer = outline(.238, 0, .54, .040)
    inner = outline(.149, .025, .446, .020)
    outer[:,0] *= np.interp(outer[:,1], [0,.15,.35,.54], [.96,1,.98,.93])
    inner[:,0] *= np.interp(inner[:,1], [0,.20,.446], [.78,.91,1])
    middle, delta = (outer+inner)/2, (outer-inner)/2
    def section(q):
        wh = middle+delta*np.sign(np.cos(q))*abs(np.cos(q))**.68
        radius = seat_profile(wh[:,1], [(0,.025),(.06,.14),(.16,.13),(.28,.095),
                                        (.40,.068),(.49,.057),(.54,.040)])[0]
        depth = .005+np.sign(np.sin(q))*abs(np.sin(q))**.48*(radius if np.sin(q)>=0 else np.full(len(wh),.035))
        return np.column_stack([depth, wh])
    angles = np.arange(32)*2*np.pi/32
    v = np.stack([section(q) for q in angles],axis=1)
    # Analytic tangents of the sampled periodic surface give smooth normals.
    n = np.cross(np.roll(v,-1,axis=0)-np.roll(v,1,axis=0),
                 np.roll(v,-1,axis=1)-np.roll(v,1,axis=1))
    # At q=0 the normal must point away from the opening in the w/h plane.
    if np.sum(n[:,0,1:]*delta)<0:n=-n
    n /= np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-12)
    faces=[]
    for i in range(len(outer)):
        for j in range(len(angles)):
            a=i*32+j;b=((i+1)%len(outer))*32+j;c=((i+1)%len(outer))*32+(j+1)%32;d=i*32+(j+1)%32
            faces.extend([(a,b,c),(a,c,d)])
    f=np.array(faces);tri=v.reshape(-1,3)[f];norm=n.reshape(-1,3)[f]
    if np.sum(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])*norm[:,0])<0:
        tri=tri[:,::-1];norm=norm[:,::-1]
    return (tri.reshape(-1,3),norm.reshape(-1,3)), section


def seats():
    all_parts=Parts()
    right=np.array([0,1,0]);up=SEAT_UP;front=np.cross(right,up)
    frame=np.column_stack([front,right,up])
    pitch=np.deg2rad(6)
    cushion_frame=np.array([[np.cos(pitch),0,-np.sin(pitch)],[0,1,0],[np.sin(pitch),0,np.cos(pitch)]])
    head_angle=np.deg2rad(-6)
    head_frame=np.array([[np.cos(head_angle),0,-np.sin(head_angle)],[0,1,0],[np.sin(head_angle),0,np.cos(head_angle)]])
    surround, surround_section=seat_surround()
    # Project shoulder stitching onto the actual triangulated front skin. A
    # straight seam in upholstery space must not kink at a mesh parameter join.
    front_tri=surround[0].reshape(-1,3,3)
    front_tri=front_tri[np.min(front_tri[:,:,0],axis=1)>=.005-1e-9]
    origin=front_tri[:,0,1:];skin_u=front_tri[:,1,1:]-origin;skin_v=front_tri[:,2,1:]-origin
    det=skin_u[:,0]*skin_v[:,1]-skin_u[:,1]*skin_v[:,0]
    valid=np.abs(det)>1e-12
    front_tri,origin,skin_u,skin_v,det=front_tri[valid],origin[valid],skin_u[valid],skin_v[valid],det[valid]
    def shoulder_skin(wh):
        q=np.asarray(wh)-origin
        a=(q[:,0]*skin_v[:,1]-q[:,1]*skin_v[:,0])/det
        b=(skin_u[:,0]*q[:,1]-skin_u[:,1]*q[:,0])/det
        inside=(a>=-1e-7)&(b>=-1e-7)&(a+b<=1+1e-7)
        if not inside.any():raise ValueError('Shoulder seam outside padded skin')
        depths=front_tri[:,0,0]*(1-a-b)+front_tri[:,1,0]*a+front_tri[:,2,0]*b
        return np.r_[depths[inside].max()+.0002,wh]
    insert_curve=[(0,0),(.08,.022),(.15,.026),(.24,.006),(.30,-.003),(.37,.005),(.47,0)]
    stitch_rows=np.array([.190,.224,.258,.292])
    def insert_relief(h):
        value,derivative=seat_profile(h,insert_curve)
        # Compressed foam under sewn joins: actual shallow channels, not black
        # lines placed across an otherwise flat cushion.
        for row in stitch_rows:
            t=(h-row)/.003
            dip=.0009*np.exp(-t*t)
            value-=dip;derivative+=2*t*dip/.003
        return value,derivative
    def skin_depth(u,v,ru,rv,depth,power):
        power_n=2/power
        return depth*max(0,1-abs(u/ru)**power_n-abs(v/rv)**power_n)**(1/power_n)
    for side in [-1,1]:
        p=Parts()
        y=side*.40
        base=np.array([SEAT_BASE_X,y,SEAT_BASE_Z])
        def point(d,w,h):return base+front*d+right*w+up*h
        # Thin seat pan clears the retained rails. The front rises six degrees.
        p.add('plastic',pillow([-.105,y,.295],[.47,.435,.05],power=.32,resolution=(12,40)))
        cushion_center=np.array([-.07,y,.325])
        def cushion_point(x,w,z):return cushion_center+cushion_frame@np.array([x,w,z])
        p.add('leather',pillow(cushion_center,[.50,.365,.067],cushion_frame,power=.28))
        for sy in [-1,1]:
            center=cushion_point(-.01,sy*.195,.017)
            # Side cushions flare gently toward the thighs rather than running
            # as parallel padded rails.
            flare=np.eye(3);flare[1,0]=sy*.06
            v,n=pillow([0,0,0],[.53,.095,.085],power=.42)
            def thigh_shape(x):
                height,dh=seat_profile(x,[(-.265,1.25),(-.12,1.18),(.08,.80),(.265,.45)])
                shift,ds=seat_profile(x,[(-.265,.008),(-.12,.005),(.08,-.004),(.265,-.013)])
                return height,dh,shift,ds
            height,dh,shift,ds=thigh_shape(v[:,0])
            n[:,0]-=n[:,2]*(v[:,2]*dh+ds)/height;n[:,2]/=height
            v[:,2]=v[:,2]*height+shift
            n=n@np.linalg.inv(flare);n/=np.linalg.norm(n,axis=1,keepdims=True)
            p.add('leather',(v@flare.T@cushion_frame.T+center,n@cushion_frame.T))
            def edge(dy):
                path=[]
                for x in np.linspace(-.245,.245,85):
                    height,_,shift,_=thigh_shape(x)
                    z=skin_depth(x,dy,.265,.0475,.0425,.42)*height+shift+.0004
                    path.append(center+cushion_frame@flare@np.array([x,sy*dy,z]))
                return path
            p.seam(edge(.029),thread_path=edge(.026))
        def base_ring(z):
            scale=(1-abs(z/.0335)**(2/.28))**(.28/2)
            return [cushion_point(.25*scale*np.sign(np.cos(a))*abs(np.cos(a))**.28,
                                 .1825*scale*np.sign(np.sin(a))*abs(np.sin(a))**.28,z)
                    for a in np.linspace(0,2*np.pi,128,endpoint=False)]
        p.seam(base_ring(.014),closed=True,thread_path=base_ring(.016))
        def cushion_row(x):return [cushion_point(x,w,skin_depth(x,w,.25,.1825,.0335,.28)+.0004)
                                  for w in np.linspace(-.173,.173,80)]
        p.seam(cushion_row(-.105),thread_path=cushion_row(-.1025),radius=.0006)
        # Continuous padded perimeter, over a slim rear shell; no detached pillars.
        p.add('leather',pillow(point(-.025,0,.267),[.075,.423,.53],frame,power=.35))
        p.add('leather',(surround[0]@frame.T+base,surround[1]@frame.T))
        p.seam(surround_section(.74)@frame.T+base,closed=True,
               thread_path=surround_section(.80)@frame.T+base,radius=.00065)
        # Diagonal sewn joins separate the shoulder bridge from each side wing.
        for sign in [-1,1]:
            def shoulder_join(thread=False):
                start=surround_section(.74)[18,1:]
                end=surround_section(np.pi-.16)[8,1:]
                path=[]
                for t in np.linspace(0,1,65):
                    wh=(1-t)*start+t*end
                    wh[0]+=.004*np.sin(np.pi*t)+(.0016 if thread else 0)
                    wh[0]*=sign
                    path.append(shoulder_skin(wh))
                return np.array(path)@frame.T+base
            p.seam(shoulder_join(),thread_path=shoulder_join(True),radius=.00045)
        # The center panel follows a lumbar bulge, then hollows below the shoulders.
        heights=np.unique(np.r_[np.linspace(-.005,.475,73),
                                (stitch_rows[:,None]+np.array([-.007,-.004,-.002,0,.002,.004,.007])).ravel()])
        v,n=pillow([.020,0,.235],[.072,.318,.48],power=.34,resolution=(40,64),
                   levels=np.clip((heights-.235)/.24,-1,1))
        shift,derivative=insert_relief(v[:,2])
        scale,scale_derivative=seat_profile(v[:,2],[(0,.88),(.22,.97),(.47,1)])
        n[:,2]-=n[:,0]*derivative+n[:,1]*v[:,1]*scale_derivative/scale
        n[:,1]/=scale;n/=np.linalg.norm(n,axis=1,keepdims=True)
        v[:,0]+=shift;v[:,1]*=scale
        p.add('leather',(v@frame.T+base,n@frame.T))
        def insert_face(w,h):
            width=seat_profile(h,[(0,.88),(.22,.97),(.47,1)])[0]
            return .020+insert_relief(h)[0]+skin_depth(w/width,h-.235,.159,.24,.036,.34)
        for h in stitch_rows:
            def seam_row(height):return [point(insert_face(w,height)+.0004,w,height) for w in np.linspace(-.144,.144,80)]
            p.seam(seam_row(h),thread_path=seam_row(h+.0018),radius=.00035)
        # Small subdivided embroidery patch follows the curved lumbar upholstery.
        vertices=[]
        for h0,h1 in zip(np.linspace(SEAT_BADGE_H,SEAT_BADGE_H+.015,5)[:-1],np.linspace(SEAT_BADGE_H,SEAT_BADGE_H+.015,5)[1:]):
            for w0,w1 in zip(np.linspace(-.043,.043,13)[:-1],np.linspace(-.043,.043,13)[1:]):
                corners=[point(insert_face(w,h)+.0008,w,h) for w,h in [(w0,h0),(w1,h0),(w1,h1),(w0,h1)]]
                vertices.extend(corners[i] for i in [0,1,2,0,2,3])
        vertices=np.array(vertices)
        p.add('badge',(vertices,np.tile(front,(len(vertices),1))))
        # Studio 07: headrest is almost upright, independent of the reclining back.
        head_center=np.array([-.51,y,.861])
        def head_point(d,w,h):return head_center+head_frame@np.array([d,w,h])
        for w in [-.09,.09]:
            a=point(-.01,w,.525);b=head_point(-.01,w,-.065)
            p.add('metal',cylinder(a,b,.005,16))
            p.add('plastic',pillow(a,[.025,.029,.012],frame,power=.4,resolution=(8,24)))
        p.add('leather',pillow(head_center,[.114,.326,.175],head_frame,power=.42))
        for sy in [-1,1]:
            def headrest_ring(w):
                scale=(1-(abs(w)/.163)**(2/.42))**(.42/2)
                return [head_point(.057*scale*np.sign(np.cos(a))*abs(np.cos(a))**.42,w,
                                   .0875*scale*np.sign(np.sin(a))*abs(np.sin(a))**.42)
                        for a in np.linspace(0,2*np.pi,100,endpoint=False)]
            p.seam(headrest_ring(sy*.151),closed=True,thread_path=headrest_ring(sy*.149))
        for sy in [-1,1]:
            c=point(-.015,sy*.244,.048)
            p.add('plastic',cylinder(c-right*.012,c+right*.012,.031,32))
            for a in np.arange(24)*2*np.pi/24:
                q=c+np.array([np.cos(a)*.030,0,np.sin(a)*.030])
                p.add('plastic',cylinder(q-right*.013,q+right*.013,.002,6))
        p.add('plastic',pillow(point(-.015,side*.231,.31),[.045,.020,.073],frame,power=.38,resolution=(12,32)))
        p.add('plastic',pillow([-.25,side*.124,.375],[.058,.025,.067],power=.35,resolution=(12,32)))
        p.add('metal',plate([-.25,side*.124,.408],[1,0,0],[0,1,0],.036,.018,.003,.003))
        p.add('red',plate([-.236,side*.124,.411],[1,0,0],[0,1,0],.023,.017,.004,.002))
        p.add('piping',plate([-.261,side*.124,.411],[1,0,0],[0,1,0],.010,.012,.004,.001))
        p.add('metal',tube([[.14,y-.16,.285],[.23,y-.16,.285],[.25,y,.29],[.23,y+.16,.285],[.14,y+.16,.285]],.005))
        # Driver seat is one rail position farther forward in studio 07.
        offset=np.array([SEAT_DRIVER_FORWARD if side>0 else 0,0,0])
        for finish,(v,n) in p.result().items():all_parts.add(finish,(v+offset,n))
    return all_parts.result()


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
