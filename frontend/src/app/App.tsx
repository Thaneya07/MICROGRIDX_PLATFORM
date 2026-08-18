import { NavLink, Route, HashRouter as Router, Routes } from "react-router-dom";
import { ConnectivityPage } from "./ConnectivityPage";
import { VisualizationPage } from "./VisualizationPage";

/**
 * HashRouter is used (rather than BrowserRouter) so the app works when
 * served as static files without server-side rewrite rules configured
 * for client-side routes (e.g. the Docker Compose `serve -s dist` setup).
 */
export function App() {
  return (
    <Router>
      <nav style={{ display: "flex", gap: 8, padding: "16px 24px 0", justifyContent: "center" }}>
        <NavLink to="/" end className={({ isActive }) => `mgx-nav-link${isActive ? " mgx-nav-link--active" : ""}`}>
          System connectivity
        </NavLink>
        <NavLink
          to="/visualization"
          className={({ isActive }) => `mgx-nav-link${isActive ? " mgx-nav-link--active" : ""}`}
        >
          3D Visualization
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<ConnectivityPage />} />
        <Route path="/visualization" element={<VisualizationPage />} />
        <Route path="/3d" element={<VisualizationPage />} />
      </Routes>
    </Router>
  );
}


