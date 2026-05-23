import React, { useState, useEffect, useRef } from 'react';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import './BankScene.css';

const Belt = ({ step }) => {
  const positions = ['18%', '39%', '61%', '82%', '100%'];
  const docLeft = step === 0 ? '-6%' : positions[Math.min(step - 1, 4)];
  return (
    <div className="belt">
      <div className="belt-stripes" />
      <div className="belt-document" style={{ left: docLeft, opacity: step > 0 ? 1 : 0 }}>
        📄
      </div>
    </div>
  );
};

// Markdown Text Formatter
const formatMemoText = (text) => {
  if (!text) return null;
  const parts = text.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={index} style={{ color: '#fff' }}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
};

export default function BankScene() {
  const PLAYER_WIDTH = 120;
  const PLAYER_HEIGHT = 180;
  const [playerPos, setPlayerPos] = useState({ x: 50, y: 50 }); 
  const [roomWidth, setRoomWidth] = useState(window.innerWidth);
  
  const [direction, setDirection] = useState('down'); 
  const [isMoving, setIsMoving] = useState(false);
  const [walkFrame, setWalkFrame] = useState(1); 

  const [isNearDesk, setIsNearDesk] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [agentStatus, setAgentStatus] = useState({});
  const [results, setResults] = useState(null);
  const [step, setStep] = useState(0);
  
  const esRef = useRef(null);
  const fileInputRef = useRef(null);
  const roomRef = useRef(null); 
  const agentOrder = ['classifier', 'extractor', 'researcher', 'synthesizer'];

  const keysPressed = useRef(new Set());
  const isNearDeskRef = useRef(false);
  const uploadingRef = useRef(false);
  const dirRef = useRef('down');
  const movingRef = useRef(false);

  useEffect(() => { uploadingRef.current = uploading; }, [uploading]);

  const DESK_WIDTH = 110; 
  const DESK_POS = { x: (roomWidth / 2) - (DESK_WIDTH / 2), y: 100, w: DESK_WIDTH, h: 80 }; 

  useEffect(() => {
    if (!isMoving) return;
    const interval = setInterval(() => {
      setWalkFrame((prev) => (prev === 1 ? 2 : 1));
    }, 150); 
    return () => clearInterval(interval);
  }, [isMoving]);

  useEffect(() => {
    const handleResize = () => setRoomWidth(window.innerWidth);
    window.addEventListener('resize', handleResize);

    const handleKeyDown = (e) => {
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) e.preventDefault();
      keysPressed.current.add(e.key.toLowerCase());
    };

    const handleKeyUp = (e) => {
      keysPressed.current.delete(e.key.toLowerCase());
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    let animationId;
    
    const gameLoop = () => {
      const keys = keysPressed.current;
      let dx = 0;
      let dy = 0;
      let newDir = dirRef.current;
      let moved = false;

      if (keys.has('arrowup') || keys.has('w')) { dy -= 6; newDir = 'up'; moved = true; }
      if (keys.has('arrowdown') || keys.has('s')) { dy += 6; newDir = 'down'; moved = true; }
      if (keys.has('arrowleft') || keys.has('a')) { dx -= 6; newDir = 'left'; moved = true; }
      if (keys.has('arrowright') || keys.has('d')) { dx += 6; newDir = 'right'; moved = true; }

      if (moved) {
        setPlayerPos(prev => {
          const currentRoomWidth = window.innerWidth;
          const currentRoomHeight = roomRef.current ? roomRef.current.clientHeight : 480;

          const nextX = Math.max(0, Math.min(prev.x + dx, currentRoomWidth - PLAYER_WIDTH)); 
          const nextY = Math.max(0, Math.min(prev.y + dy, currentRoomHeight - PLAYER_HEIGHT)); 

          // --- Collision Boxes ---
          // Player collider is the feet area
          const playerColl = { 
            x: nextX + 25, 
            y: nextY + (PLAYER_HEIGHT - 60), 
            w: PLAYER_WIDTH - 50, 
            h: 50 
          };

          const checkCollision = (rect1, rect2) => {
            return rect1.x < rect2.x + rect2.w &&
                   rect1.x + rect1.w > rect2.x &&
                   rect1.y < rect2.y + rect2.h &&
                   rect1.y + rect1.h > rect2.y;
          };

          // Reception Desk Collider (centered)
          const receptionColl = { 
            x: DESK_POS.x, 
            y: DESK_POS.y + 40, 
            w: DESK_WIDTH, 
            h: 40 
          };

          // Agent Desks & Agents Colliders
          const agentDesksCount = 4;
          const agentWrapperWidth = 120;
          const space = (currentRoomWidth - (agentDesksCount * agentWrapperWidth)) / (agentDesksCount + 1);
          const obstacleColliders = [];
          
          for (let i = 0; i < agentDesksCount; i++) {
            const wrapperX = space + i * (agentWrapperWidth + space);
            const deskX = wrapperX + (agentWrapperWidth - DESK_WIDTH) / 2;
            const containerBaseY = currentRoomHeight - 40; 
            
            // Desk Collider (the furniture itself)
            obstacleColliders.push({ 
              x: deskX, 
              y: containerBaseY - 50, 
              w: DESK_WIDTH, 
              h: 50 
            });
            
            // Agent Character Collider (the person sitting)
            // Increased height and moved Y up to cover the head area
            obstacleColliders.push({ 
              x: wrapperX + 10, 
              y: containerBaseY - 150, 
              w: 100, 
              h: 120 
            });
          }

          const allColliders = [receptionColl, ...obstacleColliders];
          const hasCollision = allColliders.some(coll => checkCollision(playerColl, coll));

          if (hasCollision) {
            // If colliding, we don't update position
            return prev;
          }

          const deskCenterX = currentRoomWidth / 2 - PLAYER_WIDTH / 2;
          const deskCenterY = 140; 
          const dist = Math.hypot(nextX - deskCenterX, nextY - deskCenterY);
          const near = dist < 160;

          if (near !== isNearDeskRef.current) {
            isNearDeskRef.current = near;
            setIsNearDesk(near); 
          }

          return { x: nextX, y: nextY };
        });
      }

      if (keys.has(' ') && isNearDeskRef.current && !uploadingRef.current) {
        fileInputRef.current?.click();
        keys.delete(' '); 
      }

      if (moved !== movingRef.current) {
        movingRef.current = moved;
        setIsMoving(moved);
      }
      if (newDir !== dirRef.current) {
        dirRef.current = newDir;
        setDirection(newDir);
      }

      animationId = requestAnimationFrame(gameLoop);
    };

    animationId = requestAnimationFrame(gameLoop);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
    };
  }, []); 

  const currentSprite = isMoving 
    ? `player-${direction}-step${walkFrame}.png` 
    : `player-${direction}-idle.png`;

  const openSSE = (sid) => {
    if (esRef.current) esRef.current.close();
    const es = new EventSource(`http://127.0.0.1:8000/api/status/${sid}`);
    esRef.current = es;

    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if (ev.done) { es.close(); return; }
      const idx = agentOrder.indexOf(ev.agent);
      if (idx >= 0 && ev.status === 'working') setStep(idx + 1);
      setAgentStatus(prev => ({
        ...prev,
        [ev.agent]: { state: ev.status, bubble: ev.message, bar: ev.short },
      }));
    };
    es.onerror = () => es.close();
  };

  const handleFileSelection = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;

    setUploading(true);
    setResults(null);
    setAgentStatus({});
    setStep(0);

    const sid = crypto.randomUUID();
    openSSE(sid);

    const form = new FormData();
    form.append('files', selectedFile);

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/upload-documents?session_id=${sid}`, {
        method: 'POST', body: form,
      });
      const data = await res.json();
      setResults(data);
      setStep(5); 
    } catch {
      alert('Upload failed. Is your Python backend running?');
    } finally {
      setUploading(false);
      e.target.value = null; 
    }
  };

  // PDF Document Builder
  const buildPDF = (results) => {
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const margin = 50;
    const pageWidth = doc.internal.pageSize.getWidth();
    let y = 40;

    // --- 1. Header & Logo ---
    doc.setFillColor(15, 23, 42); // Very Dark Navy
    doc.rect(0, 0, pageWidth, 100, 'F');
    
    // Abstract Logo Shape
    doc.setFillColor(59, 130, 246); // Bright Blue
    doc.rect(margin, 35, 30, 30, 'F');
    doc.setFillColor(255, 255, 255);
    doc.rect(margin + 8, 43, 14, 14, 'F');
    
    doc.setFontSize(22);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(255, 255, 255);
    doc.text('INTELLI-CREDIT ARK', margin + 45, 53);
    
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(200, 200, 200);
    doc.text('INSTITUTIONAL GRADE AUTOMATED CREDIT MEMORANDUM', margin + 45, 68);
    
    // Date & ID in Header
    doc.setFontSize(8);
    doc.text(`REPORT ID: ${Math.random().toString(36).substr(2, 9).toUpperCase()}`, pageWidth - margin - 100, 45, { align: 'right' });
    doc.text(`DATE: ${new Date().toLocaleDateString().toUpperCase()}`, pageWidth - margin - 100, 58, { align: 'right' });

    y = 130;

    // --- 2. Executive Summary Snapshot ---
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text('EXECUTIVE SUMMARY', margin, y);
    y += 10;
    doc.setDrawColor(59, 130, 246);
    doc.setLineWidth(1.5);
    doc.line(margin, y, margin + 50, y);
    y += 25;

    const companyName = results?.company_name || "Unknown Entity";
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text('SUBJECT ENTITY:', margin, y);
    doc.setFont("helvetica", "normal");
    doc.text(companyName.toUpperCase(), margin + 100, y);
    y += 15;

    // Snapshot boxes
    const boxW = (pageWidth - (2 * margin) - 20) / 3;
    const drawSnapshotBox = (x, label, value) => {
      doc.setFillColor(248, 250, 252);
      doc.rect(x, y, boxW, 45, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.5);
      doc.rect(x, y, boxW, 45, 'S');
      
      doc.setFontSize(7);
      doc.setTextColor(100, 116, 139);
      doc.setFont("helvetica", "bold");
      doc.text(label.toUpperCase(), x + 10, y + 15);
      
      doc.setFontSize(10);
      doc.setTextColor(15, 23, 42);
      doc.text(value || 'N/A', x + 10, y + 32);
    };

    const fin = results?.financials || {};
    drawSnapshotBox(margin, 'Total Revenue', fin.total_revenue || fin.revenue_from_operations);
    drawSnapshotBox(margin + boxW + 10, 'Net Profit', fin.profit_after_tax || fin.profit_for_the_year);
    drawSnapshotBox(margin + (2 * boxW) + 20, 'Total Assets', fin.total_assets);
    
    y += 70;

    // --- 3. Recommendation Card ---
    if (results?.final_recommendation) {
      const isApproved = results.final_recommendation.includes('APPROVE');
      const color = isApproved ? [21, 128, 61] : [185, 28, 28]; // Green 700 or Red 700
      const bgColor = isApproved ? [240, 253, 244] : [254, 242, 242];

      doc.setFillColor(...bgColor);
      doc.rect(margin, y, pageWidth - (2 * margin), 50, 'F');
      doc.setDrawColor(...color);
      doc.setLineWidth(1);
      doc.rect(margin, y, pageWidth - (2 * margin), 50, 'S');

      doc.setFontSize(12);
      doc.setTextColor(...color);
      doc.setFont("helvetica", "bold");
      doc.text(isApproved ? 'FINAL VERDICT: APPROVED' : 'FINAL VERDICT: REJECTED', margin + 20, y + 30);
      
      y += 80;
    }

    // --- 4. Detailed Financial Analysis ---
    if (results?.financials && Object.keys(results.financials).length > 0) {
      doc.setTextColor(15, 23, 42);
      doc.setFontSize(12);
      doc.setFont("helvetica", "bold");
      doc.text('DETAILED FINANCIAL METRICS', margin, y);
      y += 15;

      const tableData = Object.entries(results.financials).map(([key, value]) => [
        key.replace(/_/g, ' ').toUpperCase(),
        value || 'NOT DETECTED'
      ]);

      autoTable(doc, {
        startY: y,
        head: [['Financial Indicator', 'Extracted Value']],
        body: tableData,
        margin: { left: margin },
        theme: 'grid',
        headStyles: { fillColor: [15, 23, 42], textColor: [255, 255, 255], fontStyle: 'bold' },
        styles: { fontSize: 8, cellPadding: 5 },
        columnStyles: { 0: { fontStyle: 'bold', fillColor: [249, 250, 251] } }
      });
      
      y = doc.lastAutoTable.finalY + 40;
    }

    // --- 5. Qualitative Analysis (SWOT) ---
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(12);
    doc.setFont("helvetica", "bold");
    doc.text('QUALITATIVE RISK ASSESSMENT', margin, y);
    y += 20;

    if (results?.final_recommendation) {
      doc.setFontSize(9);
      doc.setTextColor(51, 65, 85);
      
      // Clean text: remove markdown bold and non-ASCII characters that cause spacing/rendering issues
      const cleanText = results.final_recommendation
        .replace(/\*\*/g, '')
        .replace(/[^\x00-\x7F]/g, " "); 
      
      const lines = doc.splitTextToSize(cleanText, pageWidth - (2 * margin));
      
      lines.forEach(line => {
        if (y > 750) {
          doc.addPage();
          y = 50;
        }
        
        const categories = ['Strengths:', 'Weaknesses:', 'Opportunities:', 'Threats:', 'RECOMMENDATION:'];
        let matchedCat = null;
        categories.forEach(cat => {
          if (line.trim().startsWith(cat)) matchedCat = cat;
        });

        if (matchedCat) {
          doc.setFont("helvetica", "bold");
          doc.text(matchedCat, margin, y);
          doc.setFont("helvetica", "normal");
          const rest = line.replace(matchedCat, '');
          doc.text(rest, margin + doc.getTextWidth(matchedCat) + 2, y);
        } else {
          doc.setFont("helvetica", "normal");
          doc.text(line, margin, y);
        }
        y += 14;
      });
    }

    // --- 6. Signature Section ---
    y += 40;
    if (y > 700) { doc.addPage(); y = 50; }
    
    doc.setDrawColor(203, 213, 225);
    doc.line(margin, y, margin + 150, y);
    doc.setFontSize(8);
    doc.setFont("helvetica", "italic");
    doc.text('AUTHORIZED BY ARK AI SYSTEM', margin, y + 15);
    
    // --- Footer ---
    const pageCount = doc.internal.getNumberOfPages();
    for(let i = 1; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setFontSize(7);
        doc.setTextColor(148, 163, 184);
        doc.text(`ARK INTELLI-CREDIT v1.0 | CONFIDENTIAL | PAGE ${i} OF ${pageCount}`, pageWidth / 2, doc.internal.pageSize.getHeight() - 20, { align: 'center' });
    }

    doc.save(`ARK_Credit_Memo_${companyName.replace(/\s+/g, '_')}.pdf`);
  };

  return (
    <div className="bank-root">
      <div className="bank-header">
        <span>🏦 INTELLI-CREDIT ARK</span>
        <span className="header-sub">Interactive Application Hub</span>
      </div>

      <div className="game-wrapper">
        <div className="bank-room" ref={roomRef}>
          
          <div className="front-desk-container" style={{ left: DESK_POS.x, top: DESK_POS.y }}>
            {isNearDesk && !uploading && (
              <div className="interaction-prompt">PRESS [SPACE] TO SUBMIT</div>
            )}
            {uploading && (
              <div className="interaction-prompt" style={{ color: '#f39c12' }}>PROCESSING...</div>
            )}
            <img src="/sprites/front-desk.png" className="front-desk-img" alt="Reception Desk" />
            <span className="front-desk-label">RECEPTION</span>
          </div>

          <div className="ai-desks-container">
            <div className="static-agent-wrapper">
              {agentStatus['classifier'] && (
                <div className={`agent-bubble ${agentStatus['classifier'].state}`}>
                  {agentStatus['classifier'].bar?.toUpperCase() || agentStatus['classifier'].state.toUpperCase()}
                </div>
              )}
              <img src="/sprites/agent-1.png" className="agent-sprite" alt="Classifier" />
              <img src="/sprites/agent-desk.png" className="desk-sprite" alt="Desk" />
              <span className="agent-label">Classifier</span>
            </div>

            <div className="static-agent-wrapper">
              {agentStatus['extractor'] && (
                <div className={`agent-bubble ${agentStatus['extractor'].state}`}>
                  {agentStatus['extractor'].bar?.toUpperCase() || agentStatus['extractor'].state.toUpperCase()}
                </div>
              )}
              <img src="/sprites/agent-2.png" className="agent-sprite" alt="Extractor" />
              <img src="/sprites/agent-desk.png" className="desk-sprite" alt="Desk" />
              <span className="agent-label">Extractor</span>
            </div>

            <div className="static-agent-wrapper">
              {agentStatus['researcher'] && (
                <div className={`agent-bubble ${agentStatus['researcher'].state}`}>
                  {agentStatus['researcher'].bar?.toUpperCase() || agentStatus['researcher'].state.toUpperCase()}
                </div>
              )}
              <img src="/sprites/agent-3.png" className="agent-sprite" alt="Researcher" />
              <img src="/sprites/agent-desk.png" className="desk-sprite" alt="Desk" />
              <span className="agent-label">Researcher</span>
            </div>

            <div className="static-agent-wrapper">
              {agentStatus['synthesizer'] && (
                <div className={`agent-bubble ${agentStatus['synthesizer'].state}`}>
                  {agentStatus['synthesizer'].bar?.toUpperCase() || agentStatus['synthesizer'].state.toUpperCase()}
                </div>
              )}
              <img src="/sprites/agent-4.png" className="agent-sprite" alt="Synthesizer" />
              <img src="/sprites/agent-desk.png" className="desk-sprite" alt="Desk" />
              <span className="agent-label">Synthesizer</span>
            </div>
          </div>

          <div 
            className="player-character" 
            style={{ 
              transform: `translate(${playerPos.x}px, ${playerPos.y}px)`,
              backgroundImage: `url('/sprites/${currentSprite}')` 
            }}
          />

          <input type="file" accept=".pdf" ref={fileInputRef} style={{ display: 'none' }} onChange={handleFileSelection} />
        </div>

        <Belt step={step} />
      </div>

      <div className="bottom-panel">
        {uploading && (
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#f39c12', fontSize: '9px', marginBottom: '20px' }}>
            {agentOrder.map(agent => (
              <div key={agent}>{agent.toUpperCase()}: {agentStatus[agent]?.state || 'waiting'}</div>
            ))}
          </div>
        )}
        
        {results && (
          <div className="results-box">
            {console.log("FINAL RESULTS FROM API:", results)}
            <div className="results-topbar">
              <span className="results-complete">✓ PIPELINE COMPLETE</span>
              <button className="btn-download" onClick={() => buildPDF(results)}>⬇ DOWNLOAD MEMO</button>
            </div>
            
            <div className="fin-grid">
              {results.financials && Object.keys(results.financials).length > 0 ? (
                Object.entries(results.financials).map(([k, v]) => (
                  <div key={k} className="fin-card">
                    <div className="fin-label">{k.replace(/_/g, ' ').toUpperCase()}</div>
                    <div className="fin-value">{v || 'Not Found'}</div>
                  </div>
                ))
              ) : (
                <div className="fin-card" style={{ gridColumn: 'span 4', textAlign: 'center' }}>
                  <div className="fin-label">FINANCIAL DATA</div>
                  <div className="fin-value">No financial data extracted.</div>
                </div>
              )}
            </div>

            {results.final_recommendation && (() => {
              const approved = results.final_recommendation.includes('APPROVE');
              return (
                <div className={`verdict-card ${approved ? 'approve' : 'reject'}`} style={{ marginTop: '20px' }}>
                  <div className="verdict-badge">{approved ? '✓ RECOMMENDATION: APPROVED' : '✗ RECOMMENDATION: REJECTED'}</div>
                  <p className="verdict-memo">{formatMemoText(results.final_recommendation)}</p>
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </div>
  );
}