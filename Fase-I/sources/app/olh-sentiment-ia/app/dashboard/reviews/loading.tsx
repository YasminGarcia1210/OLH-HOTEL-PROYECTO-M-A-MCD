export default function ReviewsExplorerLoading() {
  return (
    <div className="mx-auto max-w-[1400px] animate-pulse p-8 pb-12 lg:p-12">
      <div className="bg-surface-container-low mb-10 h-14 max-w-xl rounded-lg" />
      <div className="bg-surface-container mb-8 h-32 rounded-xl" />
      <div className="space-y-6">
        <div className="bg-surface-container h-64 rounded-xl" />
        <div className="bg-surface-container h-64 rounded-xl" />
      </div>
    </div>
  );
}
