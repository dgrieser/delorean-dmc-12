"""Small exterior and cabin fittings, fitted to the donor's actual surfaces.

Studio 01/02/08 locate the wing aerial; 05/06 show the louvre fixings and
open dashboard air ducts; 09 shows the bound carpet mats. Coordinates are
metres, X forward, Y left, Z up, as in the other donor builders.
"""
import numpy as np
from donor_cabin import Parts, tube, seat_roundrect
from donor_doors import plate
from donor_hinges import cylinder


class Surface:
    """Intersect an axis ray with one source component, retaining its normals."""
    def __init__(self, source, component, axis=2):
        loops = source['tris']
        loops = loops[source['comp'][source['loops'][loops[:, 0]]] == component]
        self.tri = source['v'][source['loops'][loops]]
        self.normals = source['n'][loops]
        self.axis = axis
        self.other = [i for i in range(3) if i != axis]
        q = self.tri[:, :, self.other]
        self.origin = q[:, 0]
        self.a, self.b = q[:, 1]-q[:, 0], q[:, 2]-q[:, 0]
        det = self.a[:, 0]*self.b[:, 1]-self.a[:, 1]*self.b[:, 0]
        self.det = np.where(abs(det)>1e-12, det, np.nan)

    def at(self, point):
        point = np.asarray(point, float)
        d = point[self.other]-self.origin
        b = (d[:, 0]*self.b[:, 1]-d[:, 1]*self.b[:, 0])/self.det
        c = (self.a[:, 0]*d[:, 1]-self.a[:, 1]*d[:, 0])/self.det
        weights = np.column_stack([1-b-c, b, c])
        hit = np.flatnonzero(np.all(weights>=-1e-6, axis=1))
        if not len(hit):
            raise ValueError(f'Fitting misses source surface at {point}')
        positions = np.sum(self.tri[hit]*weights[hit, :, None], axis=1)
        i = np.argmin(abs(positions[:, self.axis]-point[self.axis]))
        normal = np.sum(self.normals[hit[i]]*weights[hit[i], :, None], axis=0)
        normal /= np.linalg.norm(normal)
        return positions[i], normal


def screw(parts, center, normal, radius=.0035):
    """Low pan head, washer and a visible cross recess."""
    normal = np.asarray(normal)
    u = np.cross(normal, np.eye(3)[np.argmin(abs(normal))])
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    parts.add('hardware', cylinder(center-normal*.0006, center+normal*.0005, radius*1.35, 20))
    parts.add('metal', cylinder(center, center+normal*.0018, radius, 20))
    for a, b in [(u, v), (v, u)]:
        parts.add('recess', plate(center+normal*.00185, a, b, radius*1.45, .00065, .0002, .0002))


def aerial(paint):
    p = Parts()
    base, normal = Surface(paint, 6).at([.765, -.795, .80])
    if normal[2]<0:
        normal = -normal
    # Rubber mounting gasket follows the wing, while the mast leans rearward
    # and outward as measured in the studio front and overhead photographs.
    p.add('rubber', cylinder(base-normal*.001, base+normal*.002, .014, 48))
    p.add('bright', cylinder(base+normal*.002, base+normal*.006, .011, 48))
    start = base+normal*.006
    tip = np.array([.660, -.850, 1.60])
    direction = (tip-start)/np.linalg.norm(tip-start)
    p.add('metal', cylinder(start, start+direction*.010, .0085, 6))
    for lo, hi, radius in [(0, .37, .0027), (.37, .70, .0021), (.70, 1, .0015)]:
        a, b = start+(tip-start)*lo, start+(tip-start)*hi
        p.add('bright', cylinder(a, b, radius, 16))
        if lo:
            p.add('bright', cylinder(a-direction*.002, a+direction*.002, radius+.0005, 20))
    p.add('metal', cylinder(tip-direction*.002, tip+direction*.002, .0024, 20))
    return p.result()


def rear_heater(glass):
    p = Parts()
    surface = Surface(glass, 61, axis=0)
    # Thin fired-on conductors on the cabin face, with wider edge bus bars.
    # Sample the curved glass itself so the lines cannot float across it.
    def width(z):
        return .61-.16*(z-.908)/.179
    for z in np.linspace(.917, 1.080, 9):
        path = [surface.at([-.90, y, z])[0]+[.0008, 0, 0]
                for y in np.linspace(-width(z), width(z), 65)]
        p.add('conductor', tube(path, .00032, sides=6))
    for side in [-1, 1]:
        path = [surface.at([-.90, side*width(z), z])[0]+[.0008, 0, 0]
                for z in np.linspace(.908, 1.087, 25)]
        p.add('conductor', tube(path, .0011, sides=8))
        c, _ = surface.at([-.90, side*width(.924), .924])
        p.add('metal', plate(c+[.002, 0, 0], [0, 1, 0], [0, 0, 1], .015, .012, .002, .002))
        p.add('rubber', tube([c+[.004, 0, 0], c+[.009, side*.018, -.012],
                              c+[.003, side*.026, -.037]], .0017))
    return p.result()


