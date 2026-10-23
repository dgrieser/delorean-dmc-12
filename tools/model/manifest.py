"""Scene manifest: which NPZ part goes to which material / parent node, plus pivots.

Shared by the Blender assembler. Frame: Blender (X fwd, Y left, Z up)."""
import body as B
import details as D
import interior as I
import numpy as np

# material name -> (base rgb (linear), metallic, roughness, extra)
MATERIALS = {
    'Stainless':        ((0.60, 0.60, 0.60), 1.0, 0.30, {}),
    'Urethane':         ((0.035, 0.037, 0.040), 0.0, 0.55, {}),
    'AirDam':           ((0.022, 0.023, 0.025), 0.0, 0.32, {}),
    'Rubber':           ((0.012, 0.012, 0.012), 0.0, 0.70, {}),
    'PlasticBlack':     ((0.015, 0.015, 0.016), 0.0, 0.45, {}),
    'PlasticMatte':     ((0.020, 0.020, 0.021), 0.0, 0.85, {}),
    'Louvre':           ((0.045, 0.048, 0.050), 0.0, 0.48, {}),
    'Glass':            ((0.80, 0.84, 0.82), 0.0, 0.02, {'alpha': 0.25}),
    'Chrome':           ((0.90, 0.90, 0.90), 1.0, 0.06, {}),
    'MirrorGlass':      ((0.85, 0.86, 0.88), 1.0, 0.02, {}),
    'BadgeAlu':         ((0.75, 0.76, 0.78), 1.0, 0.22, {}),
    'Lamp_HeadLens':    ((0.90, 0.92, 0.95), 0.0, 0.03, {'alpha': 0.35}),
    'Lamp_Bulb_Hi':     ((0.90, 0.90, 0.88), 0.0, 0.2, {}),
    'Lamp_Bulb_Lo':     ((0.90, 0.90, 0.88), 0.0, 0.2, {}),
    'Lamp_TurnFront':   ((0.90, 0.35, 0.02), 0.0, 0.12, {'alpha': 0.85}),
    'Lamp_MarkerFront': ((0.90, 0.35, 0.02), 0.0, 0.12, {'alpha': 0.85}),
    'Lamp_MarkerRear':  ((0.60, 0.02, 0.02), 0.0, 0.12, {'alpha': 0.85}),
    'Lamp_TurnRear':    ((0.90, 0.35, 0.02), 0.0, 0.12, {'alpha': 0.85}),
    'Lamp_Tail':        ((0.55, 0.01, 0.01), 0.0, 0.10, {'alpha': 0.85}),
    'Lamp_Reverse':     ((0.85, 0.85, 0.85), 0.0, 0.10, {'alpha': 0.6}),
    'Exhaust':          ((0.55, 0.55, 0.56), 1.0, 0.35, {}),
    'Leather':          ((0.20, 0.205, 0.21), 0.0, 0.55, {}),
    'LeatherBlack':     ((0.025, 0.025, 0.026), 0.0, 0.5, {}),
    'Vinyl':            ((0.19, 0.195, 0.20), 0.0, 0.6, {}),
    'Headliner':        ((0.30, 0.30, 0.29), 0.0, 0.95, {}),
    'Carpet':           ((0.13, 0.13, 0.135), 0.0, 1.0, {}),
    'Lamp_Courtesy':    ((0.6, 0.05, 0.03), 0.0, 0.2, {'alpha': 0.85}),
    'PedalRubber':      ((0.02, 0.02, 0.02), 0.0, 0.8, {}),
    'MetalDark':        ((0.08, 0.08, 0.085), 1.0, 0.45, {}),
    'EngineAlu':        ((0.42, 0.42, 0.41), 1.0, 0.55, {}),
    'CastAlu':          ((0.62, 0.62, 0.60), 1.0, 0.42, {}),
    'RustyIron':        ((0.18, 0.08, 0.04), 0.3, 0.85, {}),
    'Decal_Airbox':     ((0.02, 0.02, 0.02), 0.0, 0.4, {}),
    'Decal_Jump':       ((0.02, 0.02, 0.02), 0.0, 0.5, {}),
    'Decal_Plate':      ((0.80, 0.80, 0.80), 0.0, 0.4, {}),
    'GrilleMesh':       ((0.30, 0.30, 0.30), 1.0, 0.5, {}),
    'Lamp_TurnRefl':    ((0.85, 0.40, 0.06), 1.0, 0.25, {}),
    'Lamp_HeadRefl':    ((0.90, 0.90, 0.90), 1.0, 0.32, {}),
    'Radiator':         ((0.05, 0.05, 0.05), 0.5, 0.6, {}),
    'RadiatorFrame':    ((0.16, 0.17, 0.18), 0.5, 0.5, {}),
    'RedPaint':         ((0.45, 0.02, 0.02), 0.0, 0.35, {}),
    'Tyre_Rubber':      ((0.018, 0.018, 0.019), 0.0, 0.86, {}),
    'DoorEdge':         ((0.03, 0.03, 0.032), 0.3, 0.55, {}),
}

