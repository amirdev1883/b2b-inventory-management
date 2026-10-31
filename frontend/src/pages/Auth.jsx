import { useState } from 'react';
import { ArrowRight, Boxes, Check, Package, ShieldCheck } from 'lucide-react';
import { useSession } from '../session';
import { authRequest } from '../api';
import { ErrorBanner, Field } from '../ui';

export default function Auth({ startupError }) {
  const params = new URLSearchParams(window.location.search);
  const [mode, setMode] = useState(params.has('reset_uid') ? 'reset' : 'login');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState('');
  const { signIn } = useSession();
  const titles = {
    login: 'Welcome back.',
    register: 'A workspace of your own.',
    forgot: 'Reset your password.',
    reset: 'Choose a new password.',
  };
  async function submit(event) {
    event.preventDefault();
    setError(null);
    setMessage('');
    setBusy(true);
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (mode === 'forgot') {
        const result = await authRequest('password-reset', data);
        setMessage(result.detail);
      } else if (mode === 'reset') {
        const result = await authRequest('password-reset/confirm', {
          ...data,
          uid: params.get('reset_uid'),
          token: params.get('reset_token'),
        });
        window.history.replaceState({}, '', '/');
        setMode('login');
        setMessage(result.detail);
      } else {
        await signIn(mode, data);
      }
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  }
  function changeMode(next) {
    setMode(next);
    setError(null);
    setMessage('');
  }
  return (
    <div className="auth-shell">
      <section className="auth-story">
        <a className="brand" href="/">
          <span className="brand-mark">
            <Package size={26} />
          </span>
          <span>
            stockroom<span className="brand-dot">.</span>
          </span>
        </a>
        <div>
          <span className="story-tag">
            <span />A little more control. A lot less busywork.
          </span>
          <h1>
            Keep your business
            <br />
            moving forward.
          </h1>
          <p>One clear view of your inventory, suppliers, and orders. Everything in its place.</p>
          <div className="story-features">
            {[
              'Know what’s in stock',
              'Move from purchase to delivery',
              'Give every teammate the right access',
            ].map((text) => (
              <span key={text}>
                <Check size={17} />
                {text}
              </span>
            ))}
          </div>
        </div>
        <div className="auth-story-footer">
          <Boxes size={30} />
          <span>YOUR OPERATIONS, CONNECTED.</span>
        </div>
      </section>
      <section className="auth-form-side">
        <div className="auth-form-wrap">
          <p className="eyebrow">YOUR BUSINESS STARTS HERE</p>
          <h2>{titles[mode]}</h2>
          <p className="muted">
            {mode === 'login'
              ? 'Sign in to see how things are moving.'
              : mode === 'register'
                ? 'Create your business and become its first administrator.'
                : 'We’ll help you get back to your workspace.'}
          </p>
          <ErrorBanner error={error || startupError} />
          {message && (
            <div className="success" role="status">
              {message}
            </div>
          )}
          <form onSubmit={submit} key={mode}>
            {mode === 'register' && (
              <>
                <Field label="Business name">
                  <input
                    name="business_name"
                    required
                    maxLength={160}
                    autoComplete="organization"
                    placeholder="e.g. Northstar Supply"
                  />
                </Field>
                <div className="form-grid">
                  <Field label="First name">
                    <input name="first_name" required maxLength={150} autoComplete="given-name" />
                  </Field>
                  <Field label="Last name">
                    <input name="last_name" maxLength={150} autoComplete="family-name" />
                  </Field>
                </div>
                <Field
                  label="Business currency"
                  hint="Used for all orders. Currency is fixed once your workspace is created."
                >
                  <select name="currency" defaultValue="CAD">
                    {['CAD', 'USD', 'EUR', 'GBP', 'AUD'].map((c) => (
                      <option key={c}>{c}</option>
                    ))}
                  </select>
                </Field>
              </>
            )}
            {mode !== 'reset' && (
              <Field label="Email address">
                <input
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  placeholder="you@business.com"
                  maxLength={254}
                />
              </Field>
            )}
            {mode !== 'forgot' && (
              <Field
                label={mode === 'reset' ? 'New password' : 'Password'}
                hint={mode !== 'login' ? 'At least 10 characters. Use a unique password.' : null}
              >
                <input
                  name="password"
                  type="password"
                  required
                  minLength={mode === 'login' ? 1 : 10}
                  maxLength={128}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                />
              </Field>
            )}
            {mode === 'login' && (
              <button
                type="button"
                className="text-button forgot"
                onClick={() => changeMode('forgot')}
              >
                Forgot password?
              </button>
            )}
            <button className="button primary auth-submit" disabled={busy}>
              {busy
                ? 'Please wait…'
                : {
                    login: 'Sign in',
                    register: 'Create workspace',
                    forgot: 'Send reset link',
                    reset: 'Update password',
                  }[mode]}
              <ArrowRight size={17} />
            </button>
          </form>
          <p className="auth-toggle">
            {mode === 'login' ? (
              <>
                New here?{' '}
                <button className="text-button" onClick={() => changeMode('register')}>
                  Create a workspace
                </button>
              </>
            ) : (
              <button className="text-button" onClick={() => changeMode('login')}>
                Back to sign in
              </button>
            )}
          </p>
          <div className="auth-secure">
            <ShieldCheck size={16} />
            Your business. Your own workspace.
          </div>
        </div>
      </section>
    </div>
  );
}
