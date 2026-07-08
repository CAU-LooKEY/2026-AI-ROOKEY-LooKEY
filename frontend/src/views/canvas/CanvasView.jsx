import { ReactFlow, Background, Controls } from "@xyflow/react";
import PartNode from "../../components/PartNode.jsx";
import CustomPinEdge from "../../components/CustomPinEdge.jsx";
import { circuitToReactFlow } from "./circuitToReactFlow.js";
import { sampleCircuit } from "./sampleCircuit.js";

const nodeTypes = {
  partNode: PartNode,
};

const edgeTypes = {
  pinEdge: CustomPinEdge,
};

const { nodes, edges } = circuitToReactFlow(sampleCircuit);

export default function CanvasView() {
  return (
    <div
      style={{
        width: "100%",
        height: "520px",
        border: "1px solid #dfe6f0",
        borderRadius: "24px",
        overflow: "hidden",
        marginTop: "32px",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
