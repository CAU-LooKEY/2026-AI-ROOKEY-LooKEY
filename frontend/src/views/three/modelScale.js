export const REAL_WORLD_SCENE_UNITS_PER_METER = 80;

function longestDimension(size) {
  return Math.max(
    Number(size?.x ?? 0),
    Number(size?.y ?? 0),
    Number(size?.z ?? 0),
    0.0001,
  );
}

function physicalEnvelopeMeter(metadata) {
  const dimensions = metadata?.physicalDimensions;
  if (dimensions?.unit !== "millimeter") return null;

  const longestMillimeter = Math.max(
    Number(dimensions.width ?? 0),
    Number(dimensions.depth ?? 0),
    Number(dimensions.height ?? 0),
  );
  return longestMillimeter > 0 ? longestMillimeter / 1000 : null;
}

export function resolveModelScale(metadata, modelSize, fallbackLongestSide) {
  const runtime = metadata?.coordinateSystems?.runtime;
  const isRealWorldAsset = metadata?.asset?.scaleStatus === "real-world"
    && runtime?.unit === "meter";
  if (isRealWorldAsset) return REAL_WORLD_SCENE_UNITS_PER_METER;

  const modelLongestSide = longestDimension(modelSize);
  const envelopeMeter = physicalEnvelopeMeter(metadata);
  if (envelopeMeter) {
    return envelopeMeter * REAL_WORLD_SCENE_UNITS_PER_METER / modelLongestSide;
  }

  return Number(fallbackLongestSide ?? 3) / modelLongestSide;
}
