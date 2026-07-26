import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "@xyflow/react/dist/style.css";

const isAssetLab = window.location.pathname.startsWith("/assets-3d");
const AssetLab = React.lazy(() => import("./views/three/AssetLab.jsx"));

ReactDOM.createRoot(document.getElementById("root")).render(
  isAssetLab ? (
    <React.Suspense fallback={<div>Loading 3D Asset Lab</div>}>
      <AssetLab />
    </React.Suspense>
  ) : (
    <App />
  ),
);
