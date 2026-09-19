import IndiaAiInfrastructureStrategy from './IndiaAiInfrastructureStrategy';

/**
 * Every strategy on the strategy page, in display order.
 *
 * To add one: write its table component (see IndiaAiInfrastructureStrategy)
 * and add an entry here. `monitor` is the backend view that holds the
 * evidence and figures behind the strategy; its button sits above the table,
 * with the strategy's published `report` (optional) to its right.
 */
export const STRATEGIES = [
  {
    id: 'india-ai-infrastructure',
    title: 'India AI Infrastructure',
    sector: 'Technology infrastructure · India',
    summary: 'Listed Indian companies building the physical layer of AI: compute, connectivity, data centres, cooling, electrical equipment, backup power, cables, AI electricity and the grid. Selected on direct AI revenue, orders and contracted capacity, then weighed against capital quality and what today\'s price already expects.',
    monitor: { label: 'Open the AI Monitor', to: '/india-ai#monitor' },
    // The published report (PDF in public/reports), opened beside the monitor button.
    report: { label: 'Report', href: '/reports/AGI_India_AI_Infrastructure_19_Sep_2026.pdf' },
    Component: IndiaAiInfrastructureStrategy,
  },
];
