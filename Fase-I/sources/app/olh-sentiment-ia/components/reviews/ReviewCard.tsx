import Image from "next/image";

import type { ReviewExplorerItem, TopicScoreTone } from "@/lib/reviews-types";

const borderAccentClass = {
  tertiary: "border-l-tertiary",
  error: "border-l-error",
  primary: "border-l-primary",
} as const;

function sentimentBadgeClass(variant: ReviewExplorerItem["sentimentBadge"]["variant"]): string {
  switch (variant) {
    case "excellent":
      return "border-tertiary/20 bg-tertiary-container/20 text-tertiary";
    case "critical":
      return "border-error/20 bg-error-container/20 text-error";
    case "good":
      return "border-primary/20 bg-primary-container/20 text-primary";
    default:
      return "";
  }
}

function topicChipClass(tone: TopicScoreTone): string {
  switch (tone) {
    case "tertiary":
      return "border-tertiary/20 bg-tertiary-container/20 text-tertiary";
    case "error":
      return "border-error/20 bg-error-container/20 text-error";
    default:
      return "border-primary/20 bg-primary-container/20 text-primary";
  }
}

export function ReviewCard({ item }: { item: ReviewExplorerItem }) {
  return (
    <article
      className={`bg-surface-container overflow-hidden rounded-xl border-l-4 shadow-[0px_12px_32px_rgba(225,226,237,0.02)] ${borderAccentClass[item.borderAccent]}`}
    >
      <div className="p-8">
        <div className="mb-6 flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="bg-surface-container-low rounded-lg p-2">
              <span
                className={`material-symbols-outlined ${item.headerIconMuted ? "text-on-surface/40" : "text-primary"}`}
              >
                {item.headerIcon}
              </span>
            </div>
            <div>
              <div className="mb-1 flex flex-wrap items-center gap-2">
                <p className="font-headline text-lg font-bold">{item.title}</p>
                <span className="text-xs text-on-surface/30">•</span>
                <span className="font-label text-xs text-on-surface/40">
                  {item.dateDisplay}
                </span>
              </div>
              <div className="flex items-center gap-2">
                {item.source.kind === "booking" ? (
                  <>
                    <Image
                      src={item.source.logoUrl}
                      alt={item.source.logoAlt}
                      width={16}
                      height={16}
                      className="size-4 opacity-70"
                    />
                    <span className="text-xs text-on-surface/40">
                      Fuente: {item.source.label}
                    </span>
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-xs text-on-surface/40">
                      {item.source.icon}
                    </span>
                    <span className="text-xs text-on-surface/40">
                      Fuente: {item.source.label}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div
            className={`rounded-full border px-4 py-2 ${sentimentBadgeClass(item.sentimentBadge.variant)}`}
          >
            <span className="text-sm font-bold">{item.sentimentBadge.label}</span>
          </div>
        </div>
        <div className="mb-8">
          <p className="font-body text-base leading-relaxed text-on-surface/80">
            {item.body}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 border-t border-surface-variant/50 pt-6">
          {item.topics.map((t) => (
            <div
              key={`${item.id}-${t.label}`}
              className={`flex items-center rounded-lg border px-3 py-1.5 ${topicChipClass(t.tone)}`}
            >
              <span className="text-[10px] font-bold uppercase">
                {t.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}
