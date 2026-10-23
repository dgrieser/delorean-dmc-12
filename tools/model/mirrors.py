"""Studio-reference door mirrors, lofted once in the left-side body frame.

The moulded housing, recessed glass, swept pedestal and lower pivot shoe are
separate closed surfaces above a thin mounting plate. The right mirror is an exact reflection of this mesh.
Studio 01/02 constrain the front face; 03/04/07 the section and pedestal;
05/06 the glass opening; 08 the sweep and depth.
"""
import numpy as np
import body as B

ORIGIN = np.array([0.375, 0.816, 0.830])
SWEEP = np.deg2rad(24.0)
AXIS = np.array([-np.sin(SWEEP), np.cos(SWEEP), 0.0])
FRONT = np.array([np.cos(SWEEP), np.sin(SWEEP), 0.0])


def world(s, t, w):
    # The head rakes slightly back and inward above its lower pivot.
    s, t, w = np.broadcast_arrays(s, t, w)
    return ORIGIN + (s-.10*w)[..., None]*AXIS + (.90*t-.25*w)[..., None]*FRONT + w[..., None]*[0, 0, 1]


def outline(corners, radius, arc_steps=12, edge_steps=12):
    """Rounded polygon with corresponding corner/edge samples between lofts."""
    p = np.asarray(corners, float)
    cuts = []
    for i, point in enumerate(p):
        a, b = p[i-1]-point, p[(i+1)%len(p)]-point
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        r = min(np.broadcast_to(radius, (len(p),))[i], 0.49*la, 0.49*lb)
        cuts.append((point+a*r/la, point, point+b*r/lb))
    out = []
    for i, (a, b, c) in enumerate(cuts):
        for u in np.linspace(0, 1, arc_steps, endpoint=False):
            out.append((1-u)**2*a + 2*(1-u)*u*b + u*u*c)
        end = cuts[(i+1)%len(p)][0]
        for u in np.linspace(0, 1, edge_steps, endpoint=False):
            out.append(c*(1-u) + end*u)
    return np.asarray(out)


def loft(rings):
    """Closed loft, smooth area-weighted normals, outward winding."""
    rings = np.asarray(rings)
    count, n, _ = rings.shape
    v = rings.reshape(-1, 3)
    f = []
    for r in range(count-1):
        for i in range(n):
            a=r*n+i; b=r*n+(i+1)%n; c=b+n; d=a+n
            f.extend([(a,b,c),(a,c,d)])
    v = np.vstack([v, rings[0].mean(0), rings[-1].mean(0)])
    for i in range(n):
        j=(i+1)%n
        f.extend([(count*n,j,i),(count*n+1,(count-1)*n+i,(count-1)*n+j)])
    f = np.asarray(f, np.int32)
    # The local S/T/Z frame is reflected relative to world X/Y/Z.
    a,b,c=v[f[:,0]],v[f[:,1]],v[f[:,2]]
    if np.einsum('ij,ij->i',a,np.cross(b,c)).sum()<0:
        f=f[:,[0,2,1]]
    normals=np.zeros_like(v)
    fn=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])
    for i in range(3): np.add.at(normals,f[:,i],fn)
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    return v,f,normals


def head_profiles():
    back=outline([(.002,.053),(.184,.047),(.181,-.044),(.050,-.056)],[.010,.019,.022,.012])
    front=outline([(.002,.047),(.180,.045),(.176,-.045),(.046,-.047)],[.010,.031,.031,.012])
    return back,front


def housing():
    back,front=head_profiles()
    center=np.array([.109,0.0])
    rings=[]
    # Slightly crowned front face, then the rolled shoulder into the shell.
    face=[(r,.034-.0012*(r/.82)**2) for r in np.linspace(.06,.82,15)]
    face += [(.82+.18*np.sin(a),.0328-.0228*(1-np.cos(a)))
             for a in np.linspace(0,np.pi/2,12)[1:]]
    for scale,t in face:
        p=center+(front-center)*scale
        rings.append(world(p[:,0],t,p[:,1]))
    for u in np.linspace(0,1,25)[1:]:
        blend=u*u
        p=front*(1-blend)+back*blend
        t=.010-.038*u-.10*p[:,0]*blend
        rings.append(world(p[:,0],t,p[:,1]))
    # A narrow rim turns into the recessed glass pocket.
    c=np.array([.107,0.0])
    opening=c+(back-c)*[.935,.875]
    for u,t in [(0,-.032),(.35,-.034),(1,-.034),(1,-.026)]:
        p=back*(1-u)+opening*u
        rings.append(world(p[:,0],t-.10*p[:,0],p[:,1]))
    return loft(rings)


