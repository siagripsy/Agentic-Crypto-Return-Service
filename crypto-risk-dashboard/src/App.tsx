import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ForecastPage from "./pages/ForecastPage";
import PortfolioPage from "./pages/PortfolioPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/forecast" replace />} />
        <Route path="forecast" element={<ForecastPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
      </Route>
    </Routes>
  );
}