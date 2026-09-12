import { getEntityById } from './entityStore.js';
import { getEntityRelationships } from './relationshipStore.js';
import { listTimelineEvents } from './timelineService.js';

function scoreLabel(score) {
  if (score >= 85) return 'Excellent';
  if (score >= 70) return 'Good';
  if (score >= 50) return 'Needs Enrichment';
  return 'Incomplete';
}

export function computeIntelligenceScore(entityId) {
  const entity = getEntityById(entityId);
  if (!entity) return null;

  const meta = entity.metadata || {};
  const relationships = getEntityRelationships(entityId);
  const timeline = listTimelineEvents(entityId, { limit: 100 });

  let metadataScore = 0;
  const metaFields = ['hq', 'aum', 'industry', 'website', 'logo', 'founded', 'fundSize', 'title'];
  const filled = metaFields.filter((f) => meta[f]).length;
  metadataScore = Math.round((filled / metaFields.length) * 100);

  const relationshipScore = Math.min(100, relationships.length * 8);
  const timelineScore = Math.min(100, timeline.length * 12);
  const descriptionScore = entity.description?.length > 80 ? 100 : entity.description?.length > 20 ? 60 : 20;
  const tagsScore = Math.min(100, (entity.tags?.length || 0) * 20);
  const aiScore = entity.ai_summary?.length > 120 ? 100 : entity.ai_summary?.length > 40 ? 70 : 0;
  const freshnessDays = entity.updated_at
    ? (Date.now() - new Date(entity.updated_at).getTime()) / (86400000)
    : 365;
  const freshnessScore = freshnessDays < 7 ? 100 : freshnessDays < 30 ? 80 : freshnessDays < 90 ? 50 : 25;

  const weights = {
    metadata: 0.2,
    relationships: 0.25,
    timeline: 0.15,
    description: 0.1,
    tags: 0.05,
    ai: 0.15,
    freshness: 0.1,
  };

  const overall = Math.round(
    metadataScore * weights.metadata
    + relationshipScore * weights.relationships
    + timelineScore * weights.timeline
    + descriptionScore * weights.description
    + tagsScore * weights.tags
    + aiScore * weights.ai
    + freshnessScore * weights.freshness
  );

  return {
    score: overall,
    label: scoreLabel(overall),
    factors: {
      metadata_completeness: metadataScore,
      relationship_coverage: relationshipScore,
      timeline_completeness: timelineScore,
      description_quality: descriptionScore,
      tag_coverage: tagsScore,
      ai_summary_quality: aiScore,
      news_freshness: freshnessScore,
    },
  };
}
