export const ErrorState = ({ message = 'Something went wrong.' }: { message?: string }) => (
  <div className="state state--error" role="alert">
    {message}
  </div>
)
