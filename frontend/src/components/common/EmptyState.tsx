interface EmptyStateProps {
  message?: string;
}

export function EmptyState({
  message = 'No stations found in this area. Try a larger radius or different location.',
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center">
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
