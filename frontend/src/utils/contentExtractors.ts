/**
 * Utility functions to extract structured data from analysis content.
 * Used as fallback when dashboard data is not available.
 */

export interface TrendDataPoint {
  date: string;
  mentions: number;
  reach: number;
}

export interface CountryCoverageItem {
  country: string;
  value: number;
}

/**
 * Extract trend data from analysis content when dashboard data is empty.
 */
export const extractTrendFromContent = (content: string): TrendDataPoint[] => {
  if (!content) return [];

  const byDate: Record<string, TrendDataPoint> = {};

  // Find trend section
  const trendMarkers = ['【趋势统计】', '【Trend Statistics】', '[Trend Statistics]', '## Trend Statistics'];
  const endMarkers = ['【国家覆盖】', '【引用备注】', '【参考文献】', '[Country Coverage]', '[Citation Notes]', '[References]', '## Country Coverage', '## Citation Notes', '## References', '【社交媒体最新信息】', '[Latest Social Updates]'];

  let section = '';
  for (const marker of trendMarkers) {
    const idx = content.indexOf(marker);
    if (idx !== -1) {
      let end = content.length;
      for (const em of endMarkers) {
        const pos = content.indexOf(em, idx + marker.length);
        if (pos !== -1 && pos < end) end = pos;
      }
      section = content.slice(idx + marker.length, end).trim();
      break;
    }
  }

  // Fallback to social media section
  if (!section) {
    const socialMarkers = ['【社交媒体最新信息】', '【Latest Social Updates】', '[Latest Social Updates]', '## Latest Social Updates'];
    for (const marker of socialMarkers) {
      const idx = content.indexOf(marker);
      if (idx !== -1) {
        let end = content.length;
        for (const em of endMarkers) {
          const pos = content.indexOf(em, idx + marker.length);
          if (pos !== -1 && pos < end) end = pos;
        }
        section = content.slice(idx + marker.length, end).trim();
        break;
      }
    }
  }

  if (!section) return [];

  for (const line of section.split('\n')) {
    const text = line.trim();
    if (!text) continue;

    // Extract date
    const dateMatch = text.match(/(?:时间|日期|date)\s*[:：]\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})/i) ||
                      text.match(/\b(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b/);
    if (!dateMatch) continue;

    const date = dateMatch[1].replace(/\//g, '-');
    if (!byDate[date]) byDate[date] = { date, mentions: 0, reach: 0 };
    byDate[date].mentions += 1;

    // Extract reach
    const reachMatch = text.match(/(?:reach|浏览|观看|播放|点赞|转发|互动)\s*[:：]?\s*([\d,]+)/i);
    if (reachMatch) {
      byDate[date].reach += parseInt(reachMatch[1].replace(/,/g, ''), 10) || 0;
    }
  }

  return Object.values(byDate).sort((a, b) => a.date.localeCompare(b.date)).slice(0, 14);
};

/**
 * Extract country coverage from analysis content when dashboard data is empty.
 */
export const extractCountryCoverageFromContent = (content: string, language: string = 'zh'): CountryCoverageItem[] => {
  if (!content) return [];

  const is_en = language === 'en';

  // Country patterns with bilingual names
  const countryPatterns: [RegExp, string, string][] = [
    [/\b(?:US|USA|United States)\b|美国/i, 'United States', '美国'],
    [/\b(?:UK|United Kingdom|Britain)\b|英国/i, 'United Kingdom', '英国'],
    [/\b(?:Germany|DE)\b|德国/i, 'Germany', '德国'],
    [/\b(?:Japan|JP|JPN)\b|日本/i, 'Japan', '日本'],
    [/\b(?:France|FR)\b|法国/i, 'France', '法国'],
    [/\b(?:Canada|CA)\b|加拿大/i, 'Canada', '加拿大'],
    [/\b(?:Australia|AU)\b|澳大利亚/i, 'Australia', '澳大利亚'],
    [/\b(?:India|IN)\b|印度/i, 'India', '印度'],
    [/\b(?:Brazil|BR)\b|巴西/i, 'Brazil', '巴西'],
    [/\b(?:China|CN)\b|中国/i, 'China', '中国'],
    [/\b(?:Korea|KR|South Korea)\b|韩国/i, 'South Korea', '韩国'],
    [/\b(?:Singapore|SG)\b|新加坡/i, 'Singapore', '新加坡'],
    [/\b(?:Europe)\b|欧洲/i, 'Europe', '欧洲'],
    [/\b(?:Global|Worldwide)\b|全球/i, 'Global/Unattributed', '全球/未归属'],
  ];

  // Find country section
  const sectionMarkers = ['【国家覆盖】', '[Country Coverage]', '## Country Coverage'];
  const endMarkers = ['【引用备注】', '【参考文献】', '[Citation Notes]', '[References]', '## Citation Notes', '## References', '【社交媒体最新信息】', '[Latest Social Updates]'];

  let section = '';
  for (const marker of sectionMarkers) {
    const idx = content.indexOf(marker);
    if (idx !== -1) {
      let end = content.length;
      for (const em of endMarkers) {
        const pos = content.indexOf(em, idx + marker.length);
        if (pos !== -1 && pos < end) end = pos;
      }
      section = content.slice(idx + marker.length, end).trim();
      break;
    }
  }

  // Fallback to social media and reference sections
  if (!section) {
    const socialMarkers = ['【社交媒体最新信息】', '【Latest Social Updates】', '[Latest Social Updates]', '## Latest Social Updates'];
    const refMarkers = ['【参考文献】', '[References]', '## References'];
    const sections: string[] = [];

    for (const marker of [...socialMarkers, ...refMarkers]) {
      const idx = content.indexOf(marker);
      if (idx !== -1) {
        let end = content.length;
        for (const em of endMarkers) {
          const pos = content.indexOf(em, idx + marker.length);
          if (pos !== -1 && pos < end) end = pos;
        }
        sections.push(content.slice(idx + marker.length, end).trim());
      }
    }
    section = sections.join('\n');
  }

  if (!section) return [];

  const grouped: Record<string, CountryCoverageItem> = {};

  for (const line of section.split('\n')) {
    const text = line.trim().replace(/^[-*•\d.\s]+/, '');
    if (!text || text.length < 8) continue;

    const urls = text.match(/https?:\/\/[^\s)\]}，。；;、]+/g) || [];
    let foundCountry = '';

    for (const [regex, enName, zhName] of countryPatterns) {
      if (regex.test(text)) {
        foundCountry = is_en ? enName : zhName;
        break;
      }
    }

    if (!foundCountry) continue;
    if (!grouped[foundCountry]) grouped[foundCountry] = { country: foundCountry, value: 0 };
    grouped[foundCountry].value += urls.length > 0 ? urls.length : 1;
  }

  return Object.values(grouped)
    .filter(item => item.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);
};
