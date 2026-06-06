# Miasma Pre-Permission Packet

Status: public case study
Purpose: show how InferenceAtlas frames a real supply-chain attack vector as an access-review question before an agent, workflow, package, or CI job receives dangerous scope

Private engine, public proof.

## Framing Boundary

This is a worked example based on publicly reported attack vectors.

This is not a security claim about any specific product or vendor.

This asks what InferenceAtlas would ask before this scope was granted.

InferenceAtlas interpretation: the actual incident exploited the absence of this layer; package install, publish, CI, and credential-bearing workflow scope moved without a pre-permission packet that named proof debt, reviewers, and blocked claims first.

## Public Source Basis

| Source | What it establishes |
| --- | --- |
| [Red Hat security bulletin RHSB-2026-006](https://access.redhat.com/security/vulnerabilities/RHSB-2026-006) | Multiple `@redhat-cloud-services` npm packages were affected after a compromised GitHub account pushed unauthorized commits; Red Hat removed compromised versions and continued investigation. |
| [Microsoft Defender research](https://www.microsoft.com/en-us/security/blog/2026/06/02/preinstall-persistence-inside-red-hat-npm-miasma-credential-stealing-campaign/) | The campaign used legitimate publishing workflow paths, provenance signatures, install-time execution, credential harvesting, and propagation attempts across maintainer/package environments. |
| [Wiz Research](https://www.wiz.io/blog/miasma-supply-chain-attack-targeting-redhat-npm-packages) | The affected namespace, package count, package-download scale, install-time execution mechanisms, and cloud-identity collection focus were publicly reported. |

## Pre-Permission Question

Before a coding agent, dependency update workflow, package maintainer automation, or CI job can install, publish, modify workflows, or touch credential-bearing environments, IA should force one review question:

```text
What proof exists that this package, workflow, maintainer identity, and execution environment may safely receive this scope?
```

The packet is not an incident detector. It is the upstream authority object that blocks unsupported movement until the right humans see the exact missing proof.

## Packet Sketch

| Requested scope | What IA would ask first | Blocked until |
| --- | --- | --- |
| Install a package in a developer or CI environment | Is the package version pinned, provenance reviewed, install script behavior inspected, and sandbox evidence attached? | Security and Engineering approve an isolated execution plan. |
| Let an agent inspect or modify repository workflows | Which workflow files, permissions, and token scopes are in-bounds? | DevSecOps confirms no secret-bearing or publish-capable workflow can be changed. |
| Allow package publishing or release automation | Which maintainer identity, package scope, provenance chain, and rollback path are proven? | Release owner verifies publish permission, rollback, and revocation path. |
| Expose developer or CI credentials to runtime tools | Which credential stores are reachable, and why does the workflow need them? | Security confirms least-privilege boundaries and credential rotation plan. |
| Claim the dependency is safe to run | Which evidence supports that claim, and what remains unverified? | Reviewers attach provenance, sandbox, lockfile, and maintainer-scope evidence. |

## What Stays Blocked

- Installing untrusted dependency versions in credential-bearing environments.
- Reading or exporting developer secrets, CI secrets, cloud credentials, SSH keys, npm tokens, or vault material.
- Publishing packages, changing release workflows, or modifying GitHub Actions with agent authority.
- Treating provenance signatures as sufficient proof when the pipeline path itself may be compromised.
- Claiming safety before the packet has evidence and named reviewer owners.

## Reviewers

| Reviewer | Review area |
| --- | --- |
| Security | credential exposure, sandboxing, secret rotation, install-time execution |
| Engineering | dependency scope, lockfile evidence, package behavior review |
| DevSecOps / Platform | CI permissions, workflow boundaries, publish-token exposure |
| Release owner | package publication authority, rollback, maintainer verification |
| Legal / Communications | only if public disclosure, customer notice, or vendor obligations are triggered |

## Runnable Fixture

Run the public request fixture without keys:

```bash
python3 -m agent.trial examples/requests/miasma_pre_permission_packet.yml --json
```

Expected shape:

- `request_readiness` remains `ready_for_scoped_trial`
- `production_access` remains `false`
- `public_runner_approves_access` remains `false`
- `public_runner_grants_permissions` remains `false`
- `public_runner_executes_external_writes` remains `false`
- risky claims remain blocked until Security, Engineering, DevSecOps, and Release owners attach proof

## Boundary

This case study is a governance packet example. IA does not claim to inspect malware, replace endpoint controls, replace package scanners, or certify that a package is safe. IA names the pre-permission proof and reviewer routing that should exist before high-risk agent, package, CI, or credential scope moves.
