import { demoAssets } from "../data/demoAssets";
import type {
  AssetImageKind,
  CircuitComponentAsset,
  ComponentAssetImage,
  ComponentPin,
  SignalType,
} from "../types/circuit";
import { assetBucket, hasSupabaseConfig, supabase } from "./supabaseClient";

interface AssetRow {
  slug: string;
  display_name: string;
  category: string;
  board_family: string | null;
  description: string | null;
  grid_width: number;
  grid_height: number;
  pixel_width: number;
  pixel_height: number;
  origin_x: number;
  origin_y: number;
  pin_coordinate_system: "image-pixel";
  license_status: "needs_review" | "approved" | "restricted";
  trademark_notes: string | null;
  images?: ImageRow[];
  pins?: PinRow[];
}

interface ImageRow {
  image_kind: AssetImageKind;
  storage_path: string | null;
  external_url: string | null;
  mime_type: string | null;
  width_px: number | null;
  height_px: number | null;
}

interface PinRow {
  pin_key: string;
  label: string;
  signal_type: SignalType;
  side: ComponentPin["side"];
  x_px: number;
  y_px: number;
  aliases: string[] | null;
  notes: string | null;
  sort_order: number;
}

export interface AssetLoadResult {
  assets: CircuitComponentAsset[];
  source: "supabase" | "local";
  error?: string;
}

export const loadCircuitAssets = async (): Promise<AssetLoadResult> => {
  if (!hasSupabaseConfig || !supabase) {
    return { assets: demoAssets, source: "local" };
  }

  const { data, error } = await supabase
    .from("circuit_component_assets")
    .select(
      `
        slug,
        display_name,
        category,
        board_family,
        description,
        grid_width,
        grid_height,
        pixel_width,
        pixel_height,
        origin_x,
        origin_y,
        pin_coordinate_system,
        license_status,
        trademark_notes,
        images:circuit_component_asset_images(
          image_kind,
          storage_path,
          external_url,
          mime_type,
          width_px,
          height_px
        ),
        pins:circuit_component_pins(
          pin_key,
          label,
          signal_type,
          side,
          x_px,
          y_px,
          aliases,
          notes,
          sort_order
        )
      `,
    )
    .eq("status", "ready")
    .order("display_name");

  if (error) {
    return { assets: demoAssets, source: "local", error: error.message };
  }

  return {
    assets: (data as AssetRow[]).map(mapAssetRow),
    source: "supabase",
  };
};

const resolvePublicUrl = (image: ImageRow): string | null => {
  if (image.external_url) {
    return image.external_url;
  }

  if (!image.storage_path || !supabase) {
    return null;
  }

  return supabase.storage.from(assetBucket).getPublicUrl(image.storage_path).data.publicUrl;
};

const mapAssetRow = (row: AssetRow): CircuitComponentAsset => ({
  slug: row.slug,
  displayName: row.display_name,
  category: row.category,
  boardFamily: row.board_family,
  description: row.description,
  gridWidth: row.grid_width,
  gridHeight: row.grid_height,
  pixelWidth: row.pixel_width,
  pixelHeight: row.pixel_height,
  originX: row.origin_x,
  originY: row.origin_y,
  pinCoordinateSystem: row.pin_coordinate_system,
  licenseStatus: row.license_status,
  trademarkNotes: row.trademark_notes,
  images: (row.images ?? []).map<ComponentAssetImage>((image) => ({
    kind: image.image_kind,
    storagePath: image.storage_path,
    url: resolvePublicUrl(image),
    mimeType: image.mime_type,
    width: image.width_px,
    height: image.height_px,
  })),
  pins: (row.pins ?? [])
    .map<ComponentPin>((pin) => ({
      componentSlug: row.slug,
      pinKey: pin.pin_key,
      label: pin.label,
      signalType: pin.signal_type,
      side: pin.side,
      x: pin.x_px,
      y: pin.y_px,
      sortOrder: pin.sort_order,
      aliases: pin.aliases ?? [],
      notes: pin.notes,
    }))
    .sort((a, b) => a.sortOrder - b.sortOrder),
});
