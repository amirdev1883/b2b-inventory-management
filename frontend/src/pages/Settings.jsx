import { Building2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { useSession } from '../session';
import { ErrorBanner, Field, PageHeading, Spinner, useSave } from '../ui';

export default function Settings() {
  const { setSession } = useSession();
  const query = useQuery({ queryKey: ['business'], queryFn: () => api('/api/business/') });
  const save = useSave(
    (data) => api('/api/business/', { method: 'PATCH', body: data }),
    'Business settings updated.',
    (business) => setSession((current) => ({ ...current, business })),
  );
  return (
    <>
      <PageHeading
        eyebrow="MAKE IT YOURS"
        title="Business settings"
        description="The details that make your workspace, and your invoices, yours."
      />
      {query.isPending ? (
        <Spinner />
      ) : query.isError ? (
        <ErrorBanner error={query.error} retry={() => query.refetch()} />
      ) : (
        <section className="panel settings-panel">
          <div className="panel-heading">
            <div>
              <h2>
                <Building2 size={19} />
                Business details
              </h2>
              <p className="muted">
                Updated details apply to invoices created after your next order confirmation.
              </p>
            </div>
          </div>
          <form
            key={query.data.id}
            onSubmit={(event) => {
              event.preventDefault();
              save.mutate(Object.fromEntries(new FormData(event.currentTarget)));
            }}
          >
            <div className="form-body">
              <ErrorBanner error={save.error} />
              <Field label="Business name">
                <input
                  name="name"
                  defaultValue={query.data.name}
                  required
                  maxLength={160}
                  autoComplete="organization"
                />
              </Field>
              <div className="form-grid">
                <Field label="Business email">
                  <input
                    name="email"
                    type="email"
                    defaultValue={query.data.email}
                    maxLength={254}
                  />
                </Field>
                <Field label="Phone">
                  <input name="phone" defaultValue={query.data.phone} maxLength={40} />
                </Field>
              </div>
              <Field label="Business address">
                <textarea
                  name="address"
                  rows={3}
                  defaultValue={query.data.address}
                  maxLength={1000}
                />
              </Field>
              <div className="form-grid">
                <Field label="Tax registration number">
                  <input name="tax_number" defaultValue={query.data.tax_number} maxLength={80} />
                </Field>
                <Field label="Currency" hint="Fixed for consistent inventory and order accounting.">
                  <input value={query.data.currency} readOnly disabled />
                </Field>
              </div>
            </div>
            <div className="form-actions">
              <button className="button primary" disabled={save.isPending}>
                {save.isPending ? 'Saving…' : 'Save business details'}
              </button>
            </div>
          </form>
        </section>
      )}
    </>
  );
}
