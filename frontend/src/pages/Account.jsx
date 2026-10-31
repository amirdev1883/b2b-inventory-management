import { KeyRound } from 'lucide-react';
import { useSession } from '../session';
import { changePassword } from '../api';
import { ErrorBanner, Field, PageHeading, useSave } from '../ui';

export default function Account() {
  const { session, setSession } = useSession();
  const save = useSave(
    changePassword,
    'Password changed. Your other sessions are now signed out.',
    (data) => setSession(data),
  );
  return (
    <>
      <PageHeading
        eyebrow="YOUR PERSONAL SPACE"
        title="My account"
        description={`${session.user.email} · ${session.business.name}`}
      />
      <section className="panel settings-panel">
        <div className="panel-heading">
          <div>
            <h2>
              <KeyRound size={19} />
              Change password
            </h2>
            <p className="muted">Use a unique password. Changing it revokes your other sessions.</p>
          </div>
        </div>
        <form
          key={session.access}
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate(Object.fromEntries(new FormData(event.currentTarget)));
          }}
        >
          <div className="form-body">
            <ErrorBanner error={save.error} />
            <Field label="Current password">
              <input
                name="current_password"
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
              />
            </Field>
            <Field label="New password" hint="At least 10 characters.">
              <input
                name="new_password"
                type="password"
                autoComplete="new-password"
                required
                minLength={10}
                maxLength={128}
              />
            </Field>
          </div>
          <div className="form-actions">
            <button className="button primary" disabled={save.isPending}>
              {save.isPending ? 'Updating…' : 'Update password'}
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
