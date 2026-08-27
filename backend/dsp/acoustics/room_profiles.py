from typing import Dict, Any, Tuple

# Base room profiles for procedural generation
# Each profile specifies standard dimensions [x, y, z] and materials
# RT60 targets will guide absorption, or we explicitly define absorption.
# Since we shouldn't blindly rely on ShoeBox.from_rt60, we will define ranges
# for dimensions and absorption coefficients.

ROOM_PROFILES = {
    "auditorium": {
        "dim_ranges": {
            "x": (20.0, 30.0),
            "y": (30.0, 45.0),
            "z": (8.0, 15.0)
        },
        "target_rt60_range": (1.5, 2.5),
        "max_order": 10
    },
    "hall": {
        "dim_ranges": {
            "x": (15.0, 25.0),
            "y": (25.0, 40.0),
            "z": (7.0, 12.0)
        },
        "target_rt60_range": (1.0, 1.8),
        "max_order": 10
    },
    "classroom": {
        "dim_ranges": {
            "x": (6.0, 10.0),
            "y": (8.0, 12.0),
            "z": (3.0, 4.0)
        },
        "target_rt60_range": (0.4, 0.8),
        "max_order": 6
    },
    "office": {
        "dim_ranges": {
            "x": (3.0, 6.0),
            "y": (4.0, 8.0),
            "z": (2.5, 3.5)
        },
        "target_rt60_range": (0.2, 0.5),
        "max_order": 4
    },
    "conference_room": {
        "dim_ranges": {
            "x": (5.0, 8.0),
            "y": (7.0, 10.0),
            "z": (2.8, 3.8)
        },
        "target_rt60_range": (0.3, 0.6),
        "max_order": 5
    },
    "cathedral": {
        "dim_ranges": {
            "x": (25.0, 40.0),
            "y": (40.0, 80.0),
            "z": (15.0, 30.0)
        },
        "target_rt60_range": (3.0, 6.0),
        "max_order": 12
    }
}
