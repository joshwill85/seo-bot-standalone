export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="max-w-md w-full space-y-8 text-center">
        <div>
          <h2 className="mt-6 text-center text-6xl font-extrabold text-gray-900">
            404
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Page not found
          </p>
        </div>
        <div className="bg-white p-8 rounded-lg shadow">
          <p>The page you're looking for doesn't exist.</p>
        </div>
      </div>
    </div>
  )
}