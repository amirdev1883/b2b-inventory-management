import { cloneElement } from 'react';
import { createContext, useContext, useEffect, useId, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  LoaderCircle,
  PackageOpen,
  Search,
  X,
} from 'lucide-react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './api';
import { label } from './utils';

const ToastContext = createContext(null);
export function ToastProvider({ children }) {
  const [message, setMessage] = useState('');
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);
  function notify(text) {
    clearTimeout(timer.current);
    setMessage(text);
    timer.current = setTimeout(() => setMessage(''), 5000);
  }
  return (
    <ToastContext.Provider value={notify}>
      {children}
      {message && (
        <div className="toast" role="status">
          <CheckCircle2 size={18} />
          {message}
          <button aria-label="Dismiss notification" onClick={() => setMessage('')}>
            <X size={16} />
          </button>
        </div>
      )}
    </ToastContext.Provider>
  );
}
export function useToast() {
  return useContext(ToastContext);
}
export function useSave(fn, success, done) {
  const cache = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: fn,
    onSuccess: async (data) => {
      await cache.invalidateQueries();
      toast(success);
      done?.(data);
    },
  });
}
export function useList(resource, filters = {}) {
  const query = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v !== '' && v != null),
  ).toString();
  return useQuery({
    queryKey: [resource, query],
    queryFn: () => api(`/api/${resource}/?${query}`),
    placeholderData: keepPreviousData,
  });
}
export function useDebounced(value, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}
export function Spinner({ text = 'Loading your workspace…' }) {
  return (
    <div className="loading" role="status">
      <LoaderCircle className="spin" size={24} />
      {text}
    </div>
  );
}
export function ErrorBanner({ error, retry }) {
  return error ? (
    <div className="error" role="alert">
      <AlertCircle size={18} />
      <span>{error.message || String(error)}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  ) : null;
}
export function PageHeading({ eyebrow = 'WORKSPACE', title, description, children }) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      <div className="heading-actions">{children}</div>
    </div>
  );
}
export function Badge({ value }) {
  return <span className={`badge badge-${String(value).toLowerCase()}`}>{label(value)}</span>;
}
export function Field({ label: title, hint, children, className = '' }) {
  const id = useId();
  return (
    <label className={`field ${className}`}>
      <span id={`${id}-label`}>{title}</span>
      {cloneElement(children, {
        'aria-labelledby': children.props['aria-label'] ? undefined : `${id}-label`,
        'aria-describedby': hint ? `${id}-hint` : undefined,
      })}
      {hint && <small id={`${id}-hint`}>{hint}</small>}
    </label>
  );
}
export function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${wide ? 'modal-wide' : ''}`}
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal-header">
        <h2 id={titleId}>{title}</h2>
        <button type="button" className="icon-button" aria-label="Close dialog" onClick={onClose}>
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function FormActions({ busy, onClose, label: title = 'Save changes' }) {
  return (
    <div className="form-actions">
      <button type="button" className="button secondary" onClick={onClose} disabled={busy}>
        Cancel
      </button>
      <button className="button primary" disabled={busy}>
        {busy ? (
          <>
            <LoaderCircle className="spin" size={16} />
            Saving…
          </>
        ) : (
          title
        )}
      </button>
    </div>
  );
}
export function Empty({
  title = 'Nothing here yet',
  text = 'New records will appear here.',
  children,
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <PackageOpen size={28} />
      </div>
      <h3>{title}</h3>
      <p>{text}</p>
      {children}
    </div>
  );
}
export function SearchBox({ value, onChange, placeholder = 'Search…' }) {
  return (
    <div className="search">
      <Search size={17} />
      <input
        aria-label={placeholder}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}
export function Pagination({ data, page, onPage, disabled }) {
  return data && data.count > 0 ? (
    <div className="pagination">
      <span>
        {(page - 1) * 25 + 1}–{Math.min(page * 25, data.count)} of {data.count} records
      </span>
      <div>
        <button
          className="icon-button"
          aria-label="Previous page"
          disabled={!data.previous || disabled}
          onClick={() => onPage(page - 1)}
        >
          <ArrowLeft size={17} />
        </button>
        <span>Page {page}</span>
        <button
          className="icon-button"
          aria-label="Next page"
          disabled={!data.next || disabled}
          onClick={() => onPage(page + 1)}
        >
          <ArrowRight size={17} />
        </button>
      </div>
    </div>
  ) : null;
}
export function DataState({ query, children, emptyTitle, emptyText }) {
  if (query.isPending) return <Spinner />;
  if (query.isError) return <ErrorBanner error={query.error} retry={() => query.refetch()} />;
  if (!query.data?.results.length) return <Empty title={emptyTitle} text={emptyText} />;
  return (
    <div aria-busy={query.isFetching} className={query.isPlaceholderData ? 'refreshing' : ''}>
      {children}
    </div>
  );
}
