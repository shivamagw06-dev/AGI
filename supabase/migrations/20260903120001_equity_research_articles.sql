ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS article_type text NOT NULL DEFAULT 'article';
ALTER TABLE public.articles ADD COLUMN IF NOT EXISTS equity_research jsonb;
ALTER TABLE public.articles DROP CONSTRAINT IF EXISTS articles_article_type_check;
ALTER TABLE public.articles ADD CONSTRAINT articles_article_type_check CHECK (article_type IN ('article', 'equity_research'));
COMMENT ON COLUMN public.articles.article_type IS 'Public presentation type: standard article or institutional equity research report.';
COMMENT ON COLUMN public.articles.equity_research IS 'Structured cover-sheet metadata for equity research: company, ticker, stance, valuation and analyst details.';
