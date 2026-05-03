#!/usr/bin/env node

const fs = require("fs");

const allowedStatuses = new Set([
  "started",
  "received",
  "normalized",
  "decision_created",
  "route_selected",
  "dispatched",
  "execution_started",
  "execution_completed",
  "result_sent",
  "result_received",
  "result_stored",
  "trace_stored",
  "no_route_found",
  "failed"
]);

const aliases = {
  success: "execution_completed",
  complete: "execution_completed",
  completed: "execution_completed",
  stored: "result_stored",
  result: "result_received",
  sent: "result_sent",
  error: "failed",
  failure: "failed",
  fail: "failed",
  routed: "route_selected",
  route: "route_selected",
  dispatch: "dispatched",
  dispatched: "dispatched",
  start: "started",
  started: "started",
  normalized: "normalized",
  no_route: "no_route_found",
  no_route_found: "no_route_found"
};

function clean(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function normalizeStatus(status) {
  const raw = clean(status).toLowerCase();

  if (allowedStatuses.has(raw)) return raw;

  if (raw.startsWith("decision_created")) return "decision_created";
  if (raw.includes("no_route")) return "no_route_found";
  if (raw.includes("result") && raw.includes("store")) return "result_stored";
  if (raw.includes("result") && raw.includes("send")) return "result_sent";
  if (raw.includes("result")) return "result_received";
  if (raw.includes("dispatch")) return "dispatched";
  if (raw.includes("route")) return "route_selected";
  if (raw.includes("decision")) return "decision_created";
  if (raw.includes("fail") || raw.includes("error")) return "failed";
  if (raw.includes("complete")) return "execution_completed";
  if (raw.includes("start")) return "started";

  return aliases[raw] || "";
}

function normalize(payload) {
  const now = new Date().toISOString();

  const event = {
    trace_id: clean(payload.trace_id) || `trc_${Date.now()}`,
    event_id: clean(payload.event_id) || `${Date.now()}`,
    source: clean(payload.source || payload.repo) || process.env.GITHUB_REPOSITORY || "unknown-repo",
    workflow: clean(payload.workflow) || process.env.GITHUB_WORKFLOW || "unknown-workflow",
    status: normalizeStatus(payload.status),
    route: clean(payload.route),
    target: clean(payload.target),
    result: clean(payload.result),
    error: clean(payload.error),
    timestamp: clean(payload.timestamp) || now,
    context: typeof payload.context === "object" && payload.context !== null ? payload.context : {},
    ontology: typeof payload.ontology === "object" && payload.ontology !== null ? payload.ontology : {}
  };

  return event;
}

function validate(event) {
  const errors = [];

  if (!event.trace_id) errors.push("trace_id is required");
  if (!event.source) errors.push("source is required");
  if (!event.workflow) errors.push("workflow is required");
  if (!event.timestamp) errors.push("timestamp is required");

  if (!event.status) {
    errors.push("status is required or could not be normalized");
  } else if (!allowedStatuses.has(event.status)) {
    errors.push(`status is not allowed: ${event.status}`);
  }

  if (Number.isNaN(Date.parse(event.timestamp))) {
    errors.push(`timestamp is not valid ISO datetime: ${event.timestamp}`);
  }

  return errors;
}

function emitOutput(name, value) {
  fs.appendFileSync(process.env.GITHUB_OUTPUT, `${name}=${value}\n`);
}

const raw = process.env.CLIENT_PAYLOAD || "{}";
let payload;

try {
  payload = JSON.parse(raw);
} catch (err) {
  console.error("Invalid JSON payload");
  console.error(err.message);
  process.exit(1);
}

const event = normalize(payload);
const errors = validate(event);

if (errors.length) {
  const rejection = {
    trace_id: event.trace_id || `trc_rejected_${Date.now()}`,
    event_id: event.event_id || `${Date.now()}`,
    source: event.source || process.env.GITHUB_REPOSITORY || "unknown-repo",
    workflow: event.workflow || process.env.GITHUB_WORKFLOW || "unknown-workflow",
    status: "failed",
    error: errors.join("; "),
    timestamp: new Date().toISOString(),
    context: {
      rejected: true,
      original_status: clean(payload.status)
    },
    ontology: {
      signal: "invalid_trace_event",
      phase: "validation"
    }
  };

  fs.writeFileSync("trace-event-rejected.json", JSON.stringify(rejection, null, 2));
  emitOutput("valid", "false");
  emitOutput("event", JSON.stringify(rejection));
  console.error("Trace event rejected:");
  console.error(JSON.stringify(rejection, null, 2));
  process.exit(2);
}

fs.writeFileSync("trace-event-normalized.json", JSON.stringify(event, null, 2));
emitOutput("valid", "true");
emitOutput("event", JSON.stringify(event));

console.log("Trace event accepted:");
console.log(JSON.stringify(event, null, 2));