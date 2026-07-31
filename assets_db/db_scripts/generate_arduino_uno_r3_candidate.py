"""Generate candidate metadata for the current Arduino UNO R3 GLB.

The coordinates below are measured from the exported GLB.  This script does
not modify the GLB and deliberately keeps unresolved catalog/geometry issues
visible instead of marking the asset approved.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GLB_PATH = REPO_ROOT / "assets_db/3d_models/glb/arduino-uno-r3.glb"
OUTPUT_PATH = (
    REPO_ROOT
    / "assets_db/3d_models/component_metadata/candidates/arduino-uno-r3"
    / "yoohyeon93-blender-empty.json"
)

POSITIONS = {
    "pin_3V3": [0.002720109, 0.018686056, 0.021553388],
    "pin_5V": [0.005260109, 0.018686056, 0.021553388],
    "pin_A0": [0.018027131, 0.018686056, 0.02138048],
    "pin_A1": [0.02056713, 0.018686056, 0.02138048],
    "pin_A2": [0.02310713, 0.018686056, 0.02138048],
    "pin_A3": [0.02564713, 0.018686056, 0.02138048],
    "pin_A4": [0.02818713, 0.018686056, 0.02138048],
    "pin_A5": [0.03075102, 0.018686056, 0.021308808],
    "pin_AREF": [-0.009190381, 0.018686056, -0.026039539],
    "pin_D0": [0.026848398, 0.018723954, -0.026192384],
    "pin_D1": [0.025241897, 0.018686056, -0.026293723],
    "pin_D10": [0.003509618, 0.018686056, -0.026039539],
    "pin_D11": [0.000969619, 0.018686056, -0.026039539],
    "pin_D12": [-0.001570381, 0.018686056, -0.026039539],
    "pin_D13": [-0.004110381, 0.018686056, -0.026039539],
    "pin_D2": [0.023141894, 0.018686056, -0.026293723],
    "pin_D3": [0.021041896, 0.018686056, -0.026293723],
    "pin_D4": [0.018941894, 0.018686056, -0.026293723],
    "pin_D5": [0.016841896, 0.018686056, -0.026293723],
    "pin_D6": [0.014741895, 0.018686056, -0.026293723],
    "pin_D7": [0.012641895, 0.018686056, -0.026293723],
    "pin_D8": [0.008490537, 0.018686056, -0.026039539],
    "pin_D9": [0.006049618, 0.018686056, -0.026039539],
    "pin_GND_1": [-0.006650381, 0.018686056, -0.026039539],
    "pin_GND_2": [0.007800109, 0.018686056, 0.021553388],
    "pin_GND_3": [0.010340109, 0.018686056, 0.021553388],
    "pin_ICSP_MCU_R1C1": [0.031802371, 0.019950001, -0.007293585],
    "pin_ICSP_MCU_R1C2": [0.03370237, 0.019950001, -0.007293585],
    "pin_ICSP_MCU_R2C1": [0.031802371, 0.019950001, -0.005233585],
    "pin_ICSP_MCU_R2C2": [0.03370237, 0.019950001, -0.005233585],
    "pin_ICSP_MCU_R3C1": [0.031802371, 0.019950001, -0.003173585],
    "pin_ICSP_MCU_R3C2": [0.03370237, 0.019950001, -0.003173585],
    "pin_ICSP_USB_R1C1": [-0.017195754, 0.019950181, -0.022128405],
    "pin_ICSP_USB_R1C2": [-0.015205754, 0.019950181, -0.022128405],
    "pin_ICSP_USB_R1C3": [-0.013215754, 0.019950181, -0.022128405],
    "pin_ICSP_USB_R2C1": [-0.017195754, 0.019950181, -0.020128405],
    "pin_ICSP_USB_R2C2": [-0.015205754, 0.019950181, -0.020128405],
    "pin_ICSP_USB_R2C3": [-0.013215754, 0.019950181, -0.020128405],
    "pin_IOREF": [-0.002359891, 0.018686056, 0.021553388],
    "pin_NC": [-0.004899891, 0.018686056, 0.021553388],
    "pin_RESET": [0.000180109, 0.018686056, 0.021553388],
    "pin_VIN": [0.01357295, 0.018686056, 0.02160117],
}

PIN_KEY_OVERRIDES = {
    "pin_GND_1": "GND_D",
    "pin_GND_2": "GND_P1",
    "pin_GND_3": "GND_P2",
}

PWM_PINS = {"D3", "D5", "D6", "D9", "D10", "D11"}
SPI_ALIASES = {
    "D10": ["SS"],
    "D11": ["MOSI", "COPI"],
    "D12": ["MISO", "CIPO"],
    "D13": ["SCK"],
}


def electrical(pin_key: str) -> dict:
    if pin_key.startswith("ICSP_"):
        return {"role": "signal", "aliases": [], "functions": ["spi"]}
    if pin_key.startswith("GND_"):
        return {"role": "ground", "aliases": ["GND"], "functions": ["ground"]}
    if pin_key in {"3V3", "5V", "VIN", "IOREF"}:
        return {"role": "power", "aliases": [], "functions": ["power"]}
    if pin_key == "NC":
        # The current schema requires at least one function even for no-connect
        # pins. Keep the marker machine-readable while the catalog mapping is
        # resolved; the candidate notes and validation report block approval.
        return {"role": "no-connect", "aliases": [], "functions": ["digital"]}
    if pin_key == "RESET":
        return {"role": "signal", "aliases": ["RST"], "functions": ["reset"]}
    if pin_key == "AREF":
        return {"role": "signal", "aliases": [], "functions": ["analog", "reference"]}
    if pin_key.startswith("A"):
        number = int(pin_key[1:])
        aliases = [f"D{14 + number}"]
        functions = ["analog", "digital"]
        if pin_key == "A4":
            aliases.append("SDA")
            functions.append("i2c")
        elif pin_key == "A5":
            aliases.append("SCL")
            functions.append("i2c")
        return {"role": "signal", "aliases": aliases, "functions": functions}
    if pin_key.startswith("D"):
        number = int(pin_key[1:])
        aliases = [str(number), *SPI_ALIASES.get(pin_key, [])]
        functions = ["digital"]
        if pin_key in PWM_PINS:
            functions.append("pwm")
        if pin_key in SPI_ALIASES:
            functions.append("spi")
        if pin_key in {"D0", "D1"}:
            aliases.append("RX" if pin_key == "D0" else "TX")
            functions.append("uart")
        return {"role": "signal", "aliases": aliases, "functions": functions}
    raise ValueError(f"Unclassified pin: {pin_key}")


def make_pin(node_name: str, position: list[float]) -> dict:
    pin_key = PIN_KEY_OVERRIDES.get(node_name, node_name.removeprefix("pin_"))
    is_icsp = pin_key.startswith("ICSP_")
    label = pin_key.replace("_", " ")
    notes = []
    confidence = 0.95
    pitch = 2.54
    if is_icsp:
        notes.append(
            "Spatial marker only; electrical mapping must be confirmed before approval."
        )
        confidence = 0.6
    if pin_key == "NC":
        notes.append(
            "Current GLB contains NC where the canonical UNO R3 catalog expects SDA/SCL."
        )
        confidence = 0.5
    return {
        "pinKey": pin_key,
        "label": label,
        "nodeName": node_name,
        "position": position,
        "outwardDirection": [0, 1, 0],
        "connector": {
            "gender": "male" if is_icsp else "female",
            "form": "pin" if is_icsp else "socket",
            "pitchMillimeter": pitch,
            "diameterMillimeter": 0.64 if is_icsp else None,
        },
        "electrical": electrical(pin_key),
        "mounting": {
            "breadboardCompatible": False,
            "insertionDepthMillimeter": 6,
        },
        "confidence": confidence,
        "sourceObject": node_name,
        "notes": notes,
    }


metadata = {
    "schemaVersion": "1.0.0",
    "componentSlug": "arduino-uno-r3",
    "asset": {
        "path": "assets_db/3d_models/glb/arduino-uno-r3.glb",
        "sha256": hashlib.sha256(GLB_PATH.read_bytes()).hexdigest(),
        "format": "glb",
        "scaleStatus": "uncalibrated",
        "thumbnailPath": "assets_db/2d_svgs/raster_sources/arduino-uno-r3-top.png",
    },
    "physicalDimensions": {
        "unit": "millimeter",
        "width": 75.337738,
        "depth": 53.54475,
        "height": 10.032145,
        "measurementScope": "overall-including-connectors",
        "source": "mesh-bounds",
        "confidence": 0.7,
    },
    "coordinateSystems": {
        "authoring": {
            "space": "blender-object-local",
            "handedness": "right",
            "upAxis": "+Z",
            "frontAxis": "-Y",
            "unit": "meter",
        },
        "runtime": {
            "space": "gltf-model-local",
            "handedness": "right",
            "upAxis": "+Y",
            "frontAxis": "+Z",
            "unit": "meter",
            "modelUnitsPerMillimeter": 0.001,
        },
        "anchorsStoredIn": "runtime",
    },
    "origin": {
        "targetReference": "custom",
        "referencePoint": [0, 0, 0],
        "normalized": True,
        "description": (
            "ARDUINO_UNO_R3_ROOT is identity at the exported model origin. "
            "Mounting-surface reference still requires dimensional review."
        ),
    },
    "orientation": {
        "defaultRotationQuaternion": [0, 0, 0, 1],
        "normalized": True,
        "markers": [
            {
                "key": "usb-side",
                "pinKey": "AREF",
                "direction": "-X",
                "description": "The USB connector is on the -X side in runtime space.",
            }
        ],
    },
    "pins": [make_pin(name, position) for name, position in sorted(POSITIONS.items())],
    "placement": {
        "mountingType": "surface",
        "mountingPlaneNormal": [0, 1, 0],
        "rotationPolicy": "snap-yaw",
        "allowedYawDegrees": [0, 90, 180, 270],
        "keepOutMarginMillimeter": 2,
    },
    "provenance": {
        "authorGithub": "yoohyeon93",
        "branch": "feat/assets-arduino-board-data",
        "method": "blender-empty",
        "sourceTool": "Blender 5.2",
        "assetOrigin": "project-existing",
        "sourceUrl": None,
        "redistributionRights": "needs-review",
        "createdAt": "2026-07-29",
        "status": "candidate",
        "reviewerGithub": None,
        "approvedAt": None,
    },
    "notes": [
        "All 42 exported pin_* nodes are recorded at exact GLB-local coordinates.",
        "Digital/PWM, analog, I2C, SPI, UART, power, ground, reset, and reference functions are classified.",
        "Female header sockets use +Y insertion direction in runtime coordinates.",
        "D0-D7 measured pitch is about 2.1 mm, not the nominal 2.54 mm.",
        "ICSP marker pitch and electrical mapping require review.",
        "The GLB contains pin_NC but lacks the canonical UNO R3 SDA and SCL header nodes.",
        "The first digital header mesh visually contains ten sockets where eight are expected.",
        "Do not promote to approved until the open geometry/catalog issues are corrected.",
    ],
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(OUTPUT_PATH)
