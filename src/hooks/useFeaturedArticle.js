import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

function formatPublishedDate(dateString) {
  if (!dateString) return "Recently published";

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "Recently published";

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfPublishDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = Math.round((startOfToday - startOfPublishDay) / (1000 * 60 * 60 * 24));

  if (dayDiff === 0) return "Published today";
  if (dayDiff === 1) return "Published yesterday";
  if (dayDiff < 7) return `Published ${dayDiff} days ago`;

  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function useFeaturedArticle() {
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function loadFeaturedArticle() {
      setLoading(true);
      setError(null);

      const { data, error: fetchError } = await supabase
        .from("articles")
        .select("id, title, slug, excerpt, section, tags, published_at, cover_url")
        .eq("status", "published")
        .order("published_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (cancelled) return;

      if (fetchError) {
        console.error("Failed to load featured article:", fetchError);
        setArticle(null);
        setError(fetchError.message);
      } else {
        setArticle(
          data
            ? {
                ...data,
                category:
                  data.section ||
                  (Array.isArray(data.tags) && data.tags.length ? data.tags[0] : "Research"),
                publishedLabel: formatPublishedDate(data.published_at),
              }
            : null
        );
      }

      setLoading(false);
    }

    loadFeaturedArticle();

    return () => {
      cancelled = true;
    };
  }, []);

  return { article, loading, error };
}