MATERIALS.update({
    'FasciaPaint': ((.52,.53,.54),.95,.28,{}),
    'BumperLetter': ((.044,.048,.067),0,.42,{}),
    'TailFrame': ((.040,.043,.046),.05,.38,{}),
    'Lamp_RearRefl': ((.65,.64,.60),1.0,.27,{}),
    'FrameCoat': ((.085,.090,.092),.25,.62,{}),
    'BraidedMetal': ((.36,.35,.32),.80,.58,{}),
    'AnodizedBlue': ((.018,.12,.20),.75,.30,{}),
    'PlateLight': ((.72,.65,.46),0,.25,{}),
})

# part file -> (material, parent, uv)
# parents: Body, Door_L, Door_R, Hood, EngineLid, FuelFlap
PARTS = {
    'body': ('Stainless', 'Body', 'brush'),
    'door_L': ('Stainless', 'Door_L', 'brush'),
    'door_R': ('Stainless', 'Door_R', 'brush'),
    'hood': ('Stainless', 'Hood', 'brush'),
    # Dark nose finish and smooth satin rear fascia, separate from the stainless body.
    'nose': ('Stainless', 'Body', 'brush'),
    'tail': ('FasciaPaint', 'Body', 'box'),
    'bumper_f': ('Urethane', 'Body', 'box'),
    'bumper_r': ('Urethane', 'Body', 'box'),
    'rocker': ('PlasticMatte', 'Body', 'box'),
    # the rear valance is the bumpers' graphite grey; the air dam is a darker, near-black satin
    # (front photo: ~10 of 255 face-on against the bumper's ~55)
    'airdam': ('AirDam', 'Body', 'box'),
    'rvalance': ('Urethane', 'Body', 'box'),
    'fstrip': ('Stainless', 'Body', 'brush'),
    'door_handle_L': ('PlasticBlack', 'Door_L', 'box'),
    'door_handle_R': ('PlasticBlack', 'Door_R', 'box'),
    'bumper_letters': ('BumperLetter', 'Body', 'box'),
    'glass_windshield': ('Glass', 'Body', 'box'),
    'gasket_windshield': ('Rubber', 'Body', 'box'),
    'frit_windshield': ('PlasticBlack', 'Body', 'box'),
    'glass_door_L': ('Glass', 'Door_L', 'box'),
    'glass_door_R': ('Glass', 'Door_R', 'box'),
    'gasket_door_L': ('Rubber', 'Door_L', 'box'),
    'glass_toll_L': ('Glass', 'Door_L', 'box'),
    'glass_toll_R': ('Glass', 'Door_R', 'box'),
    'toll_frame_L': ('Rubber', 'Door_L', 'box'),
    'toll_frame_R': ('Rubber', 'Door_R', 'box'),
    'gasket_door_R': ('Rubber', 'Door_R', 'box'),
    'glass_quarter_L': ('Glass', 'Body', 'box'),
    'glass_quarter_R': ('Glass', 'Body', 'box'),
    'gasket_quarter_L': ('Rubber', 'Body', 'box'),
    'gasket_quarter_R': ('Rubber', 'Body', 'box'),
    'strip_fender_L': ('Rubber', 'Body', 'box'),
    'strip_fender_R': ('Rubber', 'Body', 'box'),
    'strip_quarter_L': ('Rubber', 'Body', 'box'),
    'strip_quarter_R': ('Rubber', 'Body', 'box'),
    'strip_rearcorner_L': ('Rubber', 'Body', 'box'),
    'strip_nose_L': ('Rubber', 'Body', 'box'),
    'strip_nose_R': ('Rubber', 'Body', 'box'),
    'strip_tip_L': ('Rubber', 'Body', 'box'),
    'strip_tip_R': ('Rubber', 'Body', 'box'),
    'strip_rearcorner_R': ('Rubber', 'Body', 'box'),
    'strip_door_L': ('Rubber', 'Door_L', 'box'),
    'strip_door_R': ('Rubber', 'Door_R', 'box'),
    'hl_lens_Hi': ('Lamp_HeadLens', 'Body', 'lens'),
    'hl_lens_Lo': ('Lamp_HeadLens', 'Body', 'lens'),
    'hl_refl_Hi': ('Lamp_HeadRefl', 'Body', 'box'),
    'hl_refl_Lo': ('Lamp_HeadRefl', 'Body', 'box'),
    'hl_bulb_Hi': ('Lamp_Bulb_Hi', 'Body', 'box'),
    'hl_bulb_Lo': ('Lamp_Bulb_Lo', 'Body', 'box'),
    'hl_bezel_Hi': ('PlasticBlack', 'Body', 'box'),
    'hl_bezel_Lo': ('PlasticBlack', 'Body', 'box'),
    'hl_rim_Hi': ('Chrome', 'Body', 'box'),
    'hl_rim_Lo': ('Chrome', 'Body', 'box'),
    'grille': ('PlasticBlack', 'Body', 'box'),
    'badge_dmc': ('BadgeAlu', 'Body', 'box'),
    'turn_front': ('Lamp_TurnFront', 'Body', 'lens'),
    'turn_housing': ('PlasticBlack', 'Body', 'box'),
    'turn_bezel': ('PlasticMatte', 'Body', 'box'),
    'turn_refl': ('Lamp_TurnRefl', 'Body', 'box'),
    'intake_mesh': ('GrilleMesh', 'Body', 'lens'),
    'radiator': ('Radiator', 'Body', 'lens'),
    'intake_supports': ('RadiatorFrame', 'Body', 'box'),
    'marker_front': ('Lamp_MarkerFront', 'Body', 'lens'),
    'marker_rear': ('Lamp_MarkerRear', 'Body', 'lens'),
    'tl_turn': ('Lamp_TurnRear', 'Body', 'lens'),
    'tl_tail': ('Lamp_Tail', 'Body', 'lens'),
    'tl_rev': ('Lamp_Reverse', 'Body', 'lens'),
    'tl_housing': ('TailFrame', 'Body', 'box'),
    'plate': ('Decal_Plate', 'Body', 'lens'),
    'lid_frame': ('Louvre', 'EngineLid', 'box'),
    'lid_slats': ('Louvre', 'EngineLid', 'box'),
    'lid_under': ('PlasticMatte', 'EngineLid', 'box'),
    'quarter_vent_frame': ('PlasticBlack', 'Body', 'box'),
    'quarter_vent_fins': ('TailFrame', 'Body', 'box'),
    'quarter_vent_back': ('PlasticMatte', 'Body', 'box'),
    'bpillar_vent': ('PlasticBlack', 'Body', 'box'),
    'mirror_L': ('PlasticBlack', 'Door_L', 'box'),
    'mirror_R': ('PlasticBlack', 'Door_R', 'box'),
    'mirror_glass_L': ('MirrorGlass', 'Door_L', 'box'),
    'mirror_glass_R': ('MirrorGlass', 'Door_R', 'box'),
    'liner_f': ('PlasticMatte', 'Body', 'box'),
    'liner_r': ('PlasticMatte', 'Body', 'box'),
    'underbody': ('PlasticMatte', 'Body', 'box'),
    'rear_frame': ('FrameCoat', 'Body', 'box'),
    'driveshafts': ('MetalDark', 'Body', 'box'),
    'exhaust': ('Exhaust', 'Body', 'box'),
    'rear_fasteners': ('MetalDark', 'Body', 'box'),
    'plate_lights': ('PlasticBlack', 'Body', 'box'),
    'rear_slot_back': ('PlasticBlack', 'Body', 'box'),
    'sill_details': ('Urethane', 'Body', 'box'),
    'antenna': ('Chrome', 'Body', 'box'),
    'cowl_vent': ('PlasticBlack', 'Body', 'box'),
    'antenna_base': ('PlasticBlack', 'Body', 'box'),
}

