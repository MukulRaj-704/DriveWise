export default function ProfilePage() {
  return (
    <div className="mx-auto max-w-2xl p-8">
      <h1 className="mb-1 text-2xl font-semibold">Profile</h1>
      <p className="mb-6 text-sm text-neutral-500">Account details and preferences.</p>
      <div className="rounded-xl border border-neutral-200 p-6 text-sm text-neutral-500 dark:border-neutral-800">
        Profile management (name, email, password change) can be added here via a
        <code className="mx-1 rounded bg-neutral-100 px-1.5 py-0.5 dark:bg-neutral-900">PATCH /users/me</code>
        endpoint following the same service/repository pattern as the rest of the app.
      </div>
    </div>
  );
}
