"""Close the donor's open door skins and identify trim by their actual outline.

Source coordinates are X forward, Y left, Z up. The painted skins define both
perimeters; no rectangular cabin slice is used to decide which trim lifts.
"""
from collections import Counter, defaultdict
import numpy as np


def skin_geometry(source, component):
    faces = source['loops'][source['tris']]
    faces = faces[source['comp'][faces[:, 0]] == component]
    used = np.unique(faces)
    vertices, inverse = np.unique(np.round(source['v'][used], 5), axis=0, return_inverse=True)
    remap = np.empty(len(source['v']), int)
    remap[used] = inverse
    faces = remap[faces]
    edges = Counter(tuple(sorted(e)) for f in faces for e in zip(f, np.roll(f, -1)))
    boundary = [(a, b) for f in faces for a, b in zip(f, np.roll(f, -1)) if edges[tuple(sorted((a, b)))] == 1]
    adjacent = defaultdict(list)
    for a, b in boundary:
        adjacent[a].append(b)
        adjacent[b].append(a)
    if any(len(v) != 2 for v in adjacent.values()):
        raise ValueError('Door skin has a branched boundary')
    unseen = set(adjacent)
    loops = []
    while unseen:
        start = min(unseen)
        loop, previous, current = [], -1, start
        while True:
            loop.append(current)
            unseen.discard(current)
            nxt = next(n for n in adjacent[current] if n != previous)
            if nxt == start:
                break
            previous, current = current, nxt
        loops.append(np.array(loop))
    outer = max(loops, key=lambda ids: np.ptp(vertices[ids, 2]))
    return vertices, faces, boundary, outer


def contains_outline(points, outline, tolerance=.012):
    """Side projection, including the roof wing; tolerate the folded skin lip."""
    p = np.asarray(points)[:, [0, 2]]
    poly = outline[:, [0, 2]]
    inside = np.zeros(len(p), bool)
    nearest = np.full(len(p), np.inf)
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        delta = b - a
        t = np.clip(((p - a) @ delta) / max(delta @ delta, 1e-12), 0, 1)
        nearest = np.minimum(nearest, np.linalg.norm(p - a - t[:, None] * delta, axis=1))
        if abs(delta[1]) > 1e-10:
            crossing = ((a[1] > p[:, 1]) != (b[1] > p[:, 1]))
            inside ^= crossing & (p[:, 0] < a[0] + (p[:, 1] - a[1]) * delta[0] / delta[1])
    return inside | (nearest <= tolerance)


def door_shell(source, component):
    v, f, boundary, outer = skin_geometry(source, component)
    lookup = {tuple(p):i for i,p in enumerate(v)}
    loops = source['tris'][source['comp'][source['loops'][source['tris'][:,0]]] == component].ravel()
    ids = [lookup[tuple(p)] for p in np.round(source['v'][source['loops'][loops]],5)]
    n = np.zeros_like(v)
    np.add.at(n, ids, source['n'][loops])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    # Deep lower door box supports the door card; the window and roof flanges
    # are thinner. Preserve the glass opening and all original exterior seams.
    depth = np.interp(v[:, 2], [.31, .38, .55, .68, .78, 1.10, 1.16],
                     [.065, .075, .085, .065, .018, .012, .012])
    # Offset along the main door section, not the tiny folded-lip normals.
    # Extruding those hard end normals produces spikes at the seam corners.
    z=v[:,2]
    mix=np.clip((z-.76)/.10,0,1);mix=mix*mix*(3-2*mix)
    roof=np.clip((z-1.09)/.06,0,1);roof=roof*roof*(3-2*roof)
    ny=(1-.22*mix)*(1-roof)
    nz=np.interp(z,[.31,.55,.76],[-.22,0,.25])*(1-mix)+.63*mix
    nz=nz*(1-roof)+roof
    section=np.column_stack([np.zeros(len(v)),np.sign(v[:,1])*ny,nz])
    section/=np.linalg.norm(section,axis=1,keepdims=True)
    inner = v - section * depth[:, None]
    count = len(v)
    vertices = np.concatenate([v, inner])
    back = f[:, ::-1] + count
    walls = np.array([tri for a, b in boundary for tri in [(a, a+count, b+count), (a, b+count, b)]])
    # A closed, consistently wound skin + backing + rim is required. Reject a
    # changed source rather than silently exporting another open door cavity.
    complete = np.concatenate([f, back, walls])
    edges = Counter(tuple(sorted(e)) for face in complete for e in zip(face, np.roll(face, -1)))
    if any(value != 2 for value in edges.values()):
        raise ValueError('Door box is not closed')
    normals = np.concatenate([n, -n])
    points, shading = [vertices[back].reshape(-1, 3)], [normals[back].reshape(-1, 3)]
    wv = vertices[walls]
    wn = np.cross(wv[:, 1] - wv[:, 0], wv[:, 2] - wv[:, 0])
    wn /= np.maximum(np.linalg.norm(wn, axis=1, keepdims=True), 1e-12)
    points.append(wv.reshape(-1, 3))
    rim_normals = np.zeros_like(vertices)
    for i in range(3):
        np.add.at(rim_normals, walls[:, i], wn)
    rim_normals /= np.maximum(np.linalg.norm(rim_normals, axis=1, keepdims=True), 1e-12)
    shading.append(rim_normals[walls].reshape(-1, 3))
    return np.concatenate(points), np.concatenate(shading), (v, inner, outer)