PARTS.update({
    'rear_band': ('BadgeAlu','Body','box'),
    'tl_bezel': ('TailFrame','Body','box'),
    'tl_gasket': ('Rubber','Body','box'),
    'tl_reflectors': ('Lamp_RearRefl','Body','box'),
    'plate_border': ('BadgeAlu','Body','box'),
    'plate_lenses': ('PlateLight','Body','box'),
    'rear_lower_fasteners': ('BadgeAlu','Body','box'),
    'rear_bumper_seal': ('Rubber','Body','box'),
    'rear_apron_seal': ('Rubber','Body','box'),
    'rear_timing_cover': ('CastAlu','Body','box'),
    'rear_sump': ('EngineAlu','Body','box'),
    'rear_pulleys': ('MetalDark','Body','box'),
    'rear_belt': ('Rubber','Body','box'),
    'rear_mechanical_bolts': ('BadgeAlu','Body','box'),
    'rear_suspension': ('MetalDark','Body','box'),
    'rear_dampers': ('FrameCoat','Body','box'),
    'rear_damper_rods': ('Chrome','Body','box'),
    'rear_springs': ('MetalDark','Body','box'),
    'rear_hoses': ('BraidedMetal','Body','box'),
    'rear_hose_fittings': ('AnodizedBlue','Body','box'),
    'exhaust_liners': ('PlasticMatte','Body','box'),
    'rear_logo_border': ('BumperLetter','Body','box'),
    'lid_fasteners': ('MetalDark','EngineLid','box'),
    'lid_seal': ('Rubber','EngineLid','box'),
})

