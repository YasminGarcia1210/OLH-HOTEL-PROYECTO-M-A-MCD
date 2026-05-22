type Props = {
  note: string;
};

export function DashboardCanvasFooter({ note }: Props) {
  return (
    <footer className="border-surface-variant/10 text-on-surface-variant/40 font-label border-t pt-8 text-center text-[10px] uppercase tracking-widest opacity-40">
      {note}
    </footer>
  );
}