def glass():
    back,_=head_profiles()
    c=np.array([.107,0.0]);edge=c+(back-c)*[.915,.835]
    rings=[world(edge[:,0],-.024-.10*edge[:,0],edge[:,1])]
    for scale,t in [(1,-.027),(.90,-.0275),(.55,-.028),(.12,-.0282)]:
        p=c+(edge-c)*scale;rings.append(world(p[:,0],t-.10*p[:,0],p[:,1]))
    return loft(rings)


def skin_y(x,z):
    """Actual door skin, including the transition below the glass."""
    y=np.full_like(x,.80)
    for _ in range(12):
        d=B.flanks(x,y,z)
        g=(B.flanks(x,y+.0001,z)-B.flanks(x,y-.0001,z))/.0002
        y-=d/np.maximum(g,.2)
    return y


def sail_plate():
    p=outline([(.520,.824),(.335,.824),(.335,.895),(.520,.837)],.009)
    c=p.mean(0);rings=[]
    # Sample both faces on the actual curved skin. A single polygon fan cuts
    # across the beltline and makes triangular shards emerge through the seal.
    sections=[(r,-.006) for r in np.linspace(.05,1,15)]
    sections += [(1,.002),(.97,.005)]
    sections += [(r,.005) for r in np.linspace(.90,.05,15)]
    for scale,offset in sections:
        q=c+(p-c)*scale;x,z=q.T
        rings.append(np.column_stack([x,skin_y(x,z)+offset,z]))
    return loft(rings)


def pedestal():
    # Corners correspond to front-top, rear-top, rear-bottom, front-bottom of
    # the pivot. The long forward toe stays flush against the triangular sail.
    base=outline([(.495,.834),(.380,.871),(.345,.828),(.510,.828)],.015)
    neck=outline([(.026,.040),(-.030,.045),(-.030,-.054),(.026,-.048)],.026)
    t,w=neck.T
    s=.018-.36*w+.50*(t+.030)
    tip=world(s,t,w)
    bx,bz=base.T;by=skin_y(bx,bz)
    rings=[np.column_stack([bx,by-.006,bz]),np.column_stack([bx,by+.002,bz])]
    for u in np.linspace(0,1,29)[1:]:
        k=np.sin(np.pi*u/2)
        x=bx*(1-k)+tip[:,0]*k;z=bz*(1-k)+tip[:,2]*k
        x+=.012*np.sin(np.pi*u)*np.clip((t+.020)/.040,0,1)
        y0=skin_y(x,z)
        # Concave swept support; no spherical pad or stalk.
        lift=tip[:,1]-skin_y(tip[:,0],tip[:,2])
        y=y0+.002*(1-u)+lift*(1-np.cos(np.pi*u/2))
        rings.append(np.column_stack([x,y,z]))
    return loft(rings)


def shoe():
    p=outline([(.004,-.040),(.088,-.040),(.082,-.057),(.012,-.057)],.012)
    c=np.array([.043,-.051]);rings=[]
    for t,k in [(-.023,.72),(-.020,.90),(-.014,1),(.011,1),(.020,.90),(.024,.72)]:
        q=c+(p-c)*k;rings.append(world(q[:,0],t,q[:,1]))
    return loft(rings)


def join(parts):
    vertices,faces,normals=[],[],[];offset=0
    for v,f,n in parts:
        vertices.append(v);faces.append(f+offset);normals.append(n);offset+=len(v)
    return np.concatenate(vertices),np.concatenate(faces),np.concatenate(normals)


def build():
    left={'mirror_L':join([housing(),sail_plate(),pedestal(),shoe()]),'mirror_glass_L':glass()}
    result=dict(left)
    for name,(v,f,n) in left.items():
        result[name[:-1]+'R']=(v*[1,-1,1],f[:,[0,2,1]],n*[1,-1,1])
    return result
