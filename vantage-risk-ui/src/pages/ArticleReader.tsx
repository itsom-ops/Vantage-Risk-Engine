import { useEffect, useState, useMemo } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ExternalLink, Clock, User, Globe, Loader2 } from "lucide-react";
import { extractArticle, getStockQuote, type ArticleContent, type NewsItem } from "../api/api";
import { ImpactPredictor } from "../components/ImpactPredictor";

export function ArticleReader() {
  const { ticker, articleIndex } = useParams<{ ticker: string; articleIndex: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  // Get news item from navigation state
  const newsItem: NewsItem | null = (location.state as any)?.newsItem ?? null;
  const companyName: string = (location.state as any)?.companyName ?? ticker?.toUpperCase() ?? "";

  const [article, setArticle] = useState<ArticleContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentPrice, setCurrentPrice] = useState<number>(100);

  const tickerUpper = ticker?.toUpperCase() ?? "";

  // Fetch article content
  useEffect(() => {
    if (!newsItem?.link) {
      setLoading(false);
      return;
    }
    setLoading(true);
    extractArticle(newsItem.link)
      .then(setArticle)
      .catch(() => setArticle(null))
      .finally(() => setLoading(false));
  }, [newsItem?.link]);

  // Fetch current price for impact predictor
  useEffect(() => {
    if (!tickerUpper) return;
    getStockQuote(tickerUpper)
      .then((q) => setCurrentPrice(q.price))
      .catch(() => {});
  }, [tickerUpper]);

  // Map sentiment label
  const sentimentLabel = useMemo(() => {
    if (!newsItem) return "Neutral" as const;
    return newsItem.sentiment;
  }, [newsItem]);

  const sentimentScore = useMemo(() => {
    if (!newsItem) return 0.5;
    // Normalize the score to 0-1 range
    return Math.max(0, Math.min(1, (newsItem.score + 1) / 2));
  }, [newsItem]);

  if (!newsItem) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="glass-card p-8 text-center space-y-4">
          <p className="text-[#1C1C1C] font-semibold">No article data available.</p>
          <button onClick={() => navigate(-1)} className="btn-primary">
            <ArrowLeft size={14} /> Go Back
          </button>
        </div>
      </div>
    );
  }

  const displayTitle = article?.success ? article.title : newsItem.headline;
  const displayText = article?.success ? article.text : null;
  const displayImage = article?.top_image ?? null;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-40 px-6 py-3 border-b border-navy-700 bg-navy-950">
        <div className="max-w-screen-xl mx-auto flex items-center justify-between gap-4">
          <button
            onClick={() => navigate(`/stock/${tickerUpper}`)}
            className="flex items-center gap-2 text-sm text-stone-500 hover:text-[#1C1C1C] transition-colors"
          >
            <ArrowLeft size={16} />
            Back to {tickerUpper}
          </button>

          <a
            href={newsItem.link}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost text-xs"
          >
            <ExternalLink size={12} />
            Original Source
          </a>
        </div>
      </header>

      <main className="flex-1 max-w-screen-xl mx-auto w-full px-6 py-8">
        {/* ── Hero Image ───────────────────────────────────────── */}
        {displayImage && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-h-[400px] rounded-2xl overflow-hidden mb-8 border border-navy-700"
          >
            <img
              src={displayImage}
              alt={displayTitle}
              className="w-full h-full object-cover"
              style={{ maxHeight: 400 }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
            />
          </motion.div>
        )}

        {/* ── Article Content ──────────────────────────────────── */}
        <motion.article
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="max-w-[720px] mx-auto"
        >
          {/* Ticker badge + sentiment */}
          <div className="flex items-center gap-3 mb-4">
            <span className="ticker-label text-xs">{tickerUpper}</span>
            <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase
              ${sentimentLabel === "Bullish" ? "badge-low" :
                sentimentLabel === "Bearish" ? "badge-high" : "badge-medium"}`}>
              {sentimentLabel}
            </span>
          </div>

          {/* Title */}
          <h1 className="text-3xl font-serif font-bold text-[#1C1C1C] leading-tight mb-4">
            {displayTitle}
          </h1>

          {/* Meta info */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-stone-500 mb-8 pb-6 border-b border-navy-700">
            {article?.author && (
              <span className="flex items-center gap-1">
                <User size={12} />
                {article.author}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Globe size={12} />
              {article?.source_domain ?? newsItem.publisher}
            </span>
            {article?.publish_date && (
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {new Date(article.publish_date).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </span>
            )}
            {article?.word_count ? (
              <span className="text-stone-400">
                {article.word_count} words · {Math.ceil(article.word_count / 250)} min read
              </span>
            ) : null}
          </div>

          {/* Article Body */}
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 size={24} className="animate-spin text-stone-400" />
              <span className="ml-3 text-sm text-stone-500">Extracting article content…</span>
            </div>
          ) : displayText ? (
            <div className="article-body">
              {displayText.split("\n\n").map((paragraph, i) => (
                <p key={i} className="mb-4">
                  {paragraph}
                </p>
              ))}
            </div>
          ) : (
            <div className="rounded-xl bg-navy-900 border border-navy-700 p-8 text-center space-y-4">
              <p className="text-sm text-stone-500">
                This article could not be extracted automatically. The source may require a subscription or uses JavaScript-only rendering.
              </p>
              {newsItem.summary && (
                <div className="text-left rounded-lg bg-navy-950 p-4 border border-navy-700">
                  <p className="text-xs text-stone-500 font-mono uppercase mb-2">Article Summary</p>
                  <p className="text-sm text-[#1C1C1C] leading-relaxed">{newsItem.summary}</p>
                </div>
              )}
              <a
                href={newsItem.link}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary inline-flex"
              >
                <ExternalLink size={14} />
                Read on Original Site
              </a>
            </div>
          )}

          {/* Credit Forecast */}
          {newsItem.effect && (
            <div className="mt-8 p-4 rounded-xl bg-navy-900 border-l-4 border-electric-500 border border-navy-700">
              <p className="text-[10px] font-mono text-electric-500 font-bold uppercase tracking-wider mb-1">
                Credit Forecast
              </p>
              <p className="text-xs text-[#1C1C1C] leading-relaxed">{newsItem.effect}</p>
            </div>
          )}
        </motion.article>

        {/* ── Predicted Market Impact ──────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="max-w-[720px] mx-auto mt-12 glass-card p-6"
        >
          <ImpactPredictor
            sentimentScore={sentimentScore}
            sentimentLabel={sentimentLabel}
            currentPrice={currentPrice}
          />
        </motion.div>

        {/* ── Back to stock link ───────────────────────────────── */}
        <div className="max-w-[720px] mx-auto mt-8 text-center">
          <button
            onClick={() => navigate(`/stock/${tickerUpper}`)}
            className="btn-ghost text-sm"
          >
            <ArrowLeft size={14} />
            Back to {companyName || tickerUpper} Analysis
          </button>
        </div>
      </main>
    </div>
  );
}
