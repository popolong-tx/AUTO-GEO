/**
 * URL validation utilities for social media and reference links.
 */

/**
 * Check if a URL is a real, valid social media URL (not a placeholder/example).
 */
export const isRealSocialUrl = (url: string): boolean => {
  const lowered = url.toLowerCase();
  if (/(example|placeholder|dummy|fake|\/video\/example|\/post\/example|\/watch\/example)/i.test(lowered)) return false;
  if (/^https?:\/\/(www\.)?(x|twitter|tiktok|youtube|instagram|facebook|reddit|linkedin)\.com\/?$/i.test(lowered)) return false;

  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }

  const host = parsed.hostname.replace(/^www\./, '').toLowerCase();
  const path = parsed.pathname.replace(/^\/+|\/+$/g, '');
  if (!host || !path) return false;

  if (host === 'x.com' || host === 'twitter.com') {
    const parts = path.split('/');
    const statusId = parts[2] || '';
    if (parts.length < 3 || parts[1].toLowerCase() !== 'status') return false;
    if (!/^\d{15,22}$/.test(statusId)) return false;
    if (statusId === '1808123456789123456' || /(123456|234567|345678|456789|567890|678901|789012|890123)/.test(statusId)) return false;
  }

  if (host === 'tiktok.com') {
    const parts = path.split('/');
    const videoId = parts[2] || '';
    if (parts.length < 3 || !parts[0].startsWith('@') || parts[1].toLowerCase() !== 'video') return false;
    if (!/^\d{17,22}$/.test(videoId)) return false;
    if (videoId === '1234567890' || /(1234567890|0123456789|9876543210)/.test(videoId)) return false;
  }

  if (host === 'facebook.com') {
    if (/(posts|videos|photos)\/abc\d+/i.test(path)) return false;
    if (/(posts|videos|photos)\//i.test(path)) {
      const tail = path.split('/').filter(Boolean).pop() || '';
      if (!/^\d{8,}$/.test(tail)) return false;
    }
  }

  return true;
};
