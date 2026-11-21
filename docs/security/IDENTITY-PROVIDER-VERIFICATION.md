# Identity-provider verification: what Microsoft Entra External ID actually provides

**Status:** Architecture finding. Not yet demonstrated in a live tenant. No production use.
**Reviewer finding:** PR #52, item 4. The synthetic signed-event tests show cryptographic validation only, not compatibility with Entra External ID.
**Sources checked:** Microsoft Learn pages on custom authentication extensions, custom claims providers, external MFA providers, optional claims, and external-tenant multifactor authentication, retrieved 21 November 2026. Where a point is not in those pages, it is marked UNVERIFIED.

## 1. Conclusion

The current design in `backend/app/verification.py` assumes that Entra External ID posts signed verification events (`email_verified`, `phone_verified`, `mfa_enrolled`) to `POST /v1/verification/events`. **Entra does not do this.** The documented extension model runs the other way: Entra calls a REST API that the tenant owner registers, and that API can return claims for inclusion in tokens.

The synthetic-key tests prove that STN can verify a signature it was given. They do not prove that Entra can produce the evidence STN needs. That gap is open.

## 2. What the documentation supports

| Capability | Documented? | Detail |
|---|---|---|
| Token issuance start custom extension | Yes, external tenants | Entra calls a registered REST API before issuing a token. The call carries a bearer token issued by Entra. The API can return claims. |
| Custom claims provider | Yes | A custom authentication extension that fetches claims from an external system. Claims reach the app token only if an application's claims mapping policy includes them. |
| Email one-time passcode (sign-in method) | Yes, external tenants | Email OTP is a supported first factor and a supported second factor for external users, per the external-tenant MFA documentation. |
| SMS as second factor | Yes, as a Microsoft-managed add-on | Described as a Microsoft-managed add-on with built-in fraud controls. Bring-your-own SMS provider for MFA is not documented; a Microsoft Q&A thread reports the same, and it is not an official statement. |
| Custom email provider for OTP send | Documented (preview) | The OnOtpSend event lets an STN REST API send the one-time passcode through another provider. Availability in external tenants must be confirmed in the tenant. |
| External authentication methods (EAM) | Yes | An external MFA provider returns a token signed by its own keys, validated by Entra through the provider's `jwks_uri`. This is Entra validating a provider, not STN receiving events. |
| `amr` (authentication methods) claim | UNVERIFIED in external tenants | Present in Microsoft identity platform tokens according to community and B2C sources. Its exact values in an External ID token must be captured in a test tenant. |
| `email` claim | UNVERIFIED | Expected in ID tokens when the `email` scope is requested. Confirm presence and whether it is verified. |
| A documented `phone_verified` or `email_verified` boolean claim for External ID users | **Not found** | No such claim appeared in the pages reviewed. The optional-claims reference lists verification claims for domain-verified workforce emails, which is a different case. |

## 3. Consequences for the verification design

1. **Email verification.** Achievable through Entra email OTP at sign-up or sign-in, with the result visible in the token (`amr` and `email`). Needs a tenant test to confirm the exact claims.
2. **MFA enrolment.** Achievable only as evidence of a completed second factor in a sign-in (`amr` containing a second-factor method). "Enrolment" as a separate event is not documented. The current `mfa_enrolled` event does not map to an Entra fact.
3. **Phone verification.** No documented claim. Options are (a) Microsoft-managed SMS as a second factor, with evidence in `amr` (UNVERIFIED), or (b) an STN-operated verification step through a custom extension, where STN records the outcome itself. Option (b) makes STN the evidence source, not Entra, and must be described as such.
4. **Event ingestion.** The `POST /v1/verification/events` route cannot be the evidence source for production. It remains only as an internal path for a future custom claims provider that STN operates and authenticates.

## 4. Validation mechanism (for tokens STN receives from Entra)

Planned checks, each to be demonstrated in a test tenant:

- Issuer (`iss`) equals the external tenant's issuer, taken from its OpenID configuration. The exact URL format for External ID tenants is UNVERIFIED and must be copied from the tenant, not assumed.
- Signature verified with keys from the tenant's `jwks_uri`, selected by `kid`. Algorithm restricted to RS256.
- Audience (`aud`) equals this API's registered application ID.
- `tid` equals the expected tenant ID.
- `exp`, `nbf` and `iat` checked with bounded clock skew.
- `sub` used as the subject; no subject is accepted from request bodies.
- The `amr` claim is read only from a validated token and is never supplied by a caller.

## 5. Required evidence before any gate can rely on this

1. A development tenant (owner action, not yet provisioned).
2. A captured, redacted sample of each token type STN will accept, showing `iss`, `aud`, `tid`, `amr`, `email` and `sub`.
3. A statement, from the tenant's own configuration, of which factors the email and SMS methods produce.
4. A reproducible test that validates a real Entra token against the JWKS of that tenant.
5. A decision on phone verification (section 3, item 3).

Until items 1–5 are complete: contact verification, MFA evidence and account activation remain unproven. Onboarding must not treat a synthetic event as evidence of a live sign-in.

## 6. Status of the code

- `verification.py`: an STN-defined signed-event format. **Not Entra-native.** Its audit actor is a hash of the issuer to satisfy the audit schema. Its tests use synthetic keys only.
- `auth.py`: validates RS256 bearer tokens against a configured JWKS. This is the part that maps to Entra, but it has not been tested against a live External ID token.
- Onboarding gates on `email`, `phone` and `mfa` events. Those events currently have no Entra source. Onboarding therefore cannot complete with a live identity provider until section 5 is done. This is a known blocker (D-004, D-023).
