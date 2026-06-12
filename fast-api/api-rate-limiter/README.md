# Rate Limiter

When to use each algorithm — final summary
Fixed window — simplest, cheapest, use for internal APIs where boundary bursts don't matter.
Sliding window — perfect accuracy, no bursts, higher memory, use when you genuinely cannot allow boundary exploitation (financial transactions, auth endpoints).
Token bucket — allows controlled bursts, smooth sustained rate, use for public APIs where clients need occasional headroom (what Stripe, GitHub, and AWS all use in practice).
Leaky bucket — zero burst tolerance, constant output, use when protecting slow or fragile downstream systems from any spike at all.
