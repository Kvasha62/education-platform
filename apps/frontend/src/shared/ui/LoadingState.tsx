export const LoadingState = ({ label = 'Loading…' }: { label?: string }) => (
  <div className="state" role="status" aria-live="polite">
    <span className="spinner" aria-hidden="true" />
    {label}
  </div>
)
