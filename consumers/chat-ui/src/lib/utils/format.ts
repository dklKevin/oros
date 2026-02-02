import type { DocumentAuthor } from '@/lib/api/types';

export function formatDate(dateString: string | undefined): string {
  if (!dateString) return 'Unknown date';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateString;
  }
}

export function formatAuthors(authors: DocumentAuthor[] | string[] | undefined): string {
  if (!authors || authors.length === 0) return 'Unknown authors';

  const names = authors.map((author) => {
    if (typeof author === 'string') return author;
    return author.name;
  });

  if (names.length === 1) return names[0];
  if (names.length === 2) return names.join(' and ');
  if (names.length > 3) return `${names[0]} et al.`;
  return `${names.slice(0, -1).join(', ')}, and ${names[names.length - 1]}`;
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3) + '...';
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(1) + '%';
}

export function formatTokenCount(count: number | undefined): string {
  if (count === undefined) return '';
  return `${count.toLocaleString()} tokens`;
}

export function highlightText(text: string, query: string): string {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
  return text.replace(regex, '<mark class="bg-accent/30 text-text-primary">$1</mark>');
}

function escapeRegex(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function getDoiUrl(doi: string | undefined): string | undefined {
  if (!doi) return undefined;
  return `https://doi.org/${doi}`;
}

export function getPubMedUrl(pmcid: string | undefined): string | undefined {
  if (!pmcid) return undefined;
  return `https://www.ncbi.nlm.nih.gov/pmc/articles/${pmcid}/`;
}