def plate(center, u, v, width, height, depth, radius):
    """Rounded extruded plate in an explicit surface frame, as triangle soup."""
    u, v = np.asarray(u), np.asarray(v)
    normal = np.cross(u, v)
    ring = []
    for sx, sy, start in [(1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)]:
        for angle in np.linspace(start, start+90, 7, endpoint=False):
            a = np.deg2rad(angle)
            ring.append((sx*(width/2-radius)+radius*np.cos(a), sy*(height/2-radius)+radius*np.sin(a)))
    ring = np.array(ring)
    base = np.asarray(center) + ring[:, :1]*u + ring[:, 1:]*v
    n = len(ring)
    vertices = np.concatenate([base-normal*depth/2, base+normal*depth/2,
                               [center-normal*depth/2, center+normal*depth/2]])
    faces = []
    for a in range(n):
        b = (a+1) % n
        faces.extend([(2*n,b,a),(2*n+1,a+n,b+n),(a,b,b+n),(a,b+n,a+n)])
    tri = vertices[np.array(faces)]
    normals = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0])
    normals /= np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    return tri.reshape(-1,3), np.repeat(normals,3,axis=0)


def end_frame(skin, height, front):
    outer, inner, ids = skin
    candidates = []
    for a,b in zip(ids,np.roll(ids,-1)):
        dz=outer[b,2]-outer[a,2]
        if abs(dz)<1e-8:continue
        t=(height-outer[a,2])/dz
        if not 0<=t<=1:continue
        p=outer[a]*(1-t)+outer[b]*t
        q=inner[a]*(1-t)+inner[b]*t
        u=p-q;u/=np.linalg.norm(u)
        v=outer[b]-outer[a]
        if v[2]<0:v=-v
        v-=u*np.dot(u,v);v/=np.linalg.norm(v)
        if np.cross(u,v)[0]*(1 if front else -1)<0:u=-u
        candidates.append((p[0],(p+q)/2,u,v))
    return (max if front else min)(candidates,key=lambda x:x[0])[1:]


