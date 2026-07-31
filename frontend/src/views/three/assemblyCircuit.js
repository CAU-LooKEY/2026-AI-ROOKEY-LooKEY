export function resolveAssemblyParts(circuit) {
  const plan = circuit?.assemblyPlan;
  if (!plan?.components?.length || !Array.isArray(plan.placements)) {
    return circuit?.parts ?? [];
  }

  const sourceParts = new Map((circuit.parts ?? []).map((part) => [part.id, part]));
  const placements = new Map(plan.placements.map((placement) => [
    placement.componentId,
    placement,
  ]));

  return plan.components
    .map((component, index) => {
      const source = sourceParts.get(component.instanceId);
      const placement = placements.get(component.instanceId);
      if (placement?.status === "failed") return null;
      return {
        ...source,
        id: component.instanceId,
        label: component.label,
        componentKey: component.assetSlug,
        position: source?.position ?? { x: index * 220, y: 0 },
        width: source?.width ?? 120,
        assemblyTransform: placement?.transform ?? null,
        placementMode: placement?.mode ?? "free",
      };
    })
    .filter(Boolean);
}
