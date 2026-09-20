const API = "http://localhost:8000/api/v1";
const j = (r) => r.json();

const patients = await fetch(`${API}/patients`).then(j);
const demo2 = patients.find((p) => p.patient_identifier === "DEMO-002");

console.log("--- Submitting request for DEMO-002 ---");
const runResp = await fetch(`${API}/orchestration/run`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    patient_id: demo2.id,
    requested_service: "Lumbar spine MRI",
    service_category: "imaging",
    diagnosis_codes: ["M54.5"],
  }),
}).then(j);
console.log(`run_id=${runResp.run_id} determination=${runResp.determination}`);

console.log("\n--- Checking review queue ---");
let queue = await fetch(`${API}/review/queue`).then(j);
console.log(`Queue size: ${queue.length}`);
console.log(queue.find((q) => q.run_id === runResp.run_id));

console.log("\n--- Fetching review detail ---");
const detail = await fetch(`${API}/review/${runResp.run_id}`).then(j);
console.log(`review_status=${detail.review_status}, criteria_count=${detail.ai_response.criteria_evaluated.length}`);

console.log("\n--- Attempting override WITHOUT notes (should fail 400) ---");
const badResp = await fetch(`${API}/review/${runResp.run_id}`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ reviewer_name: "Dr. Test", decision: "override", final_determination: "approved", notes: "" }),
});
console.log(`Status: ${badResp.status} (expect 400)`);

console.log("\n--- Submitting valid uphold review ---");
const reviewResp = await fetch(`${API}/review/${runResp.run_id}`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ reviewer_name: "Dr. Nguyen", decision: "uphold", notes: "Reviewed and agree with AI assessment." }),
}).then(j);
console.log(reviewResp);

console.log("\n--- Verifying removed from queue ---");
queue = await fetch(`${API}/review/queue`).then(j);
console.log(`Still in queue: ${queue.some((q) => q.run_id === runResp.run_id)} (expect false)`);

console.log("\n--- Attempting to review again (should fail 400) ---");
const dupResp = await fetch(`${API}/review/${runResp.run_id}`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ reviewer_name: "Dr. Nguyen", decision: "uphold", notes: "again" }),
});
console.log(`Status: ${dupResp.status} (expect 400)`);

console.log("\n--- Observability review stats ---");
const metrics = await fetch(`${API}/observability/metrics`).then(j);
console.log(metrics.review);
