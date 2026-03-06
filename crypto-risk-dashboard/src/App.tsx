import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import ForecastPage from "./pages/ForecastPage";
import PortfolioPage from "./pages/PortfolioPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        {/* default route */}
        <Route path="/" element={<Navigate to="/forecast" replace />} />

        {/* main pages */}
        <Route path="/forecast" element={<ForecastPage />} />
        <Route path="/portfolio" element={<PortfolioPage />} />

        {/* fallback */}
        <Route path="*" element={<Navigate to="/forecast" replace />} />
      </Routes>
    </Layout>
  );
}