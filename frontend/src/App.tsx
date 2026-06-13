import React, { useState, useEffect, useMemo } from 'react';
import {
  Settings, RefreshCw, Wand2, Image as ImageIcon,
  CheckCircle2, XCircle, Activity, Sparkles, Compass, Maximize2
} from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: (string | undefined | null | false)[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = `http://127.0.0.1:${import.meta.env.VITE_BACKEND_PORT || 15001}`;

function extractLoras(prompt: string) {
  const regex = /<lora:([^:>]+)[^>]*>/g;
  const loras = [];
  let match;
  while ((match = regex.exec(prompt)) !== null) {
    loras.push(match[1]);
  }
  return loras;
}

export default function App() {
  const [sdConnected, setSdConnected] = useState<boolean | null>(null);
  const [sdUrl, setSdUrl] = useState<string>('');

  const [prompt, setPrompt] = useState<string>(() => sessionStorage.getItem('sd_prompt') || '');
  const [idea, setIdea] = useState<string>(() => sessionStorage.getItem('sd_idea') || '');
  const [attempts, setAttempts] = useState<number>(() => Number(sessionStorage.getItem('sd_attempts')) || 1);

  const [isGenerating, setIsGenerating] = useState(false);
  const [progressMsg, setProgressMsg] = useState('');
  const [progressPercent, setProgressPercent] = useState(0);

  const [results, setResults] = useState<any[]>(() => {
    try {
      const stored = sessionStorage.getItem('sd_results');
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const [selectedImageIndex, setSelectedImageIndex] = useState<number>(0);

  useEffect(() => { sessionStorage.setItem('sd_prompt', prompt); }, [prompt]);
  useEffect(() => { sessionStorage.setItem('sd_idea', idea); }, [idea]);
  useEffect(() => { sessionStorage.setItem('sd_attempts', attempts.toString()); }, [attempts]);
  useEffect(() => { sessionStorage.setItem('sd_results', JSON.stringify(results)); }, [results]);

  const detectedLoras = extractLoras(prompt);

  const checkStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      const data = await res.json();
      setSdConnected(data.connected);
      setSdUrl(data.sdUrl);
    } catch (e) {
      setSdConnected(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || !idea.trim()) return;

    setIsGenerating(true);
    setProgressMsg('⏳ 詠唱魔法準備中...');
    setProgressPercent(0);
    setResults([]);
    setSelectedImageIndex(0);

    try {
      const response = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, idea, attempts })
      });

      if (!response.body) throw new Error('ReadableStream not supported');

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '');
            if (!dataStr.trim()) continue;

            try {
              const data = JSON.parse(dataStr);
              if (data.type === 'progress' || data.type === 'heartbeat') {
                setProgressMsg(data.message);
                if (data.total > 0) {
                  setProgressPercent((data.completed / data.total) * 100);
                }
              } else if (data.type === 'done') {
                const resArray = Object.values(data.results || {}) as any[];
                setResults(resArray);
                setProgressMsg('✨ 魔法生成完畢！');
                setProgressPercent(100);
              }
            } catch (e) {
              console.error("JSON Error", e, dataStr);
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      setProgressMsg('❌ 連線中斷，請確認服務運行。');
    } finally {
      setIsGenerating(false);
    }
  };

  // 生成展示專用的平坦圖片清單
  const allImages = useMemo(() => {
    const list: { url: string; prompt: string; attempt_num: number }[] = [];
    results.forEach(r => {
      if (r.saved_paths && r.saved_paths.length > 0) {
        r.saved_paths.forEach((imgPath: string) => {
          const parts = imgPath.split(/[\\/]/);
          const outputsIdx = parts.indexOf("outputs");
          const relativePath = outputsIdx !== -1 ? parts.slice(outputsIdx + 1).join("/") : imgPath.split(/[\\/]/).pop();
          const fileUrl = `${API_BASE}/outputs/${relativePath}`;
          list.push({
            url: fileUrl,
            prompt: r.modified_prompt,
            attempt_num: r.attempt_num
          });
        });
      }
    });
    return list;
  }, [results]);

  // 新生成結果傳回時，預設顯示第一張，同步 Prompt
  useEffect(() => {
    if (allImages.length > 0 && !isGenerating) {
      handleSelectImage(0);
    }
  }, [allImages.length, isGenerating]);

  // 工具函式：更換主要顯示圖片的同時，同步提示詞
  const handleSelectImage = (index: number) => {
    setSelectedImageIndex(index);
    if (allImages[index]) {
      setPrompt(allImages[index].prompt);
    }
  };

  const loraColors = [
    "bg-rose-400 dark:bg-rose-500", "bg-orange-400 dark:bg-orange-500",
    "bg-fuchsia-400 dark:bg-fuchsia-500", "bg-emerald-400 dark:bg-emerald-500",
    "bg-blue-400 dark:bg-blue-500", "bg-indigo-400 dark:bg-indigo-500"
  ];

  return (
    <>
      <div className="min-h-screen relative overflow-hidden transition-colors duration-500 pb-16">

        {/* 背景光點塊 (動漫風散景) */}
        <div className="fixed top-[-10%] left-[-10%] w-[500px] h-[500px] bg-indigo-400/20 dark:bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none" />
        <div className="fixed bottom-[-10%] right-[-10%] w-[600px] h-[600px] bg-rose-300/20 dark:bg-rose-600/20 rounded-full blur-[120px] pointer-events-none" />

        {/* 頂部導覽列 */}
        <header className="sticky top-0 z-50 glass-panel border-x-0 border-t-0 border-b border-black/5 dark:border-white/5">
          <div className="w-full max-w-[1800px] mx-auto px-6 xl:px-10 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-br from-indigo-500 to-rose-400 rounded-2xl shadow-lg shadow-indigo-500/20 text-white">
                <Sparkles className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-800 dark:text-slate-100 flex items-center gap-2">
                Prompt Editor <span className="bg-clip-text text-transparent bg-gradient-to-r from-rose-400 to-indigo-500">Pro</span>
              </h1>
            </div>

            <div className="flex items-center space-x-4">
              <button
                onClick={checkStatus}
                className="flex items-center space-x-2 text-sm font-medium px-4 py-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 transition-colors border border-transparent hover:border-black/5 dark:hover:border-white/10 text-slate-600 dark:text-slate-300"
              >
                <RefreshCw className="w-4 h-4" />
                <span className="hidden sm:inline">檢查連線</span>
              </button>
              <div className={cn(
                "flex items-center space-x-2 px-4 py-2 rounded-full text-sm font-medium border shadow-sm transition-all",
                sdConnected === true ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20" :
                  sdConnected === false ? "bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-500/20" :
                    "bg-white/50 dark:bg-white/5 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-800"
              )}>
                {sdConnected === true ? <CheckCircle2 className="w-4 h-4" /> :
                  sdConnected === false ? <XCircle className="w-4 h-4" /> :
                    <Activity className="w-4 h-4 animate-pulse" />}
                <span className="font-mono text-xs">{sdUrl || "Checking..."}</span>
              </div>
            </div>
          </div>
        </header>

        {/* 主內容區 */}
        <main className="w-full max-w-[1800px] mx-auto px-4 sm:px-6 xl:px-10 py-8 grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 relative z-10">

          {/* 左側：控制面板 */}
          <div className="lg:col-span-4 xl:col-span-5 flex flex-col gap-6">
            <div className="glass-panel p-6 sm:p-8 rounded-3xl flex flex-col gap-6 relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 dark:bg-indigo-400/5 rounded-full blur-[40px] translate-x-10 -translate-y-10 group-hover:bg-indigo-500/10 transition-colors" />

              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-50 dark:bg-indigo-500/20 rounded-xl text-indigo-500 dark:text-indigo-400">
                  <Compass className="w-5 h-5" />
                </div>
                <h2 className="text-lg font-bold text-slate-800 dark:text-slate-100">靈感控制台</h2>
              </div>

              <div className="space-y-5">
                {/* 原始 Prompt 輸入框 */}
                <div className="relative">
                  <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 ml-1">
                    當前 Prompt（含 LoRA）
                  </label>
                  <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="點擊右側圖片可自動帶入對應 Prompt，或在此手動修改..."
                    className="w-full h-40 bg-white/50 dark:bg-black/30 backdrop-blur-md border border-slate-200 dark:border-white/10 rounded-2xl p-4 text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-400/50 transition-all resize-none shadow-inner scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700 placeholder:text-slate-400 dark:placeholder:text-slate-500 font-mono"
                  />

                  {/* LoRA Badges */}
                  <div className="mt-3 flex flex-wrap gap-2 min-h-[28px] ml-1">
                    {detectedLoras.length > 0 ? (
                      detectedLoras.map((lora, idx) => (
                        <span key={idx} className={cn(
                          "px-3 py-1.5 text-xs font-bold text-white rounded-full shadow-sm flex items-center gap-1.5 border border-white/20",
                          loraColors[idx % loraColors.length]
                        )}>
                          <Settings className="w-3.5 h-3.5 opacity-90" />
                          {lora}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500 dark:text-slate-400 italic">尚未偵測到 LoRA 標籤</span>
                    )}
                  </div>
                </div>

                {/* 修改想法輸入框 */}
                <div className="relative">
                  <label className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300 mb-2 ml-1">
                    <span className="text-rose-500 dark:text-rose-400">✨ AI 魔法修改想法</span>
                  </label>
                  <textarea
                    value={idea}
                    onChange={(e) => setIdea(e.target.value)}
                    placeholder="例如：換成賽博龐克風格、加入粉色頭髮..."
                    className="w-full h-24 bg-rose-50/50 dark:bg-rose-500/5 backdrop-blur-md border border-rose-200 dark:border-rose-500/20 rounded-2xl p-4 text-sm text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-400/50 transition-all resize-none shadow-inner placeholder:text-rose-300 dark:placeholder:text-rose-500/50"
                  />
                </div>

                {/* 嘗試次數 */}
                <div className="bg-white/40 dark:bg-black/20 p-4 rounded-2xl border border-slate-200 dark:border-white/5">
                  <div className="flex justify-between items-center mb-3">
                    <label className="text-sm font-bold text-slate-700 dark:text-slate-300">生成次數</label>
                  </div>
                  <div className="flex items-center gap-4">
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={attempts}
                      onChange={(e) => setAttempts(Number(e.target.value))}
                      className="flex-1 accent-indigo-500 h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={attempts}
                      onChange={(e) => setAttempts(Number(e.target.value))}
                      className="w-16 px-1 py-1 text-base font-black text-indigo-600 dark:text-indigo-400 text-center bg-white/60 dark:bg-black/40 border border-slate-300 dark:border-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                    />
                  </div>
                </div>
              </div>

              {/* 執行按鈕 */}
              <div className="mt-4">
                <button
                  onClick={handleGenerate}
                  disabled={isGenerating || !prompt.trim() || !idea.trim()}
                  className={cn(
                    "relative w-full overflow-hidden rounded-2xl font-bold shadow-xl transition-all duration-300 transform",
                    (!prompt.trim() || !idea.trim() || isGenerating)
                      ? "opacity-50 cursor-not-allowed bg-slate-400 dark:bg-slate-700 text-white"
                      : "bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-rose-500 hover:-translate-y-1 hover:shadow-fuchsia-500/30 text-white background-animate group/btn"
                  )}
                >
                  <div className="px-6 py-4 flex items-center justify-center space-x-2 relative z-10">
                    {isGenerating ? (
                      <RefreshCw className="w-5 h-5 animate-spin" />
                    ) : (
                      <Wand2 className="w-5 h-5 transition-transform group-hover/btn:scale-125 group-hover/btn:rotate-12" />
                    )}
                    <span className="text-[15px] tracking-wide">{isGenerating ? 'AI 魔法詠唱中...' : '開始注入靈感生圖'}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>

          {/* 右側：主成果展示面板 */}
          <div className="lg:col-span-8 xl:col-span-7 flex flex-col gap-6 h-[calc(100vh-8rem)] min-h-[600px]">

            {/* 進度狀態卡片 */}
            <div className={cn(
              "glass-panel rounded-3xl p-5 sm:px-8 sm:py-6 transition-all duration-500 animate-in fade-in slide-in-from-top-4",
              (isGenerating || progressMsg) ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-4 hidden"
            )}>
              <div className="flex justify-between items-center mb-3 text-sm">
                <span className="font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-2">
                  <Activity className={cn("w-4 h-4", isGenerating && "animate-pulse")} />
                  {progressMsg}
                </span>
                <span className="text-slate-500 dark:text-slate-400 font-mono font-bold bg-white/50 dark:bg-black/30 px-3 py-1 rounded-full shadow-inner">{Math.round(progressPercent)}%</span>
              </div>
              <div className="h-2.5 w-full bg-slate-200/50 dark:bg-slate-800/50 rounded-full overflow-hidden shadow-inner flex">
                <div
                  className={cn(
                    "h-full rounded-full transition-all duration-500 ease-out relative overflow-hidden",
                    progressPercent === 100
                      ? "bg-gradient-to-r from-emerald-400 to-teal-500"
                      : "bg-gradient-to-r from-indigo-400 via-fuchsia-400 to-rose-400 background-animate"
                  )}
                  style={{ width: `${progressPercent}%` }}
                >
                  {isGenerating && (
                    <div className="absolute inset-0 bg-white/20 w-8 blur-sm -skew-x-12 animate-[shimmer_2s_infinite]" />
                  )}
                </div>
              </div>
            </div>

            {/* Gallery */}
            <div className="glass-panel flex-1 rounded-3xl border border-white/50 dark:border-white/10 overflow-hidden flex flex-col shadow-2xl relative">
              <div className="px-6 py-5 border-b border-slate-200/50 dark:border-white/5 bg-white/40 dark:bg-slate-900/40 backdrop-blur-md flex items-center justify-between z-10 sticky top-0">
                <h2 className="font-bold text-lg flex items-center gap-2 text-slate-800 dark:text-slate-100">
                  <ImageIcon className="w-5 h-5 text-fuchsia-500" />
                  <span>生成畫廊展示區</span>
                </h2>
              </div>

              <div className="flex-1 overflow-hidden relative flex flex-col items-center bg-slate-100/30 dark:bg-black/20">
                {allImages.length > 0 ? (
                  <div className="w-full h-full flex flex-col pt-4 px-4 pb-2">
                    {/* 主要圖片視窗 (大圖展示) */}
                    <div className="relative flex-1 w-full flex items-center justify-center rounded-2xl overflow-hidden mb-4">
                      {/* 背景模糊填補框 為了讓長條動漫圖片更美觀 */}
                      {allImages[selectedImageIndex] && (
                        <div
                          className="absolute inset-0 bg-cover bg-center blur-3xl opacity-30 dark:opacity-20 transform scale-110"
                          style={{ backgroundImage: `url(${allImages[selectedImageIndex].url})` }}
                        />
                      )}
                      <img
                        src={allImages[selectedImageIndex]?.url}
                        alt="Main Generated"
                        className="relative z-10 w-auto h-full max-h-[65vh] object-contain drop-shadow-2xl rounded-lg transition-opacity duration-300"
                      />
                      <div className="absolute top-4 right-4 z-20 bg-black/60 backdrop-blur-sm text-white px-4 py-1.5 rounded-full text-xs font-black tracking-widest border border-white/20 shadow-lg">
                        ATTEMPT {allImages[selectedImageIndex]?.attempt_num}
                      </div>
                      <div className="absolute bottom-4 right-4 z-20 bg-emerald-500/80 backdrop-blur-sm text-white px-3 py-1.5 rounded-full text-xs font-bold border border-white/20 shadow-lg flex items-center gap-1.5 opacity-80 hover:opacity-100 cursor-pointer transition-opacity" title="圖片的 Prompt 已同步至左側">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        已同步 Prompt
                      </div>
                    </div>

                    {/* 下方縮圖序列 */}
                    <div className="h-24 sm:h-28 w-full">
                      <div className="flex items-center gap-3 overflow-x-auto w-full h-full px-2 py-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-700">
                        {allImages.map((img, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSelectImage(idx)}
                            className={cn(
                              "relative flex-shrink-0 aspect-square h-16 sm:h-20 rounded-xl overflow-hidden shadow-md transition-all duration-200 outline-none",
                              selectedImageIndex === idx
                                ? "ring-2 ring-indigo-500 ring-offset-2 ring-offset-transparent scale-[1.05] opacity-100 shadow-indigo-500/50"
                                : "ring-1 ring-black/10 dark:ring-white/10 opacity-60 hover:opacity-100 hover:scale-[1.02]"
                            )}
                          >
                            <img src={img.url} alt={`thumb ${idx}`} className="w-full h-full object-cover" />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : isGenerating ? (
                  <div className="h-full flex flex-col items-center justify-center text-indigo-500/60 dark:text-indigo-400/50">
                    <div className="relative">
                      <div className="w-24 h-24 border-[6px] border-indigo-200 dark:border-indigo-900/50 rounded-full" />
                      <div className="w-24 h-24 border-[6px] border-indigo-500 dark:border-indigo-400 rounded-full absolute top-0 left-0 border-t-transparent border-l-transparent animate-spin" />
                      <Sparkles className="absolute inset-0 m-auto w-8 h-8 animate-pulse text-rose-400" />
                    </div>
                    <p className="mt-6 font-bold tracking-wide animate-pulse">正在調配圖元魔法...</p>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 dark:text-slate-600">
                    <div className="w-32 h-32 bg-slate-200/50 dark:bg-slate-800/50 rounded-full flex items-center justify-center mb-6 shadow-inner border border-white/50 dark:border-white/5">
                      <ImageIcon className="w-12 h-12 text-slate-300 dark:text-slate-500" />
                    </div>
                    <p className="font-bold tracking-wide text-center px-4">填寫左側靈感控制台<br />見證 AI 賦予畫像新生命</p>
                  </div>
                )}
              </div>

            </div>
          </div>

        </main>

        <style dangerouslySetInnerHTML={{
          __html: `
          .background-animate {
            background-size: 200% 200%;
            animation: GradientFlow 4s ease infinite;
          }
          @keyframes GradientFlow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
          }
          @keyframes shimmer {
            100% { transform: translateX(300px); }
          }
        `}} />
      </div>
    </>
  );
}
