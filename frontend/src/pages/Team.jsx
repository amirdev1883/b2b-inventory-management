import { useState } from 'react';
import { Pencil, Plus, ShieldCheck } from 'lucide-react';
import { api } from '../api';
import { useSession } from '../session';
import {
  Badge,
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
import { date, initials } from '../utils';

export default function Team() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null);
  const { session } = useSession();
  const query = useList('users', { search: useDebounced(search), page });
  return (
    <>
      <PageHeading
        eyebrow="THE PEOPLE BEHIND THE PROGRESS"
        title="Team members"
        description="Give each person the access they need to do good work."
      >
        <button className="button primary" onClick={() => setEditing({})}>
          <Plus size={17} />
          Add team member
        </button>
      </PageHeading>
      <div className="info-box role-info">
        <ShieldCheck size={19} />
        <span>
          <strong>Admin</strong> manages people and settings. <strong>Manager</strong> manages
          inventory and fulfillment. <strong>Staff</strong> views records and prepares sales drafts.
        </span>
      </div>
      <section className="panel">
        <div className="toolbar">
          <SearchBox
            value={search}
            onChange={(v) => {
              setSearch(v);
              setPage(1);
            }}
            placeholder="Search team members…"
          />
        </div>
        <DataState
          query={query}
          emptyTitle="No team members found"
          emptyText="Try a different name or email address."
        >
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Team member</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {query.data?.results.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <div className="product-cell">
                        <span className="avatar light">{initials(u)}</span>
                        <strong>
                          {`${u.first_name} ${u.last_name}`.trim() || 'Team member'}
                          {u.id === session.user.id && <small className="you-tag">You</small>}
                        </strong>
                      </div>
                    </td>
                    <td className="muted">{u.email}</td>
                    <td>
                      <Badge value={u.role} />
                    </td>
                    <td>
                      <span className={`badge ${u.is_active ? 'badge-active' : 'badge-cancelled'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="muted">{date(u.date_joined)}</td>
                    <td>
                      <button
                        className="icon-button"
                        aria-label={`Edit ${u.email}`}
                        onClick={() => setEditing(u)}
                      >
                        <Pencil size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination data={query.data} page={page} onPage={setPage} disabled={query.isFetching} />
        </DataState>
      </section>
      {editing && <MemberForm member={editing} onClose={() => setEditing(null)} />}
    </>
  );
}
function MemberForm({ member, onClose }) {
  const { session, setSession } = useSession();
  const save = useSave(
    (data) =>
      api(`/api/users/${member.id ? `${member.id}/` : ''}`, {
        method: member.id ? 'PATCH' : 'POST',
        body: data,
      }),
    'Team member saved.',
    (data) => {
      if (data.id === session.user.id) setSession((current) => ({ ...current, user: data }));
      onClose();
    },
  );
  function submit(event) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    if (!data.password) delete data.password;
    data.is_active = data.is_active === 'on';
    save.mutate(data);
  }
  return (
    <Modal
      title={member.id ? 'Edit team member' : 'Add a team member'}
      onClose={() => !save.isPending && onClose()}
    >
      <form onSubmit={submit}>
        <div className="form-body">
          <ErrorBanner error={save.error} />
          <div className="form-grid">
            <Field label="First name">
              <input name="first_name" defaultValue={member.first_name} maxLength={150} />
            </Field>
            <Field label="Last name">
              <input name="last_name" defaultValue={member.last_name} maxLength={150} />
            </Field>
          </div>
          <Field label="Email">
            <input name="email" type="email" defaultValue={member.email} required maxLength={254} />
          </Field>
          <Field label="Role">
            <select name="role" defaultValue={member.role || 'STAFF'}>
              <option value="STAFF">Staff</option>
              <option value="MANAGER">Manager</option>
              <option value="ADMIN">Admin</option>
            </select>
          </Field>
          <Field
            label={member.id ? 'New password (optional)' : 'Initial password'}
            hint={
              member.id
                ? 'Leave blank to keep the existing password. A change signs out existing sessions.'
                : 'At least 10 characters. Share this password privately with the teammate.'
            }
          >
            <input
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={10}
              maxLength={128}
              required={!member.id}
            />
          </Field>
          <label className="checkbox">
            <input name="is_active" type="checkbox" defaultChecked={member.is_active ?? true} />
            Active account
          </label>
          <p className="muted small-text">
            Your business must always have at least one active administrator.
          </p>
        </div>
        <FormActions
          busy={save.isPending}
          onClose={onClose}
          label={member.id ? 'Save changes' : 'Create account'}
        />
      </form>
    </Modal>
  );
}
