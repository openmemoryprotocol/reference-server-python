
## v0.7.1-b.final — (2025-08-20)
- Finalized HTTP Message Signatures verification (Ed25519).
- Correct error semantics:
  - **400 Bad Request** for malformed `Signature` / `Signature-Input`.
  - **401 Unauthorized** for unknown `keyid` or invalid signature (incl. bad base64/length/type).
- Hardened dependency mapping; all tests green.
## v0.7.1-b.final — (2025-08-20)
- Finalized HTTP Message Signatures verification (Ed25519).
- Correct error semantics:
  - **400 Bad Request** for malformed `Signature` / `Signature-Input`.
  - **401 Unauthorized** for unknown `keyid` or invalid signature (incl. bad base64/length/type).
- Hardened dependency mapping; all tests green.
