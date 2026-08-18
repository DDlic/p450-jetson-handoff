# P450 authority and contradiction rules

## Authority order

1. Raw evidence establishes what bytes/events were recorded.
2. A same-condition evidence summary establishes the narrow interpretation of those observations.
3. A current runbook establishes what action is permitted and what gate applies.
4. Current indexes/handoffs route work; they do not override raw evidence.
5. Historical reports, prompts, and notes explain provenance but are not execution authority.

## Required comparison dimensions

Before claiming two results agree or conflict, compare:

- PX4 version and full custom hash;
- patch/firmware artifact checksum;
- ROS publisher and PX4 endpoint QoS;
- Micro XRCE-DDS Agent version and compile-time recovery settings;
- baud, framing, flow control, and physical transport;
- output topic set and per-topic rate limits;
- test duration and sample count;
- disarmed/armed, Offboard/non-Offboard, propeller state, indoor/outdoor;
- publish-side versus receipt-side measurement point;
- test ID and whether the session was clean.

Different conditions normally qualify rather than contradict one another.

## Current high-priority reconciliation

- `6001/6001` establishes eventual delivery for one Reliable disarmed 600-second field.
- `601.548 ms` establishes that the same field did not meet the repository's 250 ms freshness gate.
- `<1.0 s` establishes only that the worst observed sample remained below the configured PX4 loss timeout in that field.
- No existing evidence establishes the armed/outdoor worst-case tail or general flight safety.
- Repeated same-family NX kernel panic evidence is an independent failed gate.

Therefore “Reliable removed measured final loss,” “freshness remains unresolved,” and “a narrowly controlled PoC may be risk-accepted by the operator” can all be true simultaneously.
