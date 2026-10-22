"""Visible rear fittings and running gear, measured from studio views 05/06/13.

Body coordinates, metres. These are exterior assemblies: do not clip them to the
body floor, since the low rear photograph looks up at their exposed lower faces.
"""
import numpy as np
import body as B
import details as D
from sdf import smin, smax, poly2d, smoothstep
from details import cap_x, rbox3
from body import _rbox2


def chain(X,Y,Z,points,r):
    d=np.full(np.shape(X),1.0)
    for a,b in zip(points[:-1],points[1:]):
        d=smin(d,cap_x(X,Y,Z,a,b,r),r*.25)
    return d


def disk(X,Y,Z,x,y,z,r,depth):
    return smax(np.sqrt((Y-y)**2+(Z-z)**2)-r,np.abs(X-x)-depth,.0015)


def screw(X,Y,Z,x,y,z,r=.003):
    head=disk(X,Y,Z,x,y,z,r,.0018)
    slot=np.maximum(np.abs(Y-y)-r*.7,np.abs(Z-z)-.0005)
    return np.maximum(head,-np.maximum(slot,X-x+.0015))


def fasteners(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    # Separate lamp screws on the perimeter, rather than floating on the lens cells.
    for y in [.300,.438,.582]:
        for side in [-1,1]:
            for z in [.652,.805]:
                d=np.minimum(d,screw(X,Y,Z,B.x_tail(z)+.006,side*y,z,.003))
    for y in [-.264,.264]:
        for z in [.654,.800]:
            d=np.minimum(d,screw(X,Y,Z,B.x_tail(z)+.010,y,z,.0028))
    for y in [-.44,-.30,-.16,.16,.30,.44]:
        z=.350
        d=np.minimum(d,screw(X,Y,Z,B.x_rear_valance(z,abs(y))-.002,y,z,.0032))
    for y in [-.115,.115]:
        for z in [D.PLATE_ZC-.057,D.PLATE_ZC+.057]:
            d=np.minimum(d,screw(X,Y,Z,B.x_tail(z)+.010,y,z,.0032))
    return d


def plate_border(X,Y,Z):
    ring=np.maximum(_rbox2(Y,Z-D.PLATE_ZC,.1545,.0735,.007),-_rbox2(Y,Z-D.PLATE_ZC,.150,.069,.005))
    return np.maximum(ring,np.abs(X-B.x_tail(Z)-.014)-.002)


def plate_lights(X,Y,Z):
    face=B.x_tail(Z)
    outer=rbox3(X-face,np.abs(Y),Z,(.007,.112,.811),(.020,.032,.012),.004)
    pocket=rbox3(X-face,np.abs(Y),Z,(-.004,.112,.799),(.012,.025,.004),.002)
    return smax(outer,-pocket,.001)


def plate_lenses(X,Y,Z):
    return rbox3(X-B.x_tail(Z),np.abs(Y),Z,(-.003,.112,.800),(.011,.025,.002),.001)


def bumper_seal(X,Y,Z):
    plan=B.rear_bumper_plan(X,Y,np.full(np.shape(X),B.RB_Z[1]))
    return np.maximum(np.abs(plan+.007)-.0025,np.abs(Z-.590)-.0018)


def apron_seal(X,Y,Z):
    yy=np.abs(Y)
    face=B.w_crease(X)-(B.z_crease(X)-Z)*np.tan(B.TUCK)-.005
    ring=np.sqrt((yy-face)**2+(Z-B.rear_lower_edge(X))**2)-.0022
    return np.maximum(ring,np.maximum(-1.94-X,X+1.58))


def timing_cover(X,Y,Z):
    outline=[(-.235,.49),(-.17,.56),(.14,.56),(.235,.47),(.215,.30),(.14,.240),(-.13,.235),(-.225,.285)]
    d=smax(poly2d(Y,Z,outline),np.abs(X+1.885)-.048,.008)
    # Raised cast webs and the perimeter flange on the rear-facing timing cover.
    edge=np.maximum(poly2d(Y,Z,outline)-.005,-poly2d(Y,Z,outline)-.006)
    d=np.minimum(d,np.maximum(edge,np.abs(X+1.934)-.005))
    for y,z in [(-.19,.32),(-.12,.28),(.13,.28),(.20,.33),(-.19,.49),(.18,.49)]:
        d=smin(d,cap_x(X,Y,Z,(-1.938,0,.315),(-1.938,y,z),.007),.002)
    return d


def sump_details(X,Y,Z):
    pan=rbox3(X,Y,Z,(-1.57,0,.214),(.21,.15,.010),.007)
    ribs=np.full(np.shape(X),1.0)
    for x in np.linspace(-1.76,-1.38,9):
        ribs=np.minimum(ribs,rbox3(X,Y,Z,(x,0,.231),(.004,.157,.022),.003))
    drain=disk(Z,X,Y,.200,-1.63,0,.012,.006)
    return np.minimum(pan,np.minimum(ribs,drain))


PULLEYS=[(0,.330,.079),(-.235,.330,.062),(.240,.380,.058)]


def pulleys(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    for y,z,r in PULLEYS:
        radial=np.sqrt((Y-y)**2+(Z-z)**2)
        plate=disk(X,Y,Z,-1.960,y,z,r-.004,.011)
        groove=np.sqrt((radial-r+.006)**2+(X+1.975)**2)-.003
        hub=disk(X,Y,Z,-1.977,y,z,.021,.010)
        d=np.minimum(d,np.minimum(plate,np.minimum(groove,hub)))
    return d


def belt(X,Y,Z):
    outline=[(-.295,.345),(-.265,.390),(.245,.435),(.295,.390),(.272,.342),(.050,.253),(-.050,.253),(-.275,.289)]
    rim=np.abs(poly2d(Y,Z,outline))-.0025
    return np.maximum(rim,np.abs(X+1.965)-.007)


def mechanical_bolts(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    for y,z in [(-.195,.32),(-.12,.275),(.13,.275),(.195,.33),(-.195,.49),(.18,.49),(-.12,.548),(.10,.548)]:
        d=np.minimum(d,disk(X,Y,Z,-1.943,y,z,.006,.004))
    for y,z,_ in PULLEYS:
        d=np.minimum(d,disk(X,Y,Z,-1.990,y,z,.008,.004))
    for y in [-.38,.38]:
        for z in [.255,.365]:
            d=np.minimum(d,disk(X,Y,Z,-1.858,y,z,.007,.005))
    return d


def frame(X,Y,Z):
    yy=np.abs(Y)
    rails=rbox3(X,yy,Z,(-1.44,.35,.265),(.36,.031,.037),.008)
    # Sloping engine-cradle side plates and mounting ears, visible beside the sump.
    plate=poly2d(X,Z,[(-1.88,.245),(-1.84,.44),(-1.72,.47),(-1.62,.27),(-1.67,.225)])
    plate=smax(plate,np.abs(yy-.365)-.024,.008)
    eye=np.sqrt((X+1.76)**2+(Z-.40)**2)-.024
    plate=smax(plate,-eye,.003)
    cross=rbox3(X,Y,Z,(-1.70,0,.228),(.023,.35,.018),.005)
    return np.minimum(rails,np.minimum(plate,cross))


def suspension(X,Y,Z):
    yy=np.abs(Y)
    points=[((-1.07,.30,.27),(-1.24,.71,.30)),((-1.49,.31,.28),(-1.24,.71,.30)),
            ((-.67,.64,.29),(-1.20,.70,.34)),((-1.13,.34,.47),(-1.21,.70,.47))]
    d=np.full(np.shape(X),1.0)
    for a,b in points:d=np.minimum(d,cap_x(X,yy,Z,a,b,.018))
    hub=rbox3(X,yy,Z,(B.X_RA,.70,B.R_R),(.055,.027,.075),.012)
    return np.minimum(d,hub)


def dampers(X,Y,Z):
    yy=np.abs(Y)
    body=cap_x(X,yy,Z,(-1.27,.625,.29),(-1.27,.625,.54),.024)
    lower=np.sqrt((Z-.29)**2+(X+1.27)**2)-.033
    eye=np.maximum(lower,np.abs(yy-.625)-.032)
    return np.minimum(body,eye)


def damper_rods(X,Y,Z):
    return cap_x(X,np.abs(Y),Z,(-1.27,.625,.50),(-1.27,.625,.685),.009)


def springs(X,Y,Z):
    dx=X+1.27;dy=np.abs(Y)-.625
    radius=np.sqrt(dx*dx+dy*dy);theta=np.arctan2(dy,dx)
    phase=(Z-.35)/.040-theta/(2*np.pi)
    dz=(phase-np.round(phase))*.040
    coil=np.sqrt((radius-.048)**2+dz*dz)-.005
    return np.maximum(coil,np.maximum(.35-Z,Z-.65))


def driveshafts(X,Y,Z):
    yy=np.abs(Y)
    shaft=cap_x(X,yy,Z,(B.X_RA,.18,B.R_R),(B.X_RA,.69,B.R_R),.018)
    radius=np.sqrt((X-B.X_RA)**2+(Z-B.R_R)**2)
    boot=np.full(np.shape(X),1.0)
    for yc in [.235,.625]:
        profile=.034+.009*np.cos((yy-yc)*np.pi/.010)**2
        boot=np.minimum(boot,np.maximum(radius-profile,np.abs(yy-yc)-.048))
    return np.minimum(shaft,boot)


# Two braided lines run from the left relief to fittings near the engine centre.
# A shorter return emerges through the opposite relief.
HOSES=[([(-1.98,.53,.365),(-2.00,.43,.337),(-1.99,.20,.327),(-1.98,.06,.340)],.011),
       ([(-1.975,.53,.347),(-1.985,.43,.309),(-1.975,.20,.299),(-1.96,.06,.307)],.012),
       ([(-1.98,-.53,.363),(-1.97,-.46,.336),(-1.90,-.40,.318),(-1.89,-.29,.305)],.013)]


def braided_hoses(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    for pts,r in HOSES:d=np.minimum(d,chain(X,Y,Z,pts,r))
    return d


def hose_fittings(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    for x,y,z in [(-1.98,.06,.340),(-1.96,.06,.307),(-1.89,-.29,.305)]:
        d=np.minimum(d,disk(X,Y,Z,x,y,z,.020,.014))
    return d


def exhaust_liners(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    for y in B.EXHAUST_Y:
        rad=np.sqrt((Y-y)**2+(Z-B.EXHAUST_Z)**2)
        d=np.minimum(d,np.maximum(np.abs(rad-.0305)-.0017,np.maximum(-2.112-X,X+1.99)))
    return d


def louvre_fasteners(X,Y,Z):
    d=np.full(np.shape(X),1.0)
    for x in [-.94,-1.30,-1.67,-1.88]:
        width=float(np.interp(x,*B._LID_W))-.016
        z=float(B.z_fb(np.array(x)))+.001
        for y in [-width,width]:
            d=np.minimum(d,disk(Z,X,Y,z,x,y,.003,.002))
    return d


def logo_border(X,Y,Z):
    rim=np.maximum(_rbox2(Y-D.DEL_YC,Z-D.DEL_ZC,.225,.033,.003),
                   -_rbox2(Y-D.DEL_YC,Z-D.DEL_ZC,.223,.031,.002))
    return np.maximum(rim,np.abs(X-B.x_rbump(np.abs(Y))+.0007)-.0012)


def lid_seal(X,Y,Z):
    edge=poly2d(X,Y,B.LID_POLY)+.001
    return np.maximum(np.abs(edge)-.003,np.abs(B.d_fastback(X,np.abs(Y),Z)+.004)-.003)
