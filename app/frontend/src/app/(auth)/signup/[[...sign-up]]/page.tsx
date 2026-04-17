import { SignUp } from "@clerk/nextjs";

export default function SignupPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="flex flex-col items-center">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)] text-primary mb-1">
            Tradyon Outreach
          </h1>
          <p className="text-sm text-text-secondary">Create your account</p>
        </div>
        <SignUp
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "shadow-md rounded-xl border border-[var(--color-border)]",
            },
          }}
          fallbackRedirectUrl="/onboarding"
          signInUrl="/login"
        />
      </div>
    </div>
  );
}
