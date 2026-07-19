import { useState } from "react";
import { ReactFlow, Background, Controls } from "@xyflow/react";
import PartNode from "../../components/PartNode.jsx";
import CustomPinEdge from "../../components/CustomPinEdge.jsx";
import { circuitToReactFlow } from "./circuitToReactFlow.js";

const nodeTypes = {
  partNode: PartNode,
};

const edgeTypes = {
  pinEdge: CustomPinEdge,
};

const CONNECTOR_LABELS = {
  male: "수",
  female: "암",
};

function wireTypeLabel(jumper) {
  return `${CONNECTOR_LABELS[jumper.sourceConnector]}-${CONNECTOR_LABELS[jumper.targetConnector]}`;
}

export default function CanvasView({ circuit }) {
  const [showWireLabels, setShowWireLabels] = useState(false);
  const { nodes, edges, jumpers } = circuitToReactFlow(circuit);
  const visibleEdges = edges.map((edge) => ({
    ...edge,
    data: {
      ...edge.data,
      showLabel: showWireLabels,
    },
  }));

  return (
    <div className="circuitWorkspace">
      <div className="jumperInventory" aria-label="점퍼선 준비 목록">
        <div className="jumperInventoryTitle">
          <strong>점퍼선</strong>
          <span>{jumpers.length}개</span>
          <label className="wireLabelToggle">
            <input
              type="checkbox"
              checked={showWireLabels}
              onChange={(event) => setShowWireLabels(event.target.checked)}
            />
            <span>도면 라벨</span>
          </label>
        </div>
        <div className="jumperInventoryList">
          {jumpers.map((jumper) => (
            <div className="jumperInventoryItem" key={jumper.id} title={jumper.label}>
              <span className="jumperInventorySwatch" style={{ background: jumper.color }} />
              <b>{jumper.label}</b>
              <span>{wireTypeLabel(jumper)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="circuitFlowFrame">
        <ReactFlow
          nodes={nodes}
          edges={visibleEdges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.22, minZoom: 0.55, maxZoom: 1.15 }}
          minZoom={0.35}
          maxZoom={1.6}
        >
          <Background color="#cbd5e1" gap={28} size={1.5} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}
