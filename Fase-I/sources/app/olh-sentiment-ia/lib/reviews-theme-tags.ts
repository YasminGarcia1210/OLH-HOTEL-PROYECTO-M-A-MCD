import type { ReviewListItem } from "@/lib/reviews-api";
import type { ReviewsFilterBarData } from "@/lib/reviews-types";

const MORE_SLUG = "__more__";

export function buildThemeTagsFromItems(
  items: ReviewListItem[],
  activeSlug?: string,
): ReviewsFilterBarData["themeTags"] {
  const map = new Map<string, string>();
  for (const it of items) {
    for (const t of it.topicos ?? []) {
      if (!map.has(t.slug)) {
        map.set(t.slug, t.nombre);
      }
    }
  }

  const pairs = [...map.entries()].sort((a, b) =>
    a[1].localeCompare(b[1], "es"),
  );
  const max = 8;
  const shown = pairs.slice(0, max);
  const rest = Math.max(0, pairs.length - max);

  const tags = shown.map(([slug, label]) => ({
    slug,
    label,
    active: activeSlug === slug,
  }));

  if (rest > 0) {
    tags.push({
      slug: MORE_SLUG,
      label: `+${rest} más`,
      active: false,
    });
  }

  return tags;
}

export function isMoreThemesSlug(slug: string): boolean {
  return slug === MORE_SLUG;
}
