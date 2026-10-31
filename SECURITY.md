# Security boundaries

Business data is scoped to the authenticated user’s tenant. Tenant IDs cannot be supplied to switch workspaces. Admin, Manager and Staff permissions are enforced by the API, independently of visible UI controls. Related product/supplier selections are tenant-scoped. Tests include cross-business IDs and role escalation attempts.

Production requires PostgreSQL, explicit allowed hosts and a strong signing secret. Access tokens remain in browser memory; refresh tokens are HttpOnly/Secure/SameSite cookies protected by CSRF and server-side rotation/blacklisting. Password changes invalidate earlier token hashes. Logout revokes the refresh session; an access token can remain usable for the rest of its ten-minute lifetime.

Stock/order services use transactions, row locks, reservation checks and ledger entries. Direct ORM/bulk updates can bypass application-level tenant and stock service rules; restrict database access to trusted operators. Django admin exposes business records read-only, with platform superuser-only access.

The app provides business inventory/order workflows, not payment processing, a full general ledger or tax filing. Set tax rates according to your business requirements. Handle payments/refunds externally, then record their status in the workspace.

Keep credentials in your deployment secret manager or ignored environment files. Never deploy the development Compose stack directly to the public internet. Production Redis throttling requires a private authenticated/TLS Redis connection when it crosses an untrusted network. Configure forwarded headers only behind a trusted ingress that replaces client-supplied values.

Report a suspected vulnerability privately to the repository owner using GitHub’s private vulnerability reporting if enabled. Avoid public issues containing credentials, customer data or a working exploit against a deployed business.
