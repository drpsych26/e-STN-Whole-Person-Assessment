// Runtime configuration for the review copy. Intentionally empty:
// no backend endpoint, webhook or escalation service is configured in this build.
// The assessment does not send any automatic alert. See README-REVIEW-CORRECTIONS.md.
window.STN_RUNTIME_CONFIG = Object.freeze({ escalationEndpoint: null, environment: "review-copy" });
