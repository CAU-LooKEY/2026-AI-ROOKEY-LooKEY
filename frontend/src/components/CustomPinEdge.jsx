import { BaseEdge, EdgeLabelRenderer } from "@xyflow/react";

function pointOnCubic(start, controlA, controlB, end, t) {
  const inverse = 1 - t;
  return {
    x:
      inverse ** 3 * start.x
      + 3 * inverse ** 2 * t * controlA.x
      + 3 * inverse * t ** 2 * controlB.x
      + t ** 3 * end.x,
    y:
      inverse ** 3 * start.y
      + 3 * inverse ** 2 * t * controlA.y
      + 3 * inverse * t ** 2 * controlB.y
      + t ** 3 * end.y,
  };
}

function Connector({ point, toward, type, color }) {
  const angle = Math.atan2(toward.y - point.y, toward.x - point.x) * (180 / Math.PI);

  return (
    <g
      className={`jumperConnector jumperConnector--${type}`}
      transform={`translate(${point.x} ${point.y}) rotate(${angle})`}
      aria-hidden="true"
    >
      {type === "male" ? (
        <>
          <line className="jumperConnectorPin" x1="-5" y1="0" x2="1" y2="0" />
          <rect x="0" y="-2.5" width="7" height="5" rx="1" fill={color} />
        </>
      ) : (
        <>
          <rect x="-1" y="-3" width="8" height="6" rx="1" fill={color} />
          <circle className="jumperConnectorSocket" cx="0" cy="0" r="1.4" />
        </>
      )}
    </g>
  );
}

export default function CustomPinEdge({ id, data, selected }) {
  const {
    sourcePoint,
    targetPoint,
    label,
    color = "#2563eb",
    routeOffset = 0,
    labelPosition = 0.5,
    sourceConnector = "male",
    targetConnector = "female",
    wireType = "male-female",
    showLabel = false,
  } = data;

  const direction = targetPoint.x >= sourcePoint.x ? 1 : -1;
  const reach = Math.max(70, Math.min(190, Math.abs(targetPoint.x - sourcePoint.x) * 0.38));
  const controlA = {
    x: sourcePoint.x + direction * reach,
    y: sourcePoint.y + routeOffset,
  };
  const controlB = {
    x: targetPoint.x - direction * reach,
    y: targetPoint.y + routeOffset,
  };
  const labelPoint = pointOnCubic(
    sourcePoint,
    controlA,
    controlB,
    targetPoint,
    labelPosition,
  );
  const path = `M ${sourcePoint.x} ${sourcePoint.y} C ${controlA.x} ${controlA.y}, ${controlB.x} ${controlB.y}, ${targetPoint.x} ${targetPoint.y}`;

  return (
    <>
      <BaseEdge
        id={`${id}-halo`}
        path={path}
        style={{
          stroke: "rgba(255, 255, 255, 0.96)",
          strokeWidth: selected ? 5 : 3.5,
          strokeLinecap: "round",
        }}
      />
      <BaseEdge
        id={id}
        path={path}
        style={{
          stroke: color,
          strokeWidth: selected ? 2.2 : 1.4,
          strokeLinecap: "round",
        }}
      />
      <Connector
        point={sourcePoint}
        toward={controlA}
        type={sourceConnector}
        color={color}
      />
      <Connector
        point={targetPoint}
        toward={controlB}
        type={targetConnector}
        color={color}
      />

      {(showLabel || selected) && (
        <EdgeLabelRenderer>
          <div
            className="jumperEdgeLabel"
            title={`${label} / ${wireType}`}
            style={{
              transform: `translate(-50%, -50%) translate(${labelPoint.x}px, ${labelPoint.y}px)`,
              borderColor: color,
            }}
          >
            <span className="jumperEdgeSwatch" style={{ background: color }} />
            {label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
