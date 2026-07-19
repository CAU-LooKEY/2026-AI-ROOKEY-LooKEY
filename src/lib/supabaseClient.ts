import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const publishableKey = (import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY ||
  import.meta.env.VITE_SUPABASE_ANON_KEY) as string | undefined;

export const assetBucket =
  (import.meta.env.VITE_SUPABASE_ASSET_BUCKET as string | undefined) ?? "circuit-assets";

export const hasSupabaseConfig = Boolean(supabaseUrl && publishableKey);

export const supabase = hasSupabaseConfig
  ? createClient(supabaseUrl!, publishableKey!, {
      auth: {
        persistSession: false,
      },
    })
  : null;
