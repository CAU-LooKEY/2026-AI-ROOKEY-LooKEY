export type AssetImageKind = "isometric_2d" | "preview_3d" | "schematic_2d";

export type SignalType =
  | "analog"
  | "component"
  | "digital"
  | "ground"
  | "gpio"
  | "i2c"
  | "power"
  | "pwm"
  | "spi"
  | "uart";

export type PinSide = "top" | "right" | "bottom" | "left" | "center";

export interface ComponentAssetImage {
  kind: AssetImageKind;
  storagePath?: string | null;
  url?: string | null;
  mimeType?: string | null;
  width?: number | null;
  height?: number | null;
}

export interface ComponentPin {
  componentSlug: string;
  pinKey: string;
  label: string;
  signalType: SignalType;
  side: PinSide;
  x: number;
  y: number;
  sortOrder: number;
  aliases?: string[];
  notes?: string | null;
}

export interface CircuitComponentAsset {
  slug: string;
  displayName: string;
  category: string;
  boardFamily?: string | null;
  description?: string | null;
  gridWidth: number;
  gridHeight: number;
  pixelWidth: number;
  pixelHeight: number;
  originX: number;
  originY: number;
  pinCoordinateSystem: "image-pixel";
  licenseStatus: "needs_review" | "approved" | "restricted";
  trademarkNotes?: string | null;
  images: ComponentAssetImage[];
  pins: ComponentPin[];
}

export interface CircuitPlacement {
  id: string;
  componentSlug: string;
  gridX: number;
  gridY: number;
}

export interface PinRef {
  placementId: string;
  pinKey: string;
}

export interface CircuitConnection {
  id: string;
  from: PinRef;
  to: PinRef;
  color: string;
  label?: string;
}

export interface CircuitScene {
  id: string;
  title: string;
  prompt: string;
  placements: CircuitPlacement[];
  connections: CircuitConnection[];
}