INTERIOR = {
    'seat_L': ('Leather', 'Body'), 'seat_R': ('Leather', 'Body'),
    'seatbase_L': ('PlasticBlack', 'Body'), 'seatbase_R': ('PlasticBlack', 'Body'),
    'dash': ('Vinyl', 'Body'), 'stack': ('Vinyl', 'Body'), 'stack_inserts': ('PlasticBlack', 'Body'),
    'end_vents': ('PlasticBlack', 'Body'), 'console': ('Vinyl', 'Body'), 'console_inserts': ('PlasticBlack', 'Body'),
    'column': ('PlasticBlack', 'Body'),
    'door_card_L': ('Leather', 'Door_L'), 'door_card_R': ('Leather', 'Door_R'),
    'door_liner_L': ('Headliner', 'Door_L'), 'door_liner_R': ('Headliner', 'Door_R'),
    # the door's inner frame is bare stainless on the reference car (the aperture seals stay black)
    'door_edge_L': ('Stainless', 'Door_L'), 'door_edge_R': ('Stainless', 'Door_R'),
    'jamb_L': ('DoorEdge', 'Body'), 'jamb_R': ('DoorEdge', 'Body'),
    'door_seal_L': ('Rubber', 'Body'), 'door_seal_R': ('Rubber', 'Body'),
    'body_trim': ('Headliner', 'Body'), 'carpet': ('Carpet', 'Body'), 'sills': ('Carpet', 'Body'),
    'sill_plates': ('Rubber', 'Body'), 'parcel': ('Carpet', 'Body'), 'rear_window': ('Glass', 'Body'),
    'bulkhead': ('Vinyl', 'Body'), 'rear_mirror': ('PlasticBlack', 'Body'),
    'buckles': ('PlasticBlack', 'Body'), 'belt_buttons': ('Lamp_Courtesy', 'Body'),
    'door_strap_L': ('Leather', 'Door_L'), 'door_strap_R': ('Leather', 'Door_R'),
    'courtesy_L': ('Lamp_Courtesy', 'Door_L'), 'courtesy_R': ('Lamp_Courtesy', 'Door_R'),
    # local parts (vertices in pivot frame)
    'steering_wheel': ('LeatherBlack', 'SteeringWheel', 'local'),
    'pedal_Clutch': ('PedalRubber', 'Pedal_Clutch', 'local'), 'pedal_Brake': ('PedalRubber', 'Pedal_Brake', 'local'),
    'pedal_Gas': ('PedalRubber', 'Pedal_Gas', 'local'),
    'shifter_lever': ('MetalDark', 'Shifter', 'local'), 'shifter_knob': ('LeatherBlack', 'Shifter', 'local'),
    'shift_boot': ('LeatherBlack', 'ShifterBase', 'local'),
    'handbrake': ('PlasticBlack', 'Handbrake', 'local'),
}
for tag in ['L', 'R']:
    for name, material in [('door_latches', 'BadgeAlu'), ('door_lamp_bezels', 'PlasticBlack'),
                           ('door_speaker', 'PlasticBlack'), ('courtesy_rear', 'Lamp_MarkerRear')]:
        INTERIOR[f'{name}_{tag}'] = (material, f'Door_{tag}')

