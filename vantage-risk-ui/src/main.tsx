import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { StockDetail } from "./pages/StockDetail";
import { ArticleReader } from "./pages/ArticleReader";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/stock/:ticker" element={<StockDetail />} />
        <Route path="/news/:ticker/:articleIndex" element={<ArticleReader />} />
        <Route path="*" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
