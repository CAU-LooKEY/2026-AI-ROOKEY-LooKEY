import { Handle, Position } from "@xyflow/react";

function getHandlePosition(side) {
  if (side === "top") return Position.Top;
  if (side === "bottom") return Position.Bottom;
  if (side === "right") return Position.Right;
  return Position.Left;
}

export default function PartNode({ data }) {
  const pins = data.pins || [];

  const originalWidth = data.originalWidth || data.width || 180;
  const originalHeight = data.originalHeight || data.height || 120;
  const displayWidth = data.width || 180;

  const scale = displayWidth / originalWidth;
  const displayHeight = originalHeight * scale;

  return (
    <div className="lookeyPartNode" style={{ width: displayWidth }}>
      <div
        className="lookeyPartImageBox"
        style={{
          width: displayWidth,
          height: displayHeight,
        }}
      >
        <img src={data.image} alt={data.label} />

        {pins.map((pin) => {
          const left = pin.x_px * scale;
          const top = pin.y_px * scale;
          const position = getHandlePosition(pin.side);

          const commonStyle = {
            position: "absolute",
            left,
            top,
            width: 4,
            height: 4,
            borderRadius: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: 20,
          };

          return (
            <div key={pin.pin_key}>
              <Handle
                id={pin.pin_key}
                type="source"
                position={position}
                title={pin.label}
                style={{
                  ...commonStyle,
                  background: "#2563eb",
                  border: "1px solid white",
                }}
              />

              <Handle
                id={pin.pin_key}
                type="target"
                position={position}
                title={pin.label}
                style={{
                  ...commonStyle,
                  background: "transparent",
                  border: "none",
                  opacity: 0,
                }}
              />
            </div>
          );
        })}
      </div>

      <div className="lookeyPartNodeLabel">{data.label}</div>
    </div>
  );
}