INTERIOR.update({
    'eng_block': ('EngineAlu', 'Body'), 'eng_covers': ('CastAlu', 'Body'), 'eng_intake': ('CastAlu', 'Body'),
    'eng_airbox': ('PlasticBlack', 'Body'), 'eng_decal': ('Decal_Airbox', 'Body', 'lens'), 'eng_exhaust': ('Exhaust', 'Body'),
    'eng_tank': ('Exhaust', 'Body'), 'eng_aux': ('CastAlu', 'Body'), 'eng_battery': ('PlasticBlack', 'Body'),
    'eng_hoses': ('Rubber', 'Body'), 'bay_tub': ('PlasticMatte', 'Body'), 'bay_panel': ('Decal_Jump', 'Body', 'lens'),
    'frunk_tub': ('Carpet', 'Body'), 'fuel_tank': ('PlasticMatte', 'Body'), 'spare_tyre': ('Tyre_Rubber', 'Body'),
    'spare_rim': ('MetalDark', 'Body'), 'extinguisher': ('RedPaint', 'Body'),
})
for k, v in INTERIOR.items():
    PARTS[k] = (v[0], v[1], v[2] if len(v) > 2 else 'box')


def _rot(lx, ly, lz):
    return [list(map(float, lx)), list(map(float, ly)), list(map(float, lz))]


c25, s25 = np.cos(I.COL_ANG), np.sin(I.COL_ANG)
c14, s14 = np.cos(14 * np.pi / 180), np.sin(14 * np.pi / 180)
c20, s20 = np.cos(20 * np.pi / 180), np.sin(20 * np.pi / 180)