def louvre_fixings(source):
    p = Parts()
    surface = Surface(source, 121)
    # Rear rail: three small screw heads seen across the lip in studio 05/06.
    for y in [-.45, 0, .45]:
        c, n = surface.at([-1.90, y, .96])
        if n[2]<0:
            n = -n
        screw(p, c+n*.0003, n, .0028)
    return p.result()


def pedal(interior, component):
    if component not in [96, 97, 98, 99]:
        raise ValueError(f'Unknown pedal component {component}')
    p = Parts()
    u = np.array([0, -1, 0])
    up = np.array([.392, 0, .920]); up /= np.linalg.norm(up)
    normal = np.cross(u, up)
    # Retain the donor pedal positions and arms; replace only the flat cards.
    points = interior['v'][interior['comp']==component]
    c = (points.min(0)+points.max(0))/2
    width = .028 if component==97 else .064
    height = .130 if component==97 else .105
    p.add('hardware', plate(c-normal*.002, u, up, width-.004, height-.004, .003, .006))
    p.add('grip', plate(c+normal*.001, u, up, width, height, .005, .007))
    path = seat_roundrect(c+normal*.004, u, up, width-.004, height-.004, .006)
    p.add('grip', tube(path, .0012, closed=True))
    for h in np.arange(-height*.37, height*.40, .014):
        middle = c+normal*.0038+up*h
        p.add('grip', cylinder(middle-u*(width-.012)/2, middle+u*(width-.012)/2, .0018, 12))
    return p.result()


def dash_ducts(interior):
    p = Parts()
    for component in [94, 95]:
        points = interior['v'][interior['comp']==component]
        c = points.mean(0)
        _, _, axes = np.linalg.svd(points-c, full_matrices=False)
        normal = axes[-1]
        if normal[0]>0:
            normal = -normal
        up = np.array([0., 0., 1.]); up -= normal*np.dot(up, normal)
        up /= np.linalg.norm(up)
        u = np.cross(up, normal)
        # This is an open transfer duct into the door, not a grey speaker.
        # Its black throat and rolled lip show clearly with the doors raised.
        p.add('recess', cylinder(c-normal*.003, c, .035, 64))
        angles = np.arange(64)*2*np.pi/64
        ring = np.cos(angles)[:, None]*u+np.sin(angles)[:, None]*up
        p.add('rubber', tube(c+normal*.008+ring*.037, .0034, closed=True, sides=12))
        # Cylindrical inner wall, with inward-facing normals.
        rows = np.stack([c+ring*.034, c+normal*.008+ring*.034])
        faces = []
        for i in range(64):
            j = (i+1)%64
            faces.extend([(i, i+64, j+64), (i, j+64, j)])
        faces = np.array(faces)
        verts = rows.reshape(-1, 3)[faces]
        normals = np.tile(-ring, (2, 1))[faces]
        if np.sum(np.cross(verts[:,1]-verts[:,0], verts[:,2]-verts[:,0])*normals[:,0])<0:
            verts = verts[:,::-1]; normals = normals[:,::-1]
        p.add('recess', (verts.reshape(-1,3), normals.reshape(-1,3)))
    return p.result()


def floor_mats(interior):
    p = Parts()
    floor = Surface(interior, 0)
    for side in [-1, 1]:
        center = np.array([.335, side*.427, .26])
        outline = seat_roundrect(center, [1,0,0], [0,1,0], .565, .422, .025)
        # Concentric rings drape the carpet over the upward toe-board transition.
        points = [center]
        for radius in np.linspace(.05, 1, 20):
            points.extend(center+(outline-center)*radius)
        points = np.array([floor.at(q)[0]+[0,0,.004] for q in points])
        count = len(outline)
        faces = [(0, 1+i, 1+(i+1)%count) for i in range(count)]
        for j in range(19):
            for i in range(count):
                a=1+j*count+i; b=1+j*count+(i+1)%count
                faces.extend([(a,b+count,b),(a,a+count,b+count)])
        f = np.array(faces)
        tri = points[f]
        if np.cross(tri[0,1]-tri[0,0],tri[0,2]-tri[0,0])[2]<0:
            f = f[:,::-1]; tri = points[f]
        n = np.zeros_like(points)
        face_n = np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
        for i in range(3):
            np.add.at(n, f[:,i], face_n)
        n /= np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
        p.add('carpet', (tri.reshape(-1,3), n[f].reshape(-1,3)))
        # Bound edge: raised textile welt plus a fine inner stitch row.
        edge = points[-count:]
        p.add('webbing', tube(edge, .0032, closed=True, sides=10))
        stitch = center+(outline-center)*.973
        stitch = np.array([floor.at(q)[0]+[0,0,.005] for q in stitch])
        p.seam(stitch, closed=True, radius=.00055)
    return p.result()