def edge_details(skin):
    """Hardware follows the new end caps instead of the old procedural door."""
    parts = defaultdict(list)
    def add(name, frame, w,h,d,r,offset=0):
        c,u,v=frame
        parts[name].append(plate(c+np.cross(u,v)*offset,u,v,w,h,d,r))
    for front in [True,False]:
        frame=end_frame(skin,.43,front)
        add('housing',frame,.036,.034,.005,.004,.003)
        add('amber' if front else 'red',frame,.028,.026,.006,.003,.006)
        frame=end_frame(skin,.57,front)
        add('latch',frame,.047,.070,.002,.004,.0015)
        add('recess',frame,.018,.030,.001,.003,.0028)
        c,u,v=frame
        add('steel',(c+v*.004,u,v),.018,.007,.004,.001,.004)
        for x in [-.016,.016]:
            for y in [-.025,.025]:
                bolt=(c+u*x+v*y,u,v)
                add('steel',bolt,.005,.005,.0015,.0025,.003)
                add('recess',bolt,.003,.0007,.0003,.0002,.004)
    # Bottom courtesy lamp, centred along the straight lower door edge.
    outer,inner,ids=skin
    candidates=[]
    for a,b in zip(ids,np.roll(ids,-1)):
        dx=outer[b,0]-outer[a,0]
        if abs(dx)<1e-8:continue
        t=(-.12-outer[a,0])/dx
        if 0<=t<=1:
            p=outer[a]*(1-t)+outer[b]*t;q=inner[a]*(1-t)+inner[b]*t
            u=outer[b]-outer[a]
            if u[0]<0:u=-u
            u/=np.linalg.norm(u);v=p-q;v-=u*np.dot(u,v);v/=np.linalg.norm(v)
            if np.cross(u,v)[2]>0:v=-v
            candidates.append(((p+q)/2,u,v))
    frame=min(candidates,key=lambda f:f[0][2])
    add('housing',frame,.044,.031,.005,.004,.002)
    add('amber',frame,.036,.023,.006,.003,.005)
    # A narrow rubber seal follows the actual inner rim, including the roof wing.
    path=inner[ids]
    normal=inner[ids]-outer[ids]
    normal/=np.linalg.norm(normal,axis=1,keepdims=True)
    tangent=np.roll(path,-1,axis=0)-np.roll(path,1,axis=0)
    tangent/=np.linalg.norm(tangent,axis=1,keepdims=True)
    u=normal-tangent*np.sum(normal*tangent,axis=1)[:,None]
    u/=np.linalg.norm(u,axis=1,keepdims=True)
    v=np.cross(tangent,u)
    angles=np.arange(8)*np.pi/4
    radial=u[:,None,:]*np.cos(angles)[None,:,None]+v[:,None,:]*np.sin(angles)[None,:,None]
    vertices=(path[:,None,:]+normal[:,None,:]*.0015+radial*.0025).reshape(-1,3)
    normals=radial.reshape(-1,3)
    faces=[]
    for i in range(len(path)):
        for j in range(8):
            a=i*8+j;b=i*8+(j+1)%8;c=((i+1)%len(path))*8+(j+1)%8;d=((i+1)%len(path))*8+j
            faces.extend([(a,b,c),(a,c,d)])
    faces=np.array(faces)
    parts['seal'].append((vertices[faces].reshape(-1,3),normals[faces].reshape(-1,3)))
    return {name:(np.concatenate([p[0] for p in pieces]),np.concatenate([p[1] for p in pieces]))
            for name,pieces in parts.items()}