# pivots: name -> (location, parent) ; app rotates them (see web/js/car.js)
PIVOTS = {
    'Door_L': ((0.0, B.SPINE_Y - 0.012, 1.118), 'Body'),
    'Door_R': ((0.0, -(B.SPINE_Y - 0.012), 1.118), 'Body'),
    'Hood': ((0.79, 0.0, 0.842), 'Body'),
    'EngineLid': ((D.LID_HINGE[0], 0.0, D.LID_HINGE[1]), 'Body'),
    'Body': ((0.0, 0.0, 0.0), 'Car'),
    'SteeringWheel': (tuple(I.SW_CENTER), 'Body', _rot((s25, 0, c25), (0, 1, 0), (-c25, 0, s25))),
    'Pedal_Clutch': ((I.PEDAL_PIVOT_X, I.PEDALS['Clutch'][0], I.PEDAL_PIVOT_Z), 'Body'),
    'Pedal_Brake': ((I.PEDAL_PIVOT_X, I.PEDALS['Brake'][0], I.PEDAL_PIVOT_Z), 'Body'),
    'Pedal_Gas': ((I.PEDAL_PIVOT_X, I.PEDALS['Gas'][0], I.PEDAL_PIVOT_Z), 'Body'),
    'ShifterBase': ((0.215, 0.0, 0.428), 'Body'),
    'Shifter': ((0.215, 0.0, 0.428), 'Body'),
    'Handbrake': ((-0.20, 0.648, 0.305), 'Body', _rot((c20, 0, s20), (0, 1, 0), (-s20, 0, c20))),
    'GaugeFace': (tuple(map(float, I.GAUGE_FACE)), 'Body', _rot((0, -1, 0), (s14, 0, c14), (-c14, 0, s14))),
    'ClockFace': ((-0.005, 0.0, 0.4405), 'Body'),
    'RadioFace': ((0.492, 0.0, 0.655), 'Body', _rot((0, -1, 0), (0, 0, 1), (-1, 0, 0))),
}

# empties marking light sources (for the app): name -> location
MARKERS = {
    'LP_HeadLo_L': (1.97, 0.626, 0.607), 'LP_HeadLo_R': (1.97, -0.626, 0.607),
    'LP_HeadHi_L': (1.97, 0.444, 0.607), 'LP_HeadHi_R': (1.97, -0.444, 0.607),
    'LP_TurnF_L': (2.09, B.TURN_Y, B.TURN_Z), 'LP_TurnF_R': (2.09, -B.TURN_Y, B.TURN_Z),
    'LP_TurnR_L': (-2.04, 0.665, 0.727), 'LP_TurnR_R': (-2.04, -0.665, 0.727),
    'LP_Tail_L': (-2.04, 0.475, 0.727), 'LP_Tail_R': (-2.04, -0.475, 0.727),
    'LP_Rev_L': (-2.04, 0.31, 0.727), 'LP_Rev_R': (-2.04, -0.31, 0.727),
    'WheelPos_FL': (B.X_FA, B.TRACK_F / 2, B.R_F), 'WheelPos_FR': (B.X_FA, -B.TRACK_F / 2, B.R_F),
    'WheelPos_RL': (B.X_RA, B.TRACK_R / 2, B.R_R), 'WheelPos_RR': (B.X_RA, -B.TRACK_R / 2, B.R_R),
}


if __name__ == '__main__':
    import json, os
    out = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
    data = {'windshield': {'bx': float(B.WS_B[0]), 'bz': float(B.WS_B[1]), 'nx': float(B.WS_N[0]), 'nz': float(B.WS_N[1]), 'wrap': B.WS_WRAP},
            'materials': {k: {'rgb': v[0], 'metallic': v[1], 'roughness': v[2], **v[3]} for k, v in MATERIALS.items()},
            'parts': {k: {'material': v[0], 'parent': v[1], 'uv': v[2]} for k, v in PARTS.items()},
            'pivots': {k: {'loc': [float(x) for x in v[0]], 'parent': v[1], 'rot': v[2] if len(v) > 2 else None} for k, v in PIVOTS.items()},
            'markers': {k: [float(x) for x in v] for k, v in MARKERS.items()},
            'stance': float(B.STANCE)}
    json.dump(data, open(f'{out}/manifest.json', 'w'), indent=1)
    print('manifest written', len(data['parts']), 'parts')
