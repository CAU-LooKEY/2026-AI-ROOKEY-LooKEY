import "dotenv/config";
import { createClient } from "@supabase/supabase-js";
import { unzipSync } from "fflate";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

type ImageKind = "isometric_2d" | "preview_3d" | "schematic_2d";

const imageContentTypes = new Map([
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
]);

const supabaseUrl = process.env.VITE_SUPABASE_URL ?? process.env.SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const bucket = process.env.SUPABASE_ASSET_BUCKET ?? "circuit-assets";
const importDir = process.argv[2] ?? "asset-import";

if (!supabaseUrl || !serviceRoleKey) {
  throw new Error("Set VITE_SUPABASE_URL or SUPABASE_URL, plus SUPABASE_SERVICE_ROLE_KEY.");
}

const supabase = createClient(supabaseUrl, serviceRoleKey, {
  auth: {
    persistSession: false,
  },
});

const inferImageKind = (fileName: string): ImageKind => {
  const lower = fileName.toLowerCase();
  if (lower.includes("schematic") || lower.includes("symbol")) {
    return "schematic_2d";
  }
  if (lower.includes("3d") || lower.includes("preview")) {
    return "preview_3d";
  }
  return "isometric_2d";
};

const zipFiles = (await readdir(importDir)).filter((file) => file.toLowerCase().endsWith(".zip"));

for (const zipFile of zipFiles) {
  const slug = path.basename(zipFile, path.extname(zipFile));
  const { data: asset, error: assetError } = await supabase
    .from("circuit_component_assets")
    .select("id, slug")
    .eq("slug", slug)
    .single();

  if (assetError || !asset) {
    console.warn(`Skipping ${zipFile}: no circuit_component_assets row for slug "${slug}".`);
    continue;
  }

  const archive = unzipSync(new Uint8Array(await readFile(path.join(importDir, zipFile))));

  for (const [entryName, bytes] of Object.entries(archive)) {
    const extension = path.extname(entryName).toLowerCase();
    const imageContentType = imageContentTypes.get(extension);

    if (!imageContentType) {
      continue;
    }

    const imageKind = inferImageKind(entryName);
    const normalizedExtension = extension === ".jpeg" ? ".jpg" : extension;
    const storagePath = `${slug}/${imageKind}${normalizedExtension}`;
    const { error: uploadError } = await supabase.storage.from(bucket).upload(storagePath, Buffer.from(bytes), {
      cacheControl: "31536000",
      contentType: imageContentType,
      upsert: true,
    });

    if (uploadError) {
      throw new Error(`${slug}/${entryName}: ${uploadError.message}`);
    }

    const { error: upsertError } = await supabase.from("circuit_component_asset_images").upsert(
      {
        component_id: asset.id,
        image_kind: imageKind,
        storage_path: storagePath,
        external_url: null,
        mime_type: imageContentType,
      },
      { onConflict: "component_id,image_kind" },
    );

    if (upsertError) {
      throw new Error(`${slug}/${entryName}: ${upsertError.message}`);
    }

    console.log(`Uploaded ${storagePath}`);
  }
}
