# Physical lib.rs placement — source03

Validated successor to immutable source02. The two original track-caller payloads at `0x1bdeb0` and `0x1bdec8` encode `programs/pump/src/lib.rs` at 1477:42 and 1478:40. Source03 moves the real shared helper module physically inline into `lib.rs`, removes `user_quote_payments.rs`, and re-exports the module from `trade`. No lines or columns were padded.

Both candidate filename payloads now equal the original filename. Their natural positions, 567:33 and 568:36, remain different. Native helper `0x8df98` has no own Location operands.

The actual recovered bodies remain exact: wrapper `0x97930` (704 bytes), native transfer `0x8df98` (1,208 bytes). Every immediate internal callee still maps to a normalized-exact current body. Full inventory is unchanged at 730 normalized / 124 raw against source02's identity linker layout, with no gained or lost windows. Duplicate-normalized windows `0x97bf0` and `0x8e450` remain qualified exactly as in source02: their separate ABI/caller closure is not claimed.

All 1,055 existing signed original/candidate cases pass, including byte-identical transaction inputs, signature verification, strict fixture comparisons, Pump diagnostics, and complete program invocation/success/failure sequences. No new fixture cases were added. Build, source, SDK, and verified external cache identities remain bound by the public builder receipt. The artifact audit reproduces from saved outputs without re-running tests.

For the parent's current source02-based draft, apply `user-quote-wrapper03-from02.patch`. It only moves the module into `lib.rs`, changes the `trade_v3.rs` module declaration into a re-export, and deletes the old file; BuyV2 is unchanged. `user-quote-wrapper03-fromR30.patch` includes the initial caller extraction for a baseline without source02.

Candidate SHA256: `80a71299353fe234861739dce439909dcdc191108e178193ca394245db4a7bb3`.
Unstripped SHA256: `ecf78999ea9dfc4bfdb9b9351d10d711cff820e2dae5f027d7c264921a54a2ac`.
Patch-from02 SHA256: `a05426eba9e372bab9bded9638e3e894be473a16bc7103d27f23f5ac9c0aaafd`.

`RESULT03.json`, `locations03.json`, `callees03.json`, `SOURCE-MANIFEST03.json`, and `MANIFEST03.json` provide the bounded proof and exact inputs. Source02, its manifest, and its receipts remain unchanged. Full ELF identity remains false; parent combined validation remains required.
