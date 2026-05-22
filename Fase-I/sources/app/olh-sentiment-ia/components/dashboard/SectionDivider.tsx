type Props = {
  label: string;
};

export function SectionDivider({ label }: Props) {
  return (
    <div className="section-divider">
      <span className="text-primary text-[10px] font-bold uppercase tracking-[0.25em]">
        {label}
      </span>
    </div>
  );
}
