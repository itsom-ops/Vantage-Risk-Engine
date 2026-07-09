import { useRef, useState } from "react";
import { Download, FileText, Loader2 } from "lucide-react";
import type { CompanyRiskDetail, StockQuote, NewsItem } from "../api/api";

interface ExportReportProps {
  company: CompanyRiskDetail;
  quote: StockQuote | null;
  news: NewsItem[];
}

export function ExportReport({ company, quote, news }: ExportReportProps) {
  const reportRef = useRef<HTMLDivElement>(null);
  const [generating, setGenerating] = useState(false);

  const generatePDF = async () => {
    setGenerating(true);
    try {
      const { default: jsPDF } = await import("jspdf");
      const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });

      const pageW = doc.internal.pageSize.getWidth();
      const margin = 16;
      const contentW = pageW - margin * 2;
      let y = margin;

      // Helper: add a new page if needed
      const checkPage = (needed: number) => {
        if (y + needed > doc.internal.pageSize.getHeight() - margin) {
          doc.addPage();
          y = margin;
        }
      };

      // ── Header ──────────────────────────────────────────────
      doc.setFillColor(28, 28, 28);
      doc.rect(0, 0, pageW, 28, "F");
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(18);
      doc.setFont("helvetica", "bold");
      doc.text("VANTAGE RISK ENGINE", margin, 12);
      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.text("Credit Risk Intelligence Report", margin, 18);
      doc.text(
        `Generated: ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`,
        margin, 24
      );
      y = 36;

      // ── Company Header ────────────────────────────────────────
      doc.setTextColor(28, 28, 28);
      doc.setFontSize(22);
      doc.setFont("helvetica", "bold");
      doc.text(`${company.ticker} — ${company.name}`, margin, y);
      y += 8;
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(100, 100, 100);
      doc.text(`Sector: ${company.sector ?? "N/A"} · Period: ${company.period ?? "Latest"}`, margin, y);
      y += 10;

      // ── Executive Summary ────────────────────────────────────
      doc.setFillColor(240, 238, 230);
      doc.roundedRect(margin, y, contentW, 28, 3, 3, "F");
      doc.setTextColor(28, 28, 28);
      doc.setFontSize(11);
      doc.setFont("helvetica", "bold");
      doc.text("Executive Summary", margin + 4, y + 7);
      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(60, 60, 60);

      const tierColor = company.risk_tier === "Low" ? "Low Risk" :
        company.risk_tier === "Medium" ? "Medium Risk" :
        company.risk_tier === "High" ? "High Risk" : "Critical Risk";

      const summaryText = `${company.name} (${company.ticker}) is classified as ${tierColor} with a composite risk score of ${(company.composite_risk_score ?? 0).toFixed(1)}. ` +
        `The Altman Z-Score of ${(company.altman_z ?? 0).toFixed(2)} places it in the "${company.altman_tier ?? 'N/A'}" zone. ` +
        `Probability of default is estimated at ${((company.prob_of_default ?? 0) * 100).toFixed(2)}%.`;

      const summaryLines = doc.splitTextToSize(summaryText, contentW - 8);
      doc.text(summaryLines, margin + 4, y + 14);
      y += 34;

      // ── Risk Scores Grid ───────────────────────────────────────
      checkPage(45);
      doc.setTextColor(28, 28, 28);
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.text("Risk Metrics", margin, y);
      y += 6;

      const metrics = [
        ["Composite Risk Score", `${(company.composite_risk_score ?? 0).toFixed(1)}`, company.risk_tier ?? "—"],
        ["Altman Z-Score", `${(company.altman_z ?? 0).toFixed(2)}`, company.altman_tier ?? "—"],
        ["Probability of Default", `${((company.prob_of_default ?? 0) * 100).toFixed(2)}%`, ""],
        ["Distance-to-Default", `${(company.distance_to_default ?? 0).toFixed(3)}`, ""],
      ];

      // Table header
      doc.setFillColor(28, 28, 28);
      doc.rect(margin, y, contentW, 7, "F");
      doc.setTextColor(255, 255, 255);
      doc.setFontSize(8);
      doc.setFont("helvetica", "bold");
      doc.text("Metric", margin + 3, y + 5);
      doc.text("Value", margin + 90, y + 5);
      doc.text("Classification", margin + 130, y + 5);
      y += 7;

      doc.setTextColor(28, 28, 28);
      doc.setFont("helvetica", "normal");
      metrics.forEach(([label, val, cls], i) => {
        if (i % 2 === 0) {
          doc.setFillColor(247, 245, 240);
          doc.rect(margin, y, contentW, 7, "F");
        }
        doc.text(label, margin + 3, y + 5);
        doc.setFont("helvetica", "bold");
        doc.text(val, margin + 90, y + 5);
        doc.setFont("helvetica", "normal");
        if (cls) doc.text(cls, margin + 130, y + 5);
        y += 7;
      });
      y += 6;

      // ── Altman Z Ratios ────────────────────────────────────────
      checkPage(40);
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.text("Altman Z-Score Component Ratios", margin, y);
      y += 6;

      const ratios = [
        ["X1: Working Capital / Total Assets", company.x1_working_cap_ratio],
        ["X2: Retained Earnings / Total Assets", company.x2_retained_earn_ratio],
        ["X3: EBIT / Total Assets", company.x3_ebit_ratio],
        ["X4: Market Equity / Total Liabilities", company.x4_equity_debt_ratio],
        ["X5: Sales / Total Assets", company.x5_sales_ratio],
      ];

      doc.setFontSize(8);
      ratios.forEach(([label, val], i) => {
        if (i % 2 === 0) {
          doc.setFillColor(247, 245, 240);
          doc.rect(margin, y, contentW, 7, "F");
        }
        doc.setFont("helvetica", "normal");
        doc.text(label as string, margin + 3, y + 5);
        doc.setFont("helvetica", "bold");
        doc.text(`${((val as number | null) ?? 0).toFixed(4)}`, margin + 120, y + 5);
        y += 7;
      });
      y += 6;

      // ── SHAP Risk Drivers ──────────────────────────────────────
      if (company.top_risk_driver_1 || company.top_risk_driver_2) {
        checkPage(30);
        doc.setFontSize(12);
        doc.setFont("helvetica", "bold");
        doc.text("SHAP Risk Drivers", margin, y);
        y += 6;

        doc.setFontSize(8);
        doc.setFont("helvetica", "normal");
        [company.top_risk_driver_1, company.top_risk_driver_2, company.top_risk_driver_3]
          .filter(Boolean)
          .forEach((driver, i) => {
            checkPage(12);
            doc.setFillColor(247, 245, 240);
            doc.roundedRect(margin, y, contentW, 10, 2, 2, "F");
            doc.setTextColor(230, 0, 0);
            doc.setFont("helvetica", "bold");
            doc.text(`#${i + 1}`, margin + 3, y + 6);
            doc.setTextColor(60, 60, 60);
            doc.setFont("helvetica", "normal");
            const lines = doc.splitTextToSize(driver!, contentW - 16);
            doc.text(lines, margin + 12, y + 6);
            y += Math.max(10, lines.length * 5 + 4);
          });
        y += 4;
      }

      // ── Market Data ──────────────────────────────────────────
      if (quote) {
        checkPage(35);
        doc.setTextColor(28, 28, 28);
        doc.setFontSize(12);
        doc.setFont("helvetica", "bold");
        doc.text("Market Data Snapshot", margin, y);
        y += 6;

        const marketMetrics = [
          ["Current Price", `$${quote.price.toFixed(2)}`],
          ["Day Change", `${quote.day_change >= 0 ? "+" : ""}${quote.day_change.toFixed(2)} (${quote.day_change_pct >= 0 ? "+" : ""}${quote.day_change_pct.toFixed(2)}%)`],
          ["Market Cap", quote.market_cap ? `$${(quote.market_cap / 1e9).toFixed(2)}B` : "N/A"],
          ["P/E Ratio", quote.pe_ratio ? quote.pe_ratio.toFixed(2) : "N/A"],
          ["Beta", quote.beta ? quote.beta.toFixed(2) : "N/A"],
          ["52W High / Low", `$${(quote.week52_high ?? 0).toFixed(2)} / $${(quote.week52_low ?? 0).toFixed(2)}`],
        ];

        doc.setFontSize(8);
        marketMetrics.forEach(([label, val], i) => {
          if (i % 2 === 0) {
            doc.setFillColor(247, 245, 240);
            doc.rect(margin, y, contentW, 7, "F");
          }
          doc.setFont("helvetica", "normal");
          doc.text(label, margin + 3, y + 5);
          doc.setFont("helvetica", "bold");
          doc.text(val, margin + 90, y + 5);
          y += 7;
        });
        y += 6;
      }

      // ── News Sentiment Summary ──────────────────────────────────
      if (news.length > 0) {
        checkPage(25);
        doc.setTextColor(28, 28, 28);
        doc.setFontSize(12);
        doc.setFont("helvetica", "bold");
        doc.text("Recent News Sentiment", margin, y);
        y += 6;

        doc.setFontSize(8);
        news.slice(0, 5).forEach((item) => {
          checkPage(14);
          doc.setFillColor(247, 245, 240);
          doc.roundedRect(margin, y, contentW, 12, 2, 2, "F");

          // Sentiment indicator
          const sentColor = item.sentiment === "Bullish" ? [21, 128, 61] :
            item.sentiment === "Bearish" ? [230, 0, 0] : [100, 100, 100];
          doc.setFillColor(...(sentColor as [number, number, number]));
          doc.circle(margin + 4, y + 6, 1.5, "F");

          doc.setFont("helvetica", "bold");
          doc.setTextColor(28, 28, 28);
          const headlineLines = doc.splitTextToSize(item.headline, contentW - 40);
          doc.text(headlineLines[0], margin + 8, y + 5);

          doc.setFont("helvetica", "normal");
          doc.setTextColor(100, 100, 100);
          doc.text(`${item.sentiment} (${item.score > 0 ? "+" : ""}${item.score}) · ${item.publisher}`, margin + 8, y + 10);
          y += 14;
        });
      }

      // ── Footer ──────────────────────────────────────────────
      const pageCount = doc.getNumberOfPages();
      for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        const pageH = doc.internal.pageSize.getHeight();
        doc.setFillColor(240, 238, 230);
        doc.rect(0, pageH - 12, pageW, 12, "F");
        doc.setFontSize(7);
        doc.setTextColor(140, 140, 140);
        doc.text("Vantage Risk Engine — Confidential", margin, pageH - 5);
        doc.text(`Page ${i} of ${pageCount}`, pageW - margin - 20, pageH - 5);
      }

      // Save
      const dateStr = new Date().toISOString().slice(0, 10);
      doc.save(`${company.ticker}_Risk_Report_${dateStr}.pdf`);
    } catch (err) {
      console.error("PDF generation failed:", err);
      alert("Failed to generate PDF. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <>
      <button
        onClick={generatePDF}
        disabled={generating}
        className="btn-primary"
      >
        {generating ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Download size={14} />
        )}
        {generating ? "Generating…" : "Export Report"}
      </button>

      {/* Hidden ref for potential html2canvas capture */}
      <div ref={reportRef} style={{ position: "absolute", left: "-9999px", top: 0 }} />
    </>
  );
}
