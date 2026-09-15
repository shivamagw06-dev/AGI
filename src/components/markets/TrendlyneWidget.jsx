import { useEffect, useRef } from "react";

const SCRIPT_SRC = "https://cdn-static.trendlyne.com/static/js/webwidgets/tl-widgets.js";
let scriptPromise = null;

function loadTrendlyneScript() {
  if (scriptPromise) return scriptPromise;
  scriptPromise = new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${SCRIPT_SRC}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.charset = "utf-8";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Trendlyne widget script failed to load"));
    document.body.appendChild(script);
  });
  return scriptPromise;
}

const STYLE = {
  posCol: "00A25B",
  primaryCol: "006AFF",
  negCol: "EB3B00",
  neuCol: "F7941E",
};

export function buildTrendlyneUrls(symbol) {
  const s = encodeURIComponent(symbol.toUpperCase());
  const q = `posCol=${STYLE.posCol}&primaryCol=${STYLE.primaryCol}&negCol=${STYLE.negCol}&neuCol=${STYLE.neuCol}`;
  return {
    swot: `https://trendlyne.com/web-widget/swot-widget/Poppins/${s}/?${q}`,
    technical: `https://trendlyne.com/web-widget/technical-widget/Poppins/${s}/?${q}`,
    ipo: "https://trendlyne.com/web-widget/ipo-widget/Poppins/?activeCol=006AFF&linksCol=006CFF&primary=202020&secondary=666666&positive=00a25b&negative=ff4e54",
  };
}

export default function TrendlyneWidget({ dataUrl, title, subtitle, minHeight = 420, className = "" }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const el = mountRef.current;
    if (!el || !dataUrl) return;

    el.innerHTML = "";
    const blockquote = document.createElement("blockquote");
    blockquote.className = "trendlyne-widgets";
    blockquote.setAttribute("data-get-url", dataUrl);
    blockquote.setAttribute("data-theme", "light");
    el.appendChild(blockquote);

    let active = true;
    loadTrendlyneScript()
      .then(() => {
        if (active) window.TLWidgets?.init?.();
      })
      .catch(() => {});

    return () => {
      active = false;
    };
  }, [dataUrl]);

  return (
    <div className={`rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden ${className}`}>
      {(title || subtitle) && (
        <div className="border-b border-slate-100 px-6 py-4">
          {title && <h3 className="text-base font-semibold text-slate-900">{title}</h3>}
          {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
      )}
      <div ref={mountRef} className="p-4 w-full" style={{ minHeight }} />
    </div>
  );
}
