# project-scaffolding Specification

## Purpose
TBD - created by archiving change dev-6-scaffold-roadmap-awareness. Update Purpose after archive.
## Requirements
### Requirement: Scaffolding creates the roadmap directory layout

`arbor-project-scaffold` SHALL create `docs/roadmaps/` and
`docs/roadmaps/archive/` during its generate phase, each containing a `.gitkeep`
file so both directories survive the initial commit while empty. The skill SHALL
NOT author any roadmap file, phase, or item.

#### Scenario: Both directories are created and tracked

- **WHEN** the scaffold's generate phase runs
- **THEN** `docs/roadmaps/.gitkeep` and `docs/roadmaps/archive/.gitkeep` both exist and are committed

#### Scenario: No roadmap content is invented

- **WHEN** the scaffold finishes
- **THEN** `docs/roadmaps/` contains no `.md` file, because what to build is the user's to plan

### Requirement: The skill names arbor-auto-roadmap as the next step

`arbor-project-scaffold` SHALL close by naming `arbor-auto-roadmap` as the
natural next step after scaffolding, and SHALL NOT invoke it or begin planning
itself.

#### Scenario: Hand-off is named, not performed

- **WHEN** the scaffold completes
- **THEN** it names `arbor-auto-roadmap` as the next step and stops without invoking it

### Requirement: No new interrogation questions are added

The change SHALL NOT add any question to the skill's existing Phase 1
interrogation set.

#### Scenario: Question set is unchanged

- **WHEN** Phase 1 is compared before and after the change
- **THEN** its questions are identical, and the roadmap layout is created in the generate phase without asking about it

### Requirement: Scaffolding configures a local reverse proxy when one is available

`arbor-project-scaffold` SHALL, during its generate phase, detect whether a
local reverse proxy is available — an `nginx` binary on `PATH` and a writable
infrastructure root — and, when it is, write the project's virtual hosts,
certificate configuration, and log directory under a single project-owned
directory `<infra>/<name>.local/` containing `servers/`, `ssl/`, and `logs/`,
with one virtual host per HTTP-serving service for both port profiles: `<sub>.<name>.local` for the default profile and
`<sub>.e2e.<name>.local` for the e2e/agent profile. It SHALL also write a
certificate configuration carrying both `*.<name>.local` and
`*.e2e.<name>.local` as subject alternative names.

The skill SHALL NOT invoke `sudo`, modify `/etc/hosts`, or generate a
certificate. It SHALL instead write the required hosts entries to a file under
`/tmp` and print the remaining privileged commands for the user to run.

#### Scenario: Both profiles get a hostname

- **WHEN** the generate phase runs on a machine with a writable nginx servers directory
- **THEN** each HTTP-serving service has a `<sub>.<name>.local` vhost pointing at its default-profile port and a `<sub>.e2e.<name>.local` vhost pointing at its e2e-profile port

#### Scenario: Non-HTTP services get no virtual host

- **WHEN** the claimed port block includes a database, broker, or cache
- **THEN** no virtual host is written for it, because a reverse proxy cannot usefully front it

#### Scenario: A project's proxy configuration is self-contained

- **WHEN** the step writes a project's proxy configuration
- **THEN** every file it creates lives under `<infra>/<name>.local/`, so the project can be moved, archived, or deleted as one directory

#### Scenario: Generated configs do not depend on the package manager prefix

- **WHEN** a vhost references a certificate, key, or log file
- **THEN** it names the resolved absolute path under the infrastructure root rather than a path through `/opt/homebrew` or `/etc/nginx`

#### Scenario: A missing proxy is skipped, not failed

- **WHEN** `nginx` is absent or the servers directory is not writable
- **THEN** the step is skipped, the scaffold completes normally, and the hand-off notes that no proxy was configured

#### Scenario: Privileged actions are emitted, never executed

- **WHEN** the step finishes
- **THEN** `/tmp/<name>-hosts.txt` exists and the certificate generation, Keychain trust, and `/etc/hosts` edits are printed as instructions rather than run

### Requirement: Generated private keys are readable by nginx and no one else

A certificate reissue script SHALL transfer ownership of the generated
certificate and key to the user the nginx master process runs as, and SHALL set
the key to mode `600` and the certificate to mode `644`. This applies whether
`arbor-project-scaffold` writes the script or reuses an existing one.

#### Scenario: The key is not world-readable

- **WHEN** a certificate is reissued
- **THEN** `local.key` is mode `600`, so no other user on the machine can read it

#### Scenario: nginx can still read its own key

- **WHEN** a certificate is reissued and nginx is reloaded
- **THEN** nginx starts successfully, because the key was chowned to the user it runs as rather than left owned by root

### Requirement: The step verifies routing, not just parsing

`arbor-project-scaffold` SHALL confirm that each generated hostname is served
by nginx before reporting the step complete, using a request that does not
depend on `/etc/hosts` having been edited.

#### Scenario: Hostnames are proven to route before the user edits /etc/hosts

- **WHEN** the step finishes writing virtual hosts and reloads nginx
- **THEN** each hostname returns an HTTP status when requested with the address resolved explicitly to `127.0.0.1`, proving nginx answers for that name even while the upstream service is down

### Requirement: The proxy is never a dependency of the gate

The generated project SHALL address its services as `127.0.0.1:<port>` in
compose, the gate, and the e2e suite, so that the gate produces an identical
result on a machine with no reverse proxy.

#### Scenario: The gate passes without nginx

- **WHEN** the gate runs on a machine where no reverse proxy is configured
- **THEN** it passes, because no stage resolves a `.local` hostname

