import { useState } from 'react';
import { Mail, Pencil, Plus } from 'lucide-react';
import { api } from '../api';
import { useSession } from '../session';
import {
  DataState,
  ErrorBanner,
  Field,
  FormActions,
  Modal,
  PageHeading,
  Pagination,
  SearchBox,
  useDebounced,
  useList,
  useSave,
} from '../ui';

export default function Suppliers() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('true');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null);
  const { canManage } = useSession();
  const query = useList('suppliers', { search: useDebounced(search), is_active: status, page });
  return (
    <>
      <PageHeading
        eyebrow="GOOD BUSINESS STARTS WITH GOOD PARTNERS"
        title="Suppliers"
        description="Keep the people behind your products close at hand."
      >
        {canManage && (
          <button className="button primary" onClick={() => setEditing({})}>
            <Plus size={17} />
            Add supplier
          </button>
        )}
      </PageHeading>
      <section className="panel">
        <div className="toolbar">
          <SearchBox
            value={search}
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
            placeholder="Search suppliers…"
          />
          <select
            aria-label="Supplier status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="true">Active suppliers</option>
            <option value="false">Archived suppliers</option>
            <option value="">All suppliers</option>
          </select>
        </div>
        <DataState
          query={query}
          emptyTitle="No suppliers found"
          emptyText="Add your suppliers to start creating purchase orders."
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th>Email</th>
                  <th>Phone</th>
                  <th>Status</th>
                  {canManage && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {query.data?.results.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <strong>{s.name}</strong>
                      <small className="cell-secondary">
                        {s.address || 'Address not provided'}
                      </small>
                    </td>
                    <td>
                      {s.email ? (
                        <a className="contact-link" href={`mailto:${s.email}`}>
                          <Mail size={14} />
                          {s.email}
                        </a>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>{s.phone || <span className="muted">—</span>}</td>
                    <td>
                      <span className={`badge ${s.is_active ? 'badge-active' : 'badge-cancelled'}`}>
                        {s.is_active ? 'Active' : 'Archived'}
                      </span>
                    </td>
                    {canManage && (
                      <td>
                        <button
                          className="icon-button"
                          aria-label={`Edit ${s.name}`}
                          onClick={() => setEditing(s)}
                        >
                          <Pencil size={16} />
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination data={query.data} page={page} onPage={setPage} disabled={query.isFetching} />
        </DataState>
      </section>
      {editing && <SupplierForm supplier={editing} onClose={() => setEditing(null)} />}
    </>
  );
}
function SupplierForm({ supplier, onClose }) {
  const save = useSave(
    (data) =>
      api(`/api/suppliers/${supplier.id ? `${supplier.id}/` : ''}`, {
        method: supplier.id ? 'PATCH' : 'POST',
        body: data,
      }),
    'Supplier saved.',
    onClose,
  );
  function submit(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    data.is_active = data.is_active === 'on';
    save.mutate(data);
  }
  return (
    <Modal
      title={supplier.id ? 'Edit supplier' : 'Add a supplier'}
      onClose={() => !save.isPending && onClose()}
    >
      <form onSubmit={submit}>
        <div className="form-body">
          <ErrorBanner error={save.error} />
          <Field label="Supplier name">
            <input name="name" defaultValue={supplier.name} required maxLength={160} />
          </Field>
          <div className="form-grid">
            <Field label="Email">
              <input name="email" type="email" defaultValue={supplier.email} maxLength={254} />
            </Field>
            <Field label="Phone">
              <input name="phone" defaultValue={supplier.phone} maxLength={40} />
            </Field>
          </div>
          <Field label="Address">
            <textarea name="address" defaultValue={supplier.address} rows={2} maxLength={1000} />
          </Field>
          <Field label="Notes">
            <textarea name="notes" defaultValue={supplier.notes} rows={3} maxLength={2000} />
          </Field>
          <label className="checkbox">
            <input name="is_active" type="checkbox" defaultChecked={supplier.is_active ?? true} />
            Active supplier
          </label>
        </div>
        <FormActions
          busy={save.isPending}
          onClose={onClose}
          label={supplier.id ? 'Save changes' : 'Add supplier'}
        />
      </form>
    </Modal>
  );
}
