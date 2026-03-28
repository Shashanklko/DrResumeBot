import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  FileText, 
  Upload, 
  CheckCircle, 
  AlertCircle, 
  ArrowRight, 
  Download, 
  MessageSquare, 
  RefreshCw,
  Layout,
  Star,
  Zap,
  Target,
  X,
  Users,
  Coffee,
  Coins,
  Copy
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Helper for tailwind classes
function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Custom GitHub Icon since Lucide removed brand icons
const GithubIcon = ({ className }) => (
  <svg 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    className={className}
  >
    <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.28 1.15-.28 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
    <path d="M9 18c-4.51 2-5-2-7-2" />
  </svg>
);

// Custom Radar Chart Component
const RadarChart = ({ data, size = 300 }) => {
  const keys = Object.keys(data);
  const values = Object.values(data);
  const levels = 5;
  const angleStep = (Math.PI * 2) / keys.length;
  const radius = (size / 2) - 40;
  const center = size / 2;

  // Calculate points for the polygon
  const points = values.map((val, i) => {
    const r = (val / 100) * radius;
    const x = center + r * Math.sin(i * angleStep);
    const y = center - r * Math.cos(i * angleStep);
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="relative group">
      <svg width={size} height={size} className="overflow-visible">
        {/* Helper Circles/Axes */}
        {[...Array(levels)].map((_, i) => (
          <circle
            key={i}
            cx={center}
            cy={center}
            r={(radius / levels) * (i + 1)}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="1"
          />
        ))}
        {keys.map((_, i) => {
          const x = center + radius * Math.sin(i * angleStep);
          const y = center - radius * Math.cos(i * angleStep);
          return (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={x}
              y2={y}
              stroke="rgba(255,255,255,0.05)"
              strokeWidth="1"
            />
          );
        })}

        {/* The Polygon */}
        <polygon
          points={points}
          fill="rgba(168, 85, 247, 0.2)"
          stroke="rgba(168, 85, 247, 0.8)"
          strokeWidth="2"
          className="transition-all duration-1000"
        />

        {/* Labels */}
        {keys.map((key, i) => {
          const labelRadius = radius + 25;
          const x = center + labelRadius * Math.sin(i * angleStep);
          const y = center - labelRadius * Math.cos(i * angleStep);
          return (
            <text
              key={i}
              x={x}
              y={y}
              textAnchor="middle"
              className="text-[10px] fill-slate-500 uppercase font-bold tracking-tighter"
              style={{ fontSize: '9px' }}
            >
              {key.replace('_', ' ')}
            </text>
          );
        })}
      </svg>
    </div>
  );
};

// Custom Typewriter Hook
const useTypewriter = (text, speed = 10, active = true) => {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(active);

  useEffect(() => {
    if (!active) {
      setDisplayedText(text);
      setIsTyping(false);
      return;
    }

    setDisplayedText("");
    setIsTyping(true);
    let i = 0;
    const interval = setInterval(() => {
      setDisplayedText((prev) => prev + text.charAt(i));
      i++;
      if (i >= text.length) {
        clearInterval(interval);
        setIsTyping(false);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, active]);

  return { displayedText, isTyping };
};

// Formatted Message Component (Markdown-lite)
const FormattedMessage = ({ content, isLatest, isModel }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const { displayedText, isTyping } = useTypewriter(content, 5, isLatest && isModel);
  
  const textToRender = isLatest && isModel ? displayedText : content;
  const shouldTruncate = textToRender.length > 600 && !isExpanded;
  const finalContent = shouldTruncate ? textToRender.slice(0, 600) + "..." : textToRender;

  // Simple Markdown Parser
  const renderContent = (text) => {
    return text.split('\n').map((line, i) => {
      // Headers ###
      if (line.startsWith('###')) {
        return <h3 key={i} className="text-lg font-bold text-white mt-4 mb-2">{line.replace('###', '').trim()}</h3>;
      }
      // Section Headers 1. 2. 3.
      if (/^\d+\./.test(line)) {
        return <div key={i} className="text-sm font-black text-purple-400 uppercase tracking-widest mt-6 mb-3">{line}</div>;
      }
      // Bullets * or -
      if (line.trim().startsWith('*') || line.trim().startsWith('-')) {
        const bulletText = line.trim().replace(/^[*|-]\s*/, '');
        // Handle bold in bullets
        const parts = bulletText.split(/(\*\*.*?\*\*)/g);
        return (
          <div key={i} className="flex gap-3 ml-4 my-1.5 text-slate-300">
            <div className="mt-1.5 w-1.5 h-1.5 bg-purple-500/50 rounded-full shrink-0" />
            <span className="text-sm leading-relaxed">
              {parts.map((part, pi) => 
                part.startsWith('**') && part.endsWith('**') 
                ? <strong key={pi} className="text-white font-bold">{part.slice(2, -2)}</strong> 
                : part
              )}
            </span>
          </div>
        );
      }
      // Regular text with bold support
      const parts = line.split(/(\*\*.*?\*\*)/g);
      return (
        <p key={i} className="mb-2 leading-relaxed text-sm">
          {parts.map((part, pi) => 
            part.startsWith('**') && part.endsWith('**') 
            ? <strong key={pi} className="text-white font-bold">{part.slice(2, -2)}</strong> 
            : part
          )}
        </p>
      );
    });
  };

  return (
    <div className="relative">
      <div className="transition-all duration-500">
        {renderContent(finalContent)}
      </div>
      
      {textToRender.length > 600 && !isTyping && (
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-4 text-xs font-bold text-purple-400 hover:text-purple-300 flex items-center gap-1.5 transition-colors uppercase tracking-widest"
        >
          {isExpanded ? "Show Less" : "Read Full Verdict"} 
          <ArrowRight className={cn("w-3 h-3 transition-transform", isExpanded ? "-rotate-90" : "")} />
        </button>
      )}
      
      {isTyping && (
        <span className="inline-block w-1.5 h-4 bg-purple-500 animate-pulse ml-1 align-middle" />
      )}
    </div>
  );
};

// API URL (will be configured via VITE_API_URL on Vercel)
const API_BASE = import.meta.env.DEV ? 'http://localhost:10000' : (import.meta.env.VITE_API_URL || '');

export default function App() {
  const [file, setFile] = useState(null);
  const [jd, setJd] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [sid, setSid] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [error, setError] = useState(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [improvedData, setImprovedData] = useState(null);
  const [generatingCV, setGeneratingCV] = useState(false);
  const [customCvInstructions, setCustomCvInstructions] = useState("");
  const [isDevModalOpen, setIsDevModalOpen] = useState(false);
  const [isDonateModalOpen, setIsDonateModalOpen] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState("");
  const [mode, setMode] = useState('analyze'); // 'analyze' or 'simple'

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    if (mode === 'analyze' && !jd) return;

    setLoading(true);
    setAnalyzing(true);
    setError(null);

    const formData = new FormData();
    formData.append('resume', file);
    if (mode === 'analyze') {
      formData.append('jd_text', jd);
    }

    try {
      const endpoint = mode === 'analyze' ? `${API_BASE}/api/analyze` : `${API_BASE}/api/simple_generate`;
      const res = await axios.post(endpoint, formData);
      
      setSid(res.data.sid);
      if (mode === 'analyze') {
        setAnalysis(res.data.analysis);
      } else {
        // Simple mode: straight to improved CVs
        setImprovedData(res.data.improved_data);
        setAnalysis({
          overall_score: 0,
          section_scores: {},
          strengths: [],
          weaknesses: [],
          suggestions: [],
          passed: true,
          summary: "CV formatted successfully using Simple Mode."
        });
      }
      setAnalyzing(false);
      setLoading(false);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to process resume');
      setAnalyzing(false);
      setLoading(false);
    }
  };

  const askQuestion = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userMsg = { role: 'user', content: question };
    setChatHistory([...chatHistory, userMsg]);
    setQuestion('');
    
    try {
      const res = await axios.post(`${API_BASE}/api/chat`, { sid, question });
      setChatHistory(prev => [...prev, { role: 'model', content: res.data.answer }]);
      // If user asked for changes, improvedData might be stale
      setImprovedData(null);
    } catch (err) {
      setChatHistory(prev => [...prev, { role: 'model', content: "Error: Could not get a response." }]);
    }
  };

  const getImprovedData = async () => {
    setGeneratingCV(true);
    try {
      const res = await axios.post(`${API_BASE}/api/generate_improved`, { 
        sid,
        user_instruction: customCvInstructions
      });
      setImprovedData(res.data.improved_data);
      setCustomCvInstructions(""); // Clear after use
    } catch (err) {
      console.error(err);
    } finally {
      setGeneratingCV(false);
    }
  };

  const downloadReport = () => {
    window.location.href = `${API_BASE}/api/download_report?sid=${sid}`;
  };

  const downloadCV = (format) => {
    window.location.href = `${API_BASE}/api/download_cv/${format}?sid=${sid}`;
  };

  const reset = () => {
    setFile(null);
    setJd('');
    setSid(null);
    setAnalysis(null);
    setError(null);
    setChatHistory([]);
    setImprovedData(null);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-slate-200 font-sans selection:bg-purple-500/30">
      {/* Background Blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-600/10 rounded-full blur-[120px]" />
      </div>

      <nav className="relative z-10 border-b border-white/5 bg-black/20 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.png" alt="Logo" className="w-10 h-10 object-contain" />
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              Resumehub.store
            </span>
          </div>
          <div className="flex items-center gap-6">
            <a 
              href="https://t.me/resumegoatbot" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center gap-1.5"
            >
              <MessageSquare className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Telegram Bot</span>
            </a>
            <button 
              onClick={() => setIsDonateModalOpen(true)}
              className="text-sm font-medium text-slate-400 hover:text-white transition-colors flex items-center gap-1.5"
            >
              <Users className="w-3.5 h-3.5" /> <span className="hidden sm:inline">Contribute</span>
            </button>
            <button 
              onClick={reset}
              className="px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm font-medium transition-all"
            >
              New Analysis
            </button>
          </div>
        </div>
      </nav>

      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-4 pb-12">
        <AnimatePresence mode="wait">
          {!analysis ? (
            <motion.div 
              key="upload"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="max-w-5xl mx-auto"
            >
              <div className="text-center mb-10">
                <h1 className="text-5xl font-bold mb-6 tracking-tight text-white">
                  Get Professional <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-500">AI Resume Analysis</span>
                </h1>
                <p className="text-lg text-slate-400 max-w-xl mx-auto leading-relaxed">
                  Is your resume industry-ready? Upload your CV and paste the job description to get an instant ATS score, improvement tips, and 5 premium CV formats.
                </p>
              </div>

              <form onSubmit={handleUpload} className="space-y-8">
                <div className="group relative">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-3xl blur opacity-30 group-hover:opacity-100 transition duration-1000 group-hover:duration-200"></div>
                  <div className="relative bg-[#111114] border border-white/10 rounded-3xl p-8 shadow-2xl overflow-hidden">
                    
                    {/* Mode Selector */}
                    <div className="flex items-center gap-1 p-1 bg-white/[0.03] border border-white/5 rounded-2xl w-fit mb-10">
                      <button
                        type="button"
                        onClick={() => setMode('analyze')}
                        className={cn(
                          "px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-widest transition-all",
                          mode === 'analyze' 
                            ? "bg-white text-black shadow-xl" 
                            : "text-slate-500 hover:text-slate-300"
                        )}
                      >
                        JD Matching
                      </button>
                      <button
                        type="button"
                        onClick={() => setMode('simple')}
                        className={cn(
                          "px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-widest transition-all",
                          mode === 'simple' 
                            ? "bg-white text-black shadow-xl" 
                            : "text-slate-500 hover:text-slate-300"
                        )}
                      >
                        Fast Format
                      </button>
                    </div>

                    <div className={cn("grid grid-cols-1 gap-10 transition-all duration-500", mode === 'analyze' ? "md:grid-cols-2" : "md:grid-cols-1")}>
                      <div>
                        <label className="block text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6 flex items-center gap-2">
                           <Upload className="w-4 h-4" /> 1. Upload Resume
                        </label>
                        
                        <div className="relative">
                          <input 
                            type="file" 
                            onChange={(e) => setFile(e.target.files[0])}
                            accept=".pdf,.docx,.doc,.txt"
                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                          />
                          <div className={cn(
                            "h-64 border-2 border-dashed rounded-2xl flex flex-col items-center justify-center gap-4 transition-all duration-300",
                            file ? "border-purple-500/50 bg-purple-500/5" : "border-white/10 bg-white/[0.02] group-hover:border-white/20"
                          )}>
                            {file ? (
                              <>
                                <div className="w-12 h-12 bg-purple-500/20 rounded-full flex items-center justify-center">
                                  <CheckCircle className="text-purple-400" />
                                </div>
                                <div className="text-center">
                                  <p className="text-white font-medium">{file.name}</p>
                                  <p className="text-xs text-slate-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB • Ready</p>
                                </div>
                              </>
                            ) : (
                              <>
                                <Upload className="w-10 h-10 text-slate-600 mb-2" />
                                <p className="text-slate-400 font-medium text-center px-4">
                                  Drag & drop your resume or <span className="text-purple-400">browse files</span>
                                </p>
                                <p className="text-[10px] text-slate-600 uppercase tracking-widest text-center mt-2 px-4 italic">Supports PDF, DOCX, TXT (Max 5MB)</p>
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                      
                      {mode === 'analyze' && (
                        <div className="flex flex-col">
                          <label className="block text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6 flex items-center gap-2">
                             <Layout className="w-4 h-4" /> 2. Job Description
                          </label>
                          <textarea 
                            value={jd}
                            onChange={(e) => setJd(e.target.value)}
                            placeholder="Paste the full job description here..."
                            className="flex-1 min-h-[16rem] bg-white/[0.03] border border-white/10 rounded-2xl p-5 text-slate-300 focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500/40 outline-none transition-all resize-none"
                          />
                        </div>
                      )}
                    </div>

                    <button 
                      type="submit"
                      disabled={!file || (mode === 'analyze' && !jd) || loading}
                      className={cn(
                        "w-full mt-10 py-5 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all transform active:scale-[0.98]",
                        (!file || (mode === 'analyze' && !jd) || loading) 
                          ? "bg-slate-800 text-slate-500 cursor-not-allowed opacity-50" 
                          : "bg-white text-black hover:bg-slate-200 shadow-[0_0_20px_rgba(255,255,255,0.1)]"
                      )}
                    >
                      {loading ? (
                        <>
                          <RefreshCw className="animate-spin w-5 h-5" />
                          {mode === 'analyze' ? 'Analyzing Experience...' : 'Formatting Layout...'}
                        </>
                      ) : (
                        <>
                          {mode === 'analyze' ? 'Analyze & Optimize' : 'Generate Professional CVs'}
                          <ArrowRight className="w-5 h-5" />
                        </>
                      )}
                    </button>
                    
                    {error && (
                      <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 text-sm">
                        <AlertCircle className="w-5 h-5 shrink-0" />
                        {error}
                      </div>
                    )}
                  </div>
                </div>
              </form>
            </motion.div>
          ) : (
            <motion.div 
              key="results"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-10"
            >
              <div className="lg:col-span-8 space-y-10">
                {/* Score Summary (Hidden in Simple Mode) */}
                {analysis.overall_score > 0 && (
                  <div className="bg-[#111114] border border-white/10 rounded-3xl p-10 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 blur-[80px] -mr-32 -mt-32" />
                    
                    <div className="flex flex-col md:flex-row items-center gap-10">
                      <div className="relative flex-shrink-0">
                        <RadarChart data={analysis.section_scores} size={320} />
                        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                          <span className="text-5xl font-bold text-white tracking-tighter">{analysis.overall_score}%</span>
                          <span className="text-[10px] uppercase font-black text-purple-500/80 tracking-[0.2em]">Overall Match</span>
                        </div>
                      </div>
  
                      <div className="flex-1 text-center md:text-left">
                        <div className="flex items-center justify-center md:justify-start gap-3 mb-4">
                          {analysis.passed ? (
                            <span className="px-3 py-1 bg-green-500/10 text-green-400 border border-green-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                              <CheckCircle className="w-3.5 h-3.5" /> PASSED BENCHMARK
                            </span>
                          ) : (
                            <span className="px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                              <AlertCircle className="w-3.5 h-3.5" /> NEEDS IMPROVEMENT
                            </span>
                          )}
                          <span className="text-slate-500 text-xs">Benchmark: {analysis.benchmark}%</span>
                        </div>
                        <h2 className="text-2xl font-bold text-white mb-3">Analysis Result</h2>
                        <p className="text-slate-400 leading-relaxed italic">"{analysis.summary}"</p>
                      </div>
                    </div>
  
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-6 mt-12 pt-10 border-t border-white/5">
                      {Object.entries(analysis.section_scores).map(([key, score]) => (
                        <div key={key} className="text-center group">
                          <div className="text-[10px] uppercase text-slate-500 font-bold tracking-widest mb-2 group-hover:text-slate-300 transition-colors">
                            {key.replace('_', ' ')}
                          </div>
                          <div className="text-xl font-bold text-white mb-2">{score}%</div>
                          <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                            <motion.div 
                              initial={{ width: 0 }}
                              animate={{ width: `${score}%` }}
                              className="h-full bg-gradient-to-r from-purple-500/40 to-blue-500/40" 
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {mode === 'simple' && (
                  <div className="bg-[#111114] border border-white/10 rounded-3xl p-10 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 blur-[80px] -mr-32 -mt-32" />
                    <div className="flex items-center gap-6">
                       <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center shrink-0">
                          <CheckCircle className="text-green-400 w-10 h-10" />
                       </div>
                       <div>
                          <h2 className="text-3xl font-bold text-white mb-2">Ready to Download!</h2>
                          <p className="text-slate-400 leading-relaxed max-w-lg">
                            We've structured your resume into our professional Elite suite. You can now download it in any of the 5 premium formats on the right.
                          </p>
                       </div>
                    </div>
                  </div>
                )}

                {/* SWOT (Only in Analyze Mode) */}
                {analysis.overall_score > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="bg-[#111114] border border-white/10 rounded-3xl p-8">
                      <h3 className="text-sm font-bold text-green-400 uppercase tracking-widest flex items-center gap-2 mb-6">
                        <Star className="w-4 h-4" /> Top Strengths
                      </h3>
                      <ul className="space-y-4">
                        {analysis.strengths.map((s, i) => (
                          <li key={i} className="flex gap-3 text-slate-300">
                            <div className="mt-1.5 w-1.5 h-1.5 bg-green-500/50 rounded-full shrink-0" />
                            <span className="text-sm">{s}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="bg-[#111114] border border-white/10 rounded-3xl p-8">
                      <h3 className="text-sm font-bold text-red-400 uppercase tracking-widest flex items-center gap-2 mb-6">
                        <Zap className="w-4 h-4" /> Areas of concern
                      </h3>
                      <ul className="space-y-4">
                        {analysis.weaknesses.map((w, i) => (
                          <li key={i} className="flex gap-3 text-slate-300">
                            <div className="mt-1.5 w-1.5 h-1.5 bg-red-500/50 rounded-full shrink-0" />
                            <span className="text-sm">{w}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {/* Suggestions (Only in Analyze Mode) */}
                {analysis.suggestions && analysis.suggestions.length > 0 && (
                  <div className="bg-[#111114] border border-white/10 rounded-3xl p-8">
                    <h3 className="text-sm font-bold text-blue-400 uppercase tracking-widest flex items-center gap-2 mb-8">
                      <Target className="w-4 h-4" /> Strategic Improvements
                    </h3>
                    <div className="space-y-8">
                      {analysis.suggestions.map((s, i) => (
                        <div key={i} className="relative pl-8 border-l border-white/5">
                          <div className="absolute left-[-5px] top-0 w-[9px] h-[9px] bg-blue-500 rounded-full" />
                          <h4 className="text-white font-bold mb-3 flex items-center gap-2">
                            <span className="text-xs text-blue-500">[{s.section}]</span> 
                            {s.issue}
                          </h4>
                          <div className="bg-white/[0.02] border border-white/5 rounded-xl p-4 text-sm text-slate-400 leading-relaxed">
                            <span className="text-green-400/80 font-bold mr-2">Proposed Fix:</span>{s.fix}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Sidebar: Actions & Chat */}
              <div className="lg:col-span-4 space-y-8">
                <div className="bg-gradient-to-br from-purple-500 to-blue-600 rounded-3xl p-0.5 relative group shadow-2xl">
                  <div className="absolute -inset-2 bg-gradient-to-r from-purple-500 to-blue-600 rounded-[34px] blur-xl opacity-20 group-hover:opacity-40 transition duration-500"></div>
                  <div className="bg-[#111114] rounded-[30px] p-8 relative">
                    <h3 className="text-lg font-bold text-white mb-6">Action Center</h3>
                    
                      <div className="space-y-4">
                        <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-4 mb-2">
                          <label className="text-[10px] text-slate-500 font-bold uppercase tracking-widest block mb-2">Custom AI instructions</label>
                          <textarea 
                            value={customCvInstructions}
                            onChange={(e) => setCustomCvInstructions(e.target.value)}
                            placeholder="e.g. 'Make it more backend-focused' or 'Add my new OCI certificate'..."
                            className="w-full bg-transparent text-sm text-slate-300 outline-none resize-none h-20 placeholder:text-slate-700"
                          />
                        </div>

                        {!improvedData ? (
                          <button 
                            onClick={getImprovedData}
                            disabled={generatingCV}
                            className="w-full py-4 bg-white text-black font-bold rounded-2xl flex items-center justify-center gap-2 hover:bg-slate-200 transition-all disabled:opacity-50"
                          >
                            {generatingCV ? <RefreshCw className="animate-spin" /> : <Zap className="w-4 h-4" />}
                            Generate Improved CVs
                          </button>
                        ) : (
                          <>
                            <button 
                              onClick={getImprovedData}
                              disabled={generatingCV}
                              className="w-full py-3 bg-purple-600/20 hover:bg-purple-600/30 border border-purple-500/30 text-purple-400 font-bold rounded-xl flex items-center justify-center gap-2 transition-all disabled:opacity-50 mb-4"
                            >
                              {generatingCV ? <RefreshCw className="animate-spin w-4 h-4" /> : <RefreshCw className="w-4 h-4" />}
                              Update with Instructions
                            </button>
                            <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2 pt-2 border-t border-white/5">Elite Multi-Format Suite</div>
                            {[
                              { id: 'classic_1page', label: 'Classic ATS (Audric)' },
                              { id: 'specialized', label: 'Specialized Technical' },
                              { id: 'sidebar_left', label: 'Sidebar Left (Elite)' },
                              { id: 'sidebar_right', label: 'Sidebar Right (Elite)' },
                              { id: 'modern_2page', label: 'Modern 2-Page Professional' }
                            ].map(fmt => (
                              <div key={fmt.id} className="flex gap-2 w-full">
                                <button 
                                  onClick={() => {
                                    window.open(`${API_BASE}/api/download_cv/${fmt.id}?sid=${sid}`, '_blank');
                                  }} 
                                  className="flex-1 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl flex items-center justify-between px-4 transition-all"
                                  title={`Download ${fmt.label} PDF`}
                                >
                                  <span className="text-xs font-medium truncate">{fmt.label}</span>
                                  <Download className="w-3.5 h-3.5 text-slate-500" />
                                </button>
                                <button 
                                  onClick={() => {
                                    window.open(`${API_BASE}/api/download_cv_docx/${fmt.id}?sid=${sid}`, '_blank');
                                  }} 
                                  className="w-14 py-3 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-xl flex items-center justify-center transition-all"
                                  title="Download Word (.docx)"
                                >
                                  <FileText className="w-4 h-4 text-blue-400" />
                                </button>
                              </div>
                            ))}
                        </>
                      )}
                      
                      <div className="pt-4 mt-4 border-t border-white/5">
                        <button 
                          onClick={downloadReport}
                          className="w-full py-3 text-slate-400 hover:text-white flex items-center justify-center gap-2 text-sm transition-all"
                        >
                          <FileText className="w-4 h-4" />
                          Full Review Report (PDF)
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* AI Chatbox Widget */}
                <div className="bg-[#111114] border border-white/10 rounded-3xl overflow-hidden flex flex-col h-[500px]">
                  <div className="p-6 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-purple-400" /> Chat with AI
                      </h3>
                      <p className="text-[10px] text-slate-500 mt-1 uppercase tracking-wider">Discuss analysis or request changes</p>
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-white/10">
                    {chatHistory.length === 0 ? (
                      <div className="text-center py-12">
                        <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-4">
                          <MessageSquare className="text-slate-600 w-5 h-5" />
                        </div>
                        <p className="text-xs text-slate-500 px-8">Ask questions like "How can I improve my technical skills section?" or "Customize this resume for a Senior role."</p>
                      </div>
                    ) : (
                      chatHistory.map((msg, i) => (
                        <div key={i} className={cn("flex flex-col mb-6", msg.role === 'user' ? "items-end" : "items-start")}>
                          <div className={cn(
                            "max-w-[92%] px-6 py-4 rounded-3xl text-sm leading-relaxed",
                            msg.role === 'user'
                              ? "bg-purple-600 text-white rounded-tr-none shadow-[0_4px_12px_rgba(147,51,234,0.3)]"
                              : "bg-white/[0.03] text-slate-300 border border-white/10 rounded-tl-none shadow-xl"
                          )}>
                            <FormattedMessage
                              content={msg.content}
                              isLatest={i === chatHistory.length - 1}
                              isModel={msg.role === 'model'}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="p-6 border-t border-white/5 bg-black/40">
                    <form onSubmit={askQuestion} className="relative">
                      <input 
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Type your message..."
                        className="w-full bg-white/[0.03] border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm focus:ring-1 focus:ring-purple-500/50 outline-none transition-all"
                      />
                      <button 
                        type="submit"
                        className="absolute right-2 top-2 w-8 h-8 rounded-lg bg-white/5 hover:bg-white text-slate-400 hover:text-black flex items-center justify-center transition-all"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </form>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Floating Taskbar - Moved to Right Center */}
      <div className="fixed right-0 top-1/2 -translate-y-1/2 z-50">
        <motion.button
          whileHover={{ x: -10 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => setIsDevModalOpen(true)}
          className="flex flex-col items-center gap-4 py-8 px-3 bg-white/[0.05] hover:bg-white/[0.1] backdrop-blur-xl border border-white/10 rounded-l-[40px] shadow-[0_8px_32px_rgba(0,0,0,0.6)] transition-all duration-300 group"
        >
          <div className="flex flex-col -space-y-2">
            {['shashanklko', 'SumitSingh3101', 'Srinayan-96'].map(user => (
              <img 
                key={user}
                src={`https://github.com/${user}.png`} 
                alt={user} 
                className="w-6 h-6 rounded-full border border-white/20 group-hover:border-purple-500/50 transition-colors"
              />
            ))}
          </div>
          <span className="[writing-mode:vertical-lr] text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 group-hover:text-white transition-colors">
            Meet Developers
          </span>
        </motion.button>
      </div>

      {/* Developer Modal */}
      <AnimatePresence>
        {isDevModalOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsDevModalOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl px-6 z-[70]"
            >
              <div className="bg-[#111114] border border-white/10 rounded-[40px] p-10 shadow-2xl overflow-hidden relative">
                <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 blur-[100px] -mr-32 -mt-32" />
                
                <div className="flex items-center justify-between mb-10 relative z-10">
                  <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                    <Users className="text-purple-400" /> The Creators
                  </h2>
                  <button 
                    onClick={() => setIsDevModalOpen(false)}
                    className="p-2 hover:bg-white/5 rounded-full text-slate-500 hover:text-white transition-all"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
                  {[
                    { name: 'Shashank Kumar', id: 'shashanklko', role: 'Software Engineer' },
                    { name: 'Sumit Singh', id: 'SumitSingh3101', role: 'Software Engineer' },
                    { name: 'Srinayan', id: 'Srinayan-96', role: 'Software Engineer' }
                  ].map(dev => (
                    <a 
                      key={dev.id}
                      href={`https://github.com/${dev.id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group p-6 bg-white/[0.02] hover:bg-white/[0.05] border border-white/5 hover:border-white/10 rounded-3xl transition-all duration-300 flex flex-col items-center text-center"
                    >
                      <div className="relative mb-4">
                        <div className="absolute -inset-1 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full blur opacity-0 group-hover:opacity-40 transition duration-500" />
                        <img 
                          src={`https://github.com/${dev.id}.png`} 
                          alt={dev.name} 
                          className="relative w-20 h-20 rounded-full border-2 border-white/10" 
                        />
                      </div>
                      <h3 className="text-sm font-bold text-white group-hover:text-purple-400 transition-colors mb-1">{dev.name}</h3>
                      <p className="text-[9px] text-slate-500 uppercase tracking-[0.2em] font-extrabold mb-4 whitespace-nowrap">{dev.role}</p>
                      <div className="flex items-center gap-1.5 text-[10px] text-slate-400 group-hover:text-white transition-colors">
                        <GithubIcon className="w-3 h-3" />
                        @{dev.id}
                      </div>
                    </a>
                  ))}
                </div>

                <div className="mt-12 pt-10 border-t border-white/5 text-center relative z-10">
                  <p className="text-[10px] text-slate-600 uppercase tracking-[0.3em] font-medium italic">High Efficiency · Powered by Gemini 3.1 Flash Lite</p>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Donate Modal */}
      <AnimatePresence>
        {isDonateModalOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsDonateModalOpen(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl px-6 z-[70]"
            >
              <div className="bg-[#111114] border border-white/10 rounded-[40px] p-10 shadow-2xl overflow-hidden relative">
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 blur-[100px] -mr-32 -mt-32" />
                
                <div className="flex items-center justify-between mb-8 relative z-10">
                  <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                    <Star className="text-purple-400" /> Support the Project
                  </h2>
                  <button 
                    onClick={() => setIsDonateModalOpen(false)}
                    className="p-2 hover:bg-white/5 rounded-full text-slate-500 hover:text-white transition-all"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
                  {/* Buy Me a Coffee */}
                  <a 
                    href="https://buymeacoffee.com/shashanklko" 
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group p-8 bg-gradient-to-br from-yellow-500/5 to-yellow-500/10 hover:from-yellow-500/10 hover:to-yellow-500/20 border border-yellow-500/20 rounded-3xl transition-all duration-300 flex flex-col items-center text-center"
                  >
                    <div className="w-16 h-16 bg-yellow-500/20 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                      <Coffee className="text-yellow-400 w-8 h-8" />
                    </div>
                    <h3 className="text-lg font-bold text-white mb-2">Buy Me a Coffee</h3>
                    <p className="text-xs text-slate-400 leading-relaxed uppercase tracking-wider font-bold">Quick Support</p>
                  </a>

                  {/* Crypto Donation */}
                  <div className="p-8 bg-white/[0.02] border border-white/10 rounded-3xl">
                    <div className="flex items-center gap-3 mb-6">
                      <Coins className="text-purple-400 w-5 h-5" />
                      <h3 className="text-sm font-black uppercase tracking-[0.2em] text-white">Crypto Wallet</h3>
                    </div>
                    
                    <div className="space-y-4">
                      {[
                        { label: 'BTC', addr: 'bc1qshashanklko...' },
                        { label: 'ETH', addr: '0xshashanklko...' },
                        { label: 'SOL', addr: 'shashanklko...' }
                      ].map(crypto => (
                        <div key={crypto.label} className="flex items-center justify-between p-3 bg-white/5 border border-white/5 rounded-xl hover:border-purple-500/40 transition-all group/item">
                          <div>
                            <p className="text-[10px] font-black text-purple-400 mb-0.5">{crypto.label}</p>
                            <p className="text-xs text-slate-400 font-mono truncate max-w-[120px]">{crypto.addr}</p>
                          </div>
                          <button 
                            onClick={() => {
                              navigator.clipboard.writeText(crypto.addr);
                              setCopyFeedback(crypto.label);
                              setTimeout(() => setCopyFeedback(""), 2000);
                            }}
                            className="p-2 hover:bg-purple-500/20 rounded-lg text-slate-500 hover:text-purple-400 transition-all"
                          >
                            {copyFeedback === crypto.label ? <CheckCircle className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <p className="mt-8 text-center text-[10px] text-slate-500 uppercase tracking-widest leading-relaxed">
                  Your support helps us keep the AI engine running and completely free for the developer community.
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <footer className="relative z-10 py-12 border-t border-white/5 text-center mt-20 opacity-0 pointer-events-none">
        {/* Hidden reserved space for layout stability */}
      </footer>
    </div>
  );
}
