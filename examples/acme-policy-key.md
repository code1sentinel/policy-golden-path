# Acme policy: what each clause tests

The expected result of converting `acme-information-security-policy-2016.md`.
Codify Release 1 is tested against this.

**43 clauses → 33 controls**, from 27 requirement clauses (one of them a
duplicate). The other 16 are context (2 scope, 3 definitions, 4 roles,
1 exception) or not controls (6).

The expected statements below are the target a person reaches. Codify's
rules split a little more eagerly (38 drafts: "Install…" and "Keep… up to date"
as two, for example), and the reviewer merges or edits them. The tests in
`tests/test_acme.py` check the parts the rules must get right: every clause's
type, the duplicate, a draft for every requirement, and drafts that start with
the action and name no tool.

Values in [brackets] are parameters. Where the legacy clause gave a value
(90 days, 5 attempts), it becomes the parameter's value. Where it was vague
("regularly", "timely"), the parameter is left for the organization to set.

## Not controls, and context

| Clause | Type | Why |
| --- | --- | --- |
| 1.1 | Not a control | Aspiration ("is committed to"): nothing to test |
| 1.2 | Not a control | Describes the policy itself |
| 2.1, 2.2 | Scope | Becomes the catalog's "applies to" |
| 3.1, 3.2, 3.3 | Definition | Goes to the catalog's back matter |
| 4.1 | Role | CIO: accountable, approves exceptions |
| 4.2 | Role | IT Department implements. It is the "who" for implementation statements, not part of any control statement. |
| 4.3 | Role | "Line managers shall ensure…": a responsibility, not a testable control |
| 4.4 | Role | General responsibility |
| 11.1 | Not a control | Permits personal use: informative |
| 12.1 | Not a control (as written) | "Discouraged" can't be tested. Codify suggests a real requirement ("Restrict removable media to approved devices"), and the person decides. |
| 16.1 | Exception | The exception process. Kept as catalog metadata. |
| 17.1 | Not a control | Consequence of non-compliance (a deterrent) |
| 17.2 | Not a control | Aspiration ("encouraged") |

## Requirements

| Clause | Splits into | What it tests | Expected control statement(s) |
| --- | --- | --- | --- |
| 5.1 | 2 | Bundle of two requirements; passive voice | Grant access to systems on a need-to-know basis. · Require approval by the user's line manager before granting access. |
| 5.2 | 2 | "Regularly" and "as appropriate" are not testable | Review user accounts at least every [N] days. · Remove access that is no longer required within [N] days of the review. |
| 5.3 | 1 | Subject first ("The IT Department"); no time limit | Disable user accounts within [N] days of staff leaving, transferring or starting long-term leave. |
| 5.4 | 1 | Two closely joined parts: fine as one | Restrict privileged accounts to administrative tasks, and prohibit their use for email and web browsing. |
| 5.5 | 1 | Hedged ("should", "where possible") | Prohibit shared and generic accounts, except where approved as an exception to this policy. |
| 6.1 | 2 | Bundle; legacy values kept as parameter values | Enforce passwords of at least [8] characters containing letters and numbers. · Enforce password changes at least every [90] days. |
| 6.2 | 2 | Bundle of user behaviour and a technical control | Prohibit users from sharing or writing down passwords. · Prevent reuse of the last [5] passwords. |
| 6.3 | 0 | **Duplicate** of 6.1 (90-day change). Codify flags it and links it to 6.1's control. | (none: duplicate) |
| 6.4 | 1 | Already nearly control-shaped | Lock user accounts after [5] consecutive failed login attempts. |
| 7.1 | 1 | **Tool named** (Symantec) → guidance | Install anti-malware software on all desktops and servers, and keep it up to date. Guidance: e.g. Symantec Endpoint Protection. |
| 7.2 | 1 | User obligation that can be enforced technically | Prevent users from disabling or tampering with anti-malware software. |
| 7.3 | 2 | Open list ("etc."); user behaviour | Prohibit downloading software from untrusted sources. · Train users to recognise and report suspicious emails and links. |
| 8.1 | 1 | "In a timely manner" is not testable | Apply security patches to all systems within [N] days of release. |
| 8.2 | 1 | Hedged ("should", "where practical") | Test security patches before deploying them to production systems. |
| 9.1 | 2 | Subject first; **tools named** (Veritas, tapes) → guidance | Back up all servers at least daily. · Store backups in a separate, off-site location. Guidance: e.g. Veritas Backup Exec, tape. |
| 9.2 | 1 | "Periodically" is not testable | Test the restoration of backups at least every [N] days. |
| 10.1 | 1 | "Should", "as needed", open list ("such as") | Review security logs from all firewalls and servers at least every [N] days. |
| 10.2 | 1 | "Appropriate period" is not testable | Retain system logs for at least [N] days. |
| 11.2 | 1 | Clean prohibition | Prohibit sending confidential information to personal email accounts. |
| 12.2 | 1 | Clean requirement | Encrypt confidential information copied to removable media. |
| 13.1 | 1 | Vague ("shall comply with this policy") | Require third parties to meet Agency security requirements through their contracts. |
| 13.2 | 1 | Clean, with a trigger | Require vendors to sign a non-disclosure agreement before granting them access to Agency information. |
| 14.1 | 1 | Subject first; "immediately" | Report suspected security incidents to the IT Helpdesk within [N] hours of discovery. |
| 14.2 | 1 | "Will… take appropriate action" is not testable | Investigate reported security incidents and contain them within [N] hours. |
| 15.1 | 2 | Bundle | Keep the server room locked at all times. · Restrict server room access to authorised IT staff. |
| 15.2 | 1 | Clean | Escort visitors in Agency premises at all times. |
| 18.1 | 1 | Clean; subject at the end ("by the CIO") | Review this policy at least annually. |

## Legacy problems covered

| Problem | Clauses |
| --- | --- |
| Not a control (aspiration, consequence, permission) | 1.1, 1.2, 11.1, 12.1, 17.1, 17.2 |
| Bundled requirements | 5.1, 5.2, 6.1, 6.2, 7.3, 9.1, 15.1 |
| Subject first / passive voice | 5.1, 5.3, 9.1, 14.1, 18.1 |
| Vague timing ("regularly", "timely", "periodically", "as needed", "appropriate period") | 5.2, 8.1, 9.2, 10.1, 10.2 |
| Hedges ("should", "where possible", "where practical", "discouraged") | 5.5, 8.2, 10.1, 12.1 |
| Tools named | 7.1, 9.1 |
| Open-ended lists ("etc.", "such as") | 7.3, 10.1 |
| Duplicate | 6.3 |
| Legacy values to keep as parameter values | 6.1, 6.2, 6.4 |
