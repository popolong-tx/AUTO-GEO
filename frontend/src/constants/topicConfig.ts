/**
 * Shared topic configuration constants used across components.
 */

export const TOPIC_I18N_KEYS: Record<string, { name: string; description: string }> = {
  'goodwood-festival': { name: 'topic.goodwood.name', description: 'topic.goodwood.description' },
  'flash-charge-launch': { name: 'topic.flashCharge.name', description: 'topic.flashCharge.description' },
  'q1-financial-report': { name: 'topic.q1Report.name', description: 'topic.q1Report.description' },
  'smart-chip-launch': { name: 'topic.smartChip.name', description: 'topic.smartChip.description' },
  'dod-1260h-list': { name: 'topic.dod1260h.name', description: 'topic.dod1260h.description' },
  'custom-report': { name: 'topic.custom.name', description: 'topic.custom.description' },
};

export const OVERSEAS_TOPICS = ['goodwood-festival', 'dod-1260h-list'];
