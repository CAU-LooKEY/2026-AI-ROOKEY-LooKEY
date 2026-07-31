import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "@xyflow/react/dist/style.css";

const isJumperDemo = window.location.pathname.startsWith("/assets-3d/jumper-demo");
const isAssetLab = window.location.pathname.startsWith("/assets-3d");
const AssetLab = React.lazy(() => import("./views/three/AssetLab.jsx"));
const JumperDemo = React.lazy(() => import("./views/three/JumperDemo.jsx"));

ReactDOM.createRoot(document.getElementById("root")).render(
  isJumperDemo ? (
    <React.Suspense fallback={<div>Loading Jumper Connector Lab</div>}>
      <JumperDemo />
    </React.Suspense>
  ) : isAssetLab ? (
    <React.Suspense fallback={<div>Loading 3D Asset Lab</div>}>
      <AssetLab />
    </React.Suspense>
  ) : (
    <App />
  ),
);
