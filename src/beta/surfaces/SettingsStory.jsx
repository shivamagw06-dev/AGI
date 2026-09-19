import SurfaceChrome from '@/beta/components/SurfaceChrome';
import { StorySection, InsightCard } from '@/beta/components/Cards';
import DepthSwitch from '@/beta/components/DepthSwitch';
import { Link } from 'react-router-dom';

export default function SettingsStory() {
  return (
    <SurfaceChrome>
      <div className="beta-story-stack">
        <header>
          <p className="beta-kicker">Settings</p>
          <h1 className="beta-h1 mt-2">Reading preferences</h1>
        </header>

        <StorySection title="Depth">
          <InsightCard
            title="Three-layer interface"
            body="Explain in 30 seconds for orientation. Research Report for the magazine scroll. Professional for evidence, runs, and denser detail."
          >
            <div className="mt-4">
              <DepthSwitch />
            </div>
          </InsightCard>
        </StorySection>

        <StorySection title="About this beta">
          <InsightCard
            title="Design prototype"
            body="This beta prototypes AGI’s story-first experience. It reuses existing market and intelligence APIs when available and never invents financial figures for prettier charts."
          >
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/" className="beta-btn-ghost beta-btn">
                Exit to production site
              </Link>
              <Link to="/macro-intelligence" className="beta-btn">
                Macro Intelligence
              </Link>
            </div>
          </InsightCard>
        </StorySection>
      </div>
    </SurfaceChrome>
  );
}