def body_jamb(skin):
    """Fixed doorway returns, sill, weatherstrip and striker plates.

    Follow the donor's seam in 3D. The return bridges the outer body edge to
    cabin trim instead of leaving a view through the sill or rear quarter.
    """
    outer, inner, ids = skin
    path = outer[ids]
    inward = inner[ids] - path
    inward /= np.linalg.norm(inward, axis=1, keepdims=True)
    tangent = np.roll(path,-1,axis=0) - np.roll(path,1,axis=0)
    tangent /= np.linalg.norm(tangent,axis=1,keepdims=True)
    radial = np.cross(tangent,inward)
    radial /= np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),1e-12)
    # The source has opposite winding on the two sides.
    if np.sum(radial*(path-path.mean(0)))<0:radial=-radial
    width = np.interp(path[:,2],[.31,.65,.90,1.10,1.16],[.20,.19,.13,.055,.025])
    lip = path + radial*.009 + inward*.006
    # Rounded step into the cabin. Narrow raised lip carries the rubber seal.
    rings = [lip, lip+inward*.025, lip+inward*(width[:,None]*.75)-radial*.020,
             lip+inward*width[:,None]-radial*.035]
    # Closed wall under the visible return, so both inside and outside views
    # show a physical jamb instead of a one-sided patch.
    rings += [rings[-1]+radial*.012, rings[0]+radial*.012]
    v=np.stack(rings,axis=1)
    faces=[]
    for i in range(len(path)):
        ni=(i+1)%len(path)
        for j in range(len(rings)):
            nj=(j+1)%len(rings)
            faces.extend([(i*6+j,ni*6+j,ni*6+nj),(i*6+j,ni*6+nj,i*6+nj)])
    v=v.reshape(-1,3);faces=np.array(faces)
    tri=v[faces]
    # Mirrored source loops may wind differently. Keep the closed return's
    # outward faces visible from above the sill as well as from the cabin.
    if np.sum(tri[:,0]*np.cross(tri[:,1],tri[:,2]))<0:
        faces=faces[:,::-1];tri=v[faces]
    normals=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
    normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    # Smooth along the doorway, retain the cross-section's fold lines.
    smooth=np.zeros_like(v)
    for j in range(3):np.add.at(smooth,faces[:,j],normals)
    smooth/=np.maximum(np.linalg.norm(smooth,axis=1,keepdims=True),1e-12)
    parts={'shell':(tri.reshape(-1,3),smooth[faces].reshape(-1,3))}
    # A continuous compression seal runs along the return, just inside the lip.
    center=lip+inward*.045-radial*.004
    angles=np.arange(10)*np.pi/5
    radius=inward[:,None,:]*np.cos(angles)[None,:,None]+radial[:,None,:]*np.sin(angles)[None,:,None]
    verts=(center[:,None,:]+radius*.006).reshape(-1,3);norm=radius.reshape(-1,3)
    f=[]
    for i in range(len(path)):
        for j in range(10):
            a=i*10+j;b=i*10+(j+1)%10;c=((i+1)%len(path))*10+(j+1)%10;d=((i+1)%len(path))*10+j
            f.extend([(a,b,c),(a,c,d)])
    f=np.array(f)
    tri=verts[f]
    if np.sum(tri[:,0]*np.cross(tri[:,1],tri[:,2]))<0:f=f[:,::-1]
    parts['seal']=(verts[f].reshape(-1,3),norm[f].reshape(-1,3))
    # Bare metal flange beside the rear weatherstrip, visible in studio 03/04.
    flange=[]
    for i in range(len(path)):
        j=(i+1)%len(path)
        if not (path[[i,j],0].max()<-.30 and path[[i,j],1].min()*np.sign(path[0,1])>.45
                and path[[i,j],2].max()<1.135 and path[[i,j],2].min()>.33):continue
        a,b=lip[[i,j]]-radial[[i,j]]*.001
        c=b+inward[j]*.028;d=a+inward[i]*.028
        tris=np.array([[a,b,c],[a,c,d]])
        norm=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0])
        if np.dot(norm[0],radial[i])>0:tris=tris[:,::-1];norm=-norm
        norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12)
        flange.append((tris.reshape(-1,3),np.repeat(norm,3,axis=0)))
    if flange:parts['flange']=(np.concatenate([v for v,n in flange]),np.concatenate([n for v,n in flange]))
    hardware=[]
    for front in [True,False]:
        c,u,z=end_frame(skin,.57,front)
        # Face toward the opening, opposing the corresponding door latch.
        n=-np.cross(u,z)
        c=c+n*(.024 if not front else -.014)
        if not front:parts['housing']=plate(c-n*.018,u,-z,.078,.095,.032,.008)
        hardware.append(plate(c,u,-z,.045,.066,.003,.006))
        hardware.append(plate(c+n*.009,u,-z,.009,.026,.016,.004))
        for offset in [-.024,.024]:
            hardware.append(plate(c+z*offset+n*.002,u,-z,.006,.006,.003,.003))
    parts['striker']=(np.concatenate([v for v,n in hardware]),np.concatenate([n for v,n in hardware]))
    screws=[]
    for height in [.42,.68,.82,.95,1.06]:
        for i in range(len(path)):
            j=(i+1)%len(path)
            if path[[i,j],0].max()>-.3 or not min(path[i,2],path[j,2])<height<=max(path[i,2],path[j,2]):continue
            t=(height-path[i,2])/(path[j,2]-path[i,2])
            p=lip[i]*(1-t)+lip[j]*t
            u=inward[i]*(1-t)+inward[j]*t;u/=np.linalg.norm(u)
            v=tangent[i]*(1-t)+tangent[j]*t;v-=u*np.dot(u,v);v/=np.linalg.norm(v)
            if np.dot(np.cross(u,v),radial[i])>0:v=-v
            screws.append(plate(p+u*.014+np.cross(u,v)*.002,u,v,.006,.006,.002,.003))
    if screws:
        pv,pn=parts['striker'];parts['striker']=(np.concatenate([pv]+[v for v,n in screws]),np.concatenate([pn]+[n for v,n in screws]))
    return parts
