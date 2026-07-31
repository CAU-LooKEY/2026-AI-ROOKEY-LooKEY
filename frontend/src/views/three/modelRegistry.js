const modelModules = import.meta.glob(
  "../../../../assets_db/3d_models/glb/*.glb",
  {
    eager: true,
    import: "default",
    query: "?url",
  },
);

const approvedMetadataModules = import.meta.glob(
  "../../../../assets_db/3d_models/component_metadata/approved/**/*.json",
  {
    eager: true,
    import: "default",
  },
);

const candidateMetadataModules = import.meta.glob(
  "../../../../assets_db/3d_models/component_metadata/candidates/**/*.json",
  {
    eager: true,
    import: "default",
  },
);

const exampleMetadataModules = import.meta.glob(
  "../../../../assets_db/3d_models/component_metadata/examples/**/*.json",
  {
    eager: true,
    import: "default",
  },
);

const displayNames = {
  "active-buzzor": "Active Buzzer",
  "arduino-nano": "Arduino Nano",
  "arduino-uno-r3": "Arduino UNO R3",
  "breadboard-full": "Breadboard Full",
  "breadboard-half": "Breadboard Half",
  "dc-motor": "DC Motor",
  "hc-sr04": "HC-SR04",
  "led-5mm-blue": "LED 5mm Blue",
  "led-5mm-red": "LED 5mm Red",
  "led-rgb-5mm": "RGB LED 5mm",
  "l298n": "L298N Motor Driver",
  "passive-buzzor": "Passive Buzzer",
  "potentiometer-10k": "Potentiometer 10k",
  "pushbutton-6x6": "Push Button 6x6",
  "resistor-220-ohm": "Resistor 220 ohm",
  "servo-sg90": "Servo SG90",
  "slide-switch-spdt": "Slide Switch SPDT",
};

function normalizeModule(moduleValue) {
  return moduleValue?.default ?? moduleValue;
}

function collectMetadata(modules, status, priority, result) {
  Object.entries(modules).forEach(([sourcePath, moduleValue]) => {
    const metadata = normalizeModule(moduleValue);
    const slug = metadata?.componentSlug;
    if (!slug) return;

    const current = result.get(slug);
    if (!current || priority > current.priority) {
      result.set(slug, {
        data: metadata,
        priority,
        sourcePath,
        status,
      });
    }
  });
}

function makeDisplayName(slug) {
  if (displayNames[slug]) return displayNames[slug];
  return slug
    .split("-")
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(" ");
}

const metadataBySlug = new Map();
collectMetadata(exampleMetadataModules, "example", 1, metadataBySlug);
collectMetadata(candidateMetadataModules, "candidate", 2, metadataBySlug);
collectMetadata(approvedMetadataModules, "approved", 3, metadataBySlug);

export const modelRegistry = Object.entries(modelModules)
  .map(([sourcePath, url]) => {
    const fileName = sourcePath.split("/").pop();
    const slug = fileName.replace(/\.glb$/i, "");
    const metadataEntry = metadataBySlug.get(slug);

    return {
      fileName,
      key: slug,
      label: makeDisplayName(slug),
      metadata: metadataEntry?.data ?? null,
      metadataSourcePath: metadataEntry?.sourcePath ?? null,
      metadataStatus: metadataEntry?.status ?? "missing",
      slug,
      sourcePath,
      url,
    };
  })
  .sort((left, right) => left.label.localeCompare(right.label));
