import React, { useState } from "react";
import jsPDF from "jspdf";

const DocumentUpload = () => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [aiResults, setAiResults] = useState(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
  };

  const downloadPDF = () => {
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const pageW = doc.internal.pageSize.getWidth();
    const pageH = doc.internal.pageSize.getHeight();
    const margin = 50;
    const contentW = pageW - margin * 2;
    let y = margin;

    const checkPageBreak = (needed = 20) => {
      if (y + needed > pageH - margin) {
        doc.addPage();
        y = margin;
      }
    };

    const addLine = (text, size = 11, style = "normal", color = [30, 30, 30]) => {
      doc.setFontSize(size);
      doc.setFont("helvetica", style);
      doc.setTextColor(...color);
      const lines = doc.splitTextToSize(String(text), contentW);
      checkPageBreak(lines.length * (size * 1.4));
      doc.text(lines, margin, y);
      y += lines.length * (size * 1.4);
    };

    const addSpacer = (h = 12) => { y += h; };

    const addDivider = () => {
      checkPageBreak(10);
      doc.setDrawColor(200, 200, 200);
      doc.line(margin, y, pageW - margin, y);
      y += 10;
    };

    // ── Header ──────────────────────────────────────────────
    doc.setFillColor(30, 58, 138);
    doc.rect(0, 0, pageW, 70, "F");
    doc.setFontSize(20);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(255, 255, 255);
    doc.text("Intelli-Credit ARK", margin, 35);
    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    doc.text("AI-Generated Credit Memo", margin, 52);
    const dateStr = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" });
    doc.text(`Generated: ${dateStr}`, pageW - margin, 52, { align: "right" });
    y = 95;

    // ── Company & Classification ─────────────────────────────
    addLine("DOCUMENT CLASSIFICATION", 10, "bold", [100, 100, 100]);
    addSpacer(4);
    const categories = aiResults?.categories || {};
    const catEntries = Object.entries(categories);
    if (catEntries.length > 0) {
      catEntries.forEach(([file, type]) => addLine(`${file}  →  ${type}`, 11, "normal"));
    } else {
      addLine("No classification data.", 11, "normal");
    }
    addSpacer(8);
    addDivider();

    // ── Hard Financials ──────────────────────────────────────
    addLine("HARD FINANCIALS", 10, "bold", [100, 100, 100]);
    addSpacer(4);
    const fin = aiResults?.financials || {};
    const finRows = [
      ["Total Revenue",       fin.total_revenue       || "Not Found"],
      ["Net Profit",          fin.net_profit          || "Not Found"],
      ["Total Debt",          fin.total_debt          || "Not Found"],
      ["Cash & Equivalents",  fin.cash_and_equivalents || "Not Found"],
    ];
    finRows.forEach(([label, value]) => {
      checkPageBreak(18);
      doc.setFontSize(11);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(30, 30, 30);
      doc.text(`${label}:`, margin, y);
      doc.setFont("helvetica", "normal");
      doc.text(value, margin + 150, y);
      y += 18;
    });
    addSpacer(8);
    addDivider();

    // ── Market Sentiment ─────────────────────────────────────
    if (aiResults?.external_news?.length > 0) {
      addLine("LIVE MARKET SENTIMENT", 10, "bold", [100, 100, 100]);
      addSpacer(4);
      addLine(aiResults.external_news[0], 11, "normal");
      addSpacer(8);
      addDivider();
    }

    // ── Final Credit Memo ────────────────────────────────────
    if (aiResults?.final_recommendation) {
      const isApproved = aiResults.final_recommendation.includes("APPROVE");
      const badgeColor = isApproved ? [39, 174, 96] : [192, 57, 43];

      addLine("SENIOR CREDIT OFFICER — FINAL MEMO", 10, "bold", [100, 100, 100]);
      addSpacer(6);

      // Recommendation badge
      checkPageBreak(28);
      doc.setFillColor(...badgeColor);
      doc.roundedRect(margin, y - 14, 160, 22, 4, 4, "F");
      doc.setFontSize(11);
      doc.setFont("helvetica", "bold");
      doc.setTextColor(255, 255, 255);
      doc.text(isApproved ? "✓  RECOMMENDATION: APPROVE" : "✗  RECOMMENDATION: REJECT", margin + 10, y + 1);
      y += 28;

      addSpacer(6);
      addLine(aiResults.final_recommendation, 11, "normal", [50, 50, 50]);
    }

    // ── Footer ───────────────────────────────────────────────
    const totalPages = doc.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      doc.setPage(i);
      doc.setFontSize(9);
      doc.setFont("helvetica", "normal");
      doc.setTextColor(160, 160, 160);
      doc.text("Intelli-Credit ARK  •  Confidential", margin, pageH - 25);
      doc.text(`Page ${i} of ${totalPages}`, pageW - margin, pageH - 25, { align: "right" });
    }

    doc.save("credit_memo.pdf");
  };

  const handleDocumentUpload = async () => {
    if (!selectedFile) {
      alert("Please select a file first!");
      return;
    }

    setIsUploading(true);
    setAiResults(null);

    const formData = new FormData();
    formData.append("files", selectedFile); 

    try {
      console.log("Sending PDF to the Python backend...");
      
      const response = await fetch("http://127.0.0.1:8000/api/upload-documents", {
        method: "POST",
        body: formData, 
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      console.log("AI Analysis Complete!", data);
      
      setAiResults(data);

    } catch (error) {
      console.error("Failed to upload:", error);
      alert("Something went wrong. Is your Python server running?");
    } finally {
      setIsUploading(false); 
    }
  };

  return (
    <div style={{ padding: "20px", maxWidth: "700px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <h2>Intelli-Credit ARK</h2>
      <p>Upload a financial document for multi-agent AI extraction and research.</p>

      {/* The File Input */}
      <div style={{ marginBottom: "20px", padding: "20px", border: "2px dashed #ccc", borderRadius: "8px", textAlign: "center" }}>
        <input 
          type="file" 
          accept=".pdf" 
          onChange={handleFileChange} 
          style={{ cursor: "pointer" }}
        />
      </div>

      {/* The Upload Button */}
      <button 
        onClick={handleDocumentUpload} 
        disabled={isUploading || !selectedFile}
        style={{ 
          padding: "12px 24px", 
          backgroundColor: isUploading || !selectedFile ? "#ccc" : "#007BFF", 
          color: "white", 
          border: "none", 
          borderRadius: "4px",
          cursor: isUploading || !selectedFile ? "not-allowed" : "pointer",
          width: "100%",
          fontSize: "16px",
          fontWeight: "bold"
        }}
      >
        {isUploading ? "🤖 Agents are analyzing..." : "Upload & Run AI Pipeline"}
      </button>

      {/* The Results Display */}
      {aiResults && (
        <div style={{ marginTop: "30px", border: "1px solid #e0e0e0", borderRadius: "8px", overflow: "hidden" }}>
          
          {/* Header Banner */}
          <div style={{ backgroundColor: "#f4f6f8", padding: "15px", borderBottom: "1px solid #e0e0e0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <h3 style={{ margin: 0 }}>Analysis Results</h3>
              <p style={{ margin: "5px 0 0 0", fontSize: "14px", color: "#555" }}>
                <strong>Detected Type:</strong> {aiResults?.categories?.document_type || "Unknown"}
              </p>
            </div>
            <button
              onClick={downloadPDF}
              style={{
                padding: "8px 16px",
                backgroundColor: "#1e3a8a",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "bold",
                whiteSpace: "nowrap"
              }}
            >
              ⬇ Download PDF
            </button>
          </div>

          <div style={{ padding: "20px" }}>
            
            {/* Agent 2: Extracted Financials */}
            <h4 style={{ marginTop: 0, color: "#2c3e50" }}>📊 Hard Financials (ChromaDB)</h4>
            <ul style={{ lineHeight: "1.8" }}>
              <li><strong>Total Revenue:</strong> {aiResults?.financials?.total_revenue || "Not found"}</li>
              <li><strong>Net Profit:</strong> {aiResults?.financials?.net_profit || "Not found"}</li>
              <li><strong>Total Debt:</strong> {aiResults?.financials?.total_debt || "Not found"}</li>
              <li><strong>Cash & Equivalents:</strong> {aiResults?.financials?.cash_and_equivalents || "Not found"}</li>
            </ul>

            {/* Agent 3: Live Market Research */}
            {aiResults?.external_news && aiResults.external_news.length > 0 && (
              <div style={{ marginTop: "25px", padding: "15px", backgroundColor: "#e8f4fd", borderLeft: "4px solid #007BFF", borderRadius: "4px" }}>
                <h4 style={{ marginTop: 0, color: "#0056b3" }}>🌐 Live Market Sentiment (DuckDuckGo + Qwen)</h4>
                <p style={{ margin: 0, lineHeight: "1.6", color: "#333" }}>
                  {aiResults.external_news[0]}
                </p>
              </div>
            )}

            {/* Agent 4: Final Credit Memo */}
            {aiResults?.final_recommendation && (
              <div style={{
                marginTop: "25px",
                padding: "20px",
                backgroundColor: aiResults.final_recommendation.includes("APPROVE") ? "#eafaf1" : "#fdf2f2",
                borderLeft: `4px solid ${aiResults.final_recommendation.includes("APPROVE") ? "#27ae60" : "#e74c3c"}`,
                borderRadius: "4px"
              }}>
                <h4 style={{
                  marginTop: 0,
                  color: aiResults.final_recommendation.includes("APPROVE") ? "#1e8449" : "#c0392b"
                }}>
                  {aiResults.final_recommendation.includes("APPROVE") ? "✅ Credit Memo — APPROVED" : "❌ Credit Memo — REJECTED"}
                </h4>
                <p style={{ margin: 0, lineHeight: "1.8", color: "#333", whiteSpace: "pre-wrap" }}>
                  {aiResults.final_recommendation}
                </p>
              </div>
            )}

            {/* Debug Payload */}
            <details style={{ marginTop: "20px", fontSize: "13px", color: "#666" }}>
              <summary style={{ cursor: "pointer" }}>View Raw JSON Payload</summary>
              <pre style={{ backgroundColor: "#f8f9fa", padding: "10px", borderRadius: "4px", overflowX: "auto" }}>
                {JSON.stringify(aiResults, null, 2)}
              </pre>
            </details>

          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;