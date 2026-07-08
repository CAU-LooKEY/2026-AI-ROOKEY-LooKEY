import { BaseEdge, EdgeLabelRenderer } from "@xyflow/react";

export default function CustomPinEdge({ id, data }) {
  const { sourcePoint, targetPoint, label, labelDx = 0, labelDy = -14, color = "#ef4444" } = data;

  const midX = (sourcePoint.x + targetPoint.x) / 2;
  const midY = (sourcePoint.y + targetPoint.y) / 2;

  const path = `M ${sourcePoint.x} ${sourcePoint.y}
                C ${(sourcePoint.x + targetPoint.x) / 2} ${sourcePoint.y},
                  ${(sourcePoint.x + targetPoint.x) / 2} ${targetPoint.y},
                  ${targetPoint.x} ${targetPoint.y}`;

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke: color,
          strokeWidth: 5,
          zIndex: 9999,
        }}
      />

      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${midX + labelDx}px, ${midY + labelDy}px)`,
            background: "white",
            padding: "2px 6px",
            borderRadius: "6px",
            fontSize: "13px",
            fontWeight: 800,
            color: "#111827",
            pointerEvents: "none",
            zIndex: 10000,
          }}
        >
          {label}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
