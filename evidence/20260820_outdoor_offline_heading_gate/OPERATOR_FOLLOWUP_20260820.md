# Operator follow-up — 2026-08-20 outdoor session

Source: operator statements supplied in the NX Codex session on 2026-08-20 after review of the F1/F2 evidence.

## Confirmed facts

1. Propellers were installed during both rejected F1 and F2 script attempts.
2. The F1/F2 scripts stopped at PRECHECK with publishes=0. Therefore the installed propellers were never driven by these script attempts.
3. After F1/F2 failed, the operator manually armed and performed a GPS-mode flight. The aircraft flew normally.
4. RC operation was normal, including mode switching and Kill.
5. Moonlight remained connected during the 300-second soak, F1/F2 attempts and the subsequent manual flight. No connection instability was observed.

## Engineering interpretation

The manual flight is separate from the rejected NX script attempts. It supports the basic airframe, PX4 GPS-mode flight, RC/Kill path and Moonlight-loaded LAN operation. It does not validate the corrected Offboard mission, final in-flight heading-alignment gate, autonomous forward segment or autonomous landing.

The later `vehicle_status` arm/disarm history is consistent with the operator-reported manual flight, but exact event attribution should be verified from PX4 ULog rather than inferred from a later snapshot.

## Outstanding artifacts

- PX4 ULog covering the manual flight.
- QGC TLog for the same period, if recorded.
