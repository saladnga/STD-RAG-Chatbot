import { useState } from "react";
import { Link } from "react-router-dom";
import { sendPasswordResetEmail } from "firebase/auth";
import { auth, authErrorMessage } from "../lib/firebase";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import FormError from "../components/FormError";
import SubmitButton from "../components/SubmitButton";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Firebase emails a link to its own hosted page where the new password is set.
      await sendPasswordResetEmail(auth, email);
      setSubmitted(true);
    } catch (err) {
      // Never reveal whether an account exists for this email.
      if ((err as { code?: string }).code === "auth/user-not-found") setSubmitted(true);
      else setError(authErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Forgot Password">
      {submitted ? (
        <p className="text-troy-ink/80 text-center">
          If an account exists for that email, a reset link has been sent.
          Check your inbox.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <FormError message={error} />

          <SubmitButton loading={loading} loadingText="Sending...">
            Send reset link
          </SubmitButton>
        </form>
      )}

      <p className="text-center text-base text-troy-ink/70 mt-4">
        <Link to="/login" className="text-troy-red font-semibold hover:underline">
          Back to login
        </Link>
      </p>
    </AuthLayout>
  );
}

export default ForgotPassword;
