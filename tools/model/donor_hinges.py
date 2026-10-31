"""Door attachment hardware in the donor's body coordinates (X forward, Z up)."""
from collections import defaultdict
import numpy as np
from donor_doors import plate, end_frame

HINGE_Z = 1.121
HINGE_SLOPE = .04
BODY_BALL = np.array([-.700, .58, 1.055])
DOOR_BALL = np.array([-.697, .31, 1.093])


def cylinder(a, b, radius, segments=16):
    a,b=np.asarray(a,float),np.asarray(b,float)
    axis=b-a;axis/=np.linalg.norm(axis)
    u=np.cross(axis,[0,0,1] if abs(axis[2])<.9 else [0,1,0]);u/=np.linalg.norm(u)
    v=np.cross(axis,u)
    angle=np.arange(segments)*2*np.pi/segments
    ring=np.cos(angle)[:,None]*u+np.sin(angle)[:,None]*v
    pts=np.concatenate([a+ring*radius,b+ring*radius,[a,b]])
    normals=np.concatenate([ring,ring,[-axis,axis]])
    faces=[];cap=[]
    for i in range(segments):
        j=(i+1)%segments
        faces.extend([(i,j,j+segments),(i,j+segments,i+segments)])
        cap.extend([(2*segments,j,i),(2*segments+1,i+segments,j+segments)])
    faces=np.array(faces);cap=np.array(cap)
    return (np.concatenate([pts[faces].reshape(-1,3),pts[cap].reshape(-1,3)]),
            np.concatenate([normals[faces].reshape(-1,3),np.repeat(np.tile([-axis,axis],(segments,1)),3,axis=0)]))


def attachments(skin, side):
    """Two hinges share the rig axis; strut studs meet actual mounting plates."""
    parts=defaultdict(list)
    def add(parent,mat,mesh):parts[(parent,mat)].append(mesh)
    def slab(parent,mat,c,u,v,w,h,d,r=.003):add(parent,mat,plate(np.array(c),u,v,w,h,d,r))
    def bolt(parent,c,n,r=.004):
        c,n=np.array(c),np.array(n)
        add(parent,'steel',cylinder(c,c+n*.003,r,6))
    # Fixed roof channel and hinge leaves attach to the central spine.
    hinge_axis=np.array([1,0,-HINGE_SLOPE]);hinge_axis/=np.linalg.norm(hinge_axis)
    slab('Body','dark',[-.36,.101,HINGE_Z+.36*HINGE_SLOPE-.014],hinge_axis,[0,1,0],.72,.064,.008)
    for x in [-.10,-.64]:
        z=HINGE_Z-x*HINGE_SLOPE
        slab('Body','steel',[x,.095,z-.010],hinge_axis,[0,1,0],.094,.080,.005)
        # The moving leaf sits below the liner, with a bent web up to the pin.
        # A flat leaf at pin height cut through the upholstered edge.
        slab('Door','steel',[x,.180,z-.038],hinge_axis,[0,1,0],.080,.070,.005)
        web=np.array([0,.028,-.038]);web/=np.linalg.norm(web)
        slab('Door','steel',[x,.149,z-.019],hinge_axis,web,.080,.048,.004)
        # Interleaved knuckles are centred on the exact door pivot axis.
        for i in range(5):
            lo=x-.05+i*.020
            add('Body' if i%2==0 else 'Door','steel',cylinder([lo,.135,HINGE_Z-lo*HINGE_SLOPE],[lo+.018,.135,HINGE_Z-(lo+.018)*HINGE_SLOPE],.007))
        add('Body','dark',cylinder([x-.055,.135,z+.055*HINGE_SLOPE],[x+.055,.135,z-.055*HINGE_SLOPE],.003))
        for dx in [-.028,.028]:
            bolt('Body',[x+dx,.078,z-.006-dx*HINGE_SLOPE],[0,0,1])
            bolt('Door',[x+dx,.196,z-.041-dx*HINGE_SLOPE],[0,0,-1])
    # Straight bound edge closes the upholstered panel onto the door flange.
    slab('Door','dark',[-.35,.206,HINGE_Z+.35*HINGE_SLOPE-.030],
         hinge_axis,[0,1,0],.655,.036,.009,.004)
    # Torsion-bar representation along the hinge axis, under the roof channel.
    add('Body','dark',cylinder([-.71,.119,HINGE_Z+.71*HINGE_SLOPE-.01],[-.025,.119,HINGE_Z+.025*HINGE_SLOPE-.01],.0045))
    # Fixed bracket is fastened across the rear jamb, not left inside the sail.
    slab('Body','steel',[-.721,.58,1.055],[0,1,0],[0,0,1],.045,.060,.006)
    slab('Body','steel',[-.737,.58,1.027],[1,0,0],[0,1,0],.038,.045,.006)
    add('Body','steel',cylinder([-.718,.58,1.055],BODY_BALL,.006))
    for y in [.567,.593]:bolt('Body',[-.717,y,1.074],[1,0,0])
    # Moving bracket reaches down from the inner door roof to its ball stud.
    slab('Door','steel',[-.698,.31,1.122],[1,0,0],[0,1,0],.035,.060,.005)
    slab('Door','steel',[-.704,.31,1.104],[0,1,0],[0,0,1],.048,.038,.006)
    add('Door','steel',cylinder([-.704,.31,1.093],DOOR_BALL,.006))
    for y in [.286,.334]:bolt('Door',[-.698,y,1.118],[0,0,-1])
    # Door frame fasteners on the exposed front/rear roof returns.
    for front in [True,False]:
        for z in [.91,1.01,1.08]:
            c,u,v=end_frame(skin,z,front)
            n=np.cross(u,v)
            bolt('Door',c+n*.002,n,.004)
    # Mirror complete assemblies, including winding, for the opposite side.
    result={}
    for key,pieces in parts.items():
        v=np.concatenate([v for v,n in pieces]);n=np.concatenate([n for v,n in pieces])
        if side<0:
            v=(v*[1,-1,1]).reshape(-1,3,3)[:,::-1].reshape(-1,3)
            n=(n*[1,-1,1]).reshape(-1,3,3)[:,::-1].reshape(-1,3)
        result[key]=(v,n)
    return result
