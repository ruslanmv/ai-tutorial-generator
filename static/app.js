// ─────────────────────────────────────────────────────────────────────────────
// static/app.js
// ─────────────────────────────────────────────────────────────────────────────
/*
Wizard logic
────────────
Step 0 – enter a URL or upload a PDF/HTML file
Step 1 – show JSON outline
Step 2 – show rendered draft Markdown
Step 3 – raw Markdown + Download button
*/
"use strict";

/* -------------------------------------------------------------------------- */
/* DOM references                                                              */
/* -------------------------------------------------------------------------- */
const steps    = [...document.querySelectorAll(".step")];
const progress = [...document.querySelectorAll(".progress-step")];

const prevBtn  = document.getElementById("prev-btn");
const nextBtn  = document.getElementById("next-btn");

const outlineEl = document.getElementById("render-outline");
const draftEl   = document.getElementById("render-draft");
const finalTA   = document.getElementById("final-markdown");

/* -------------------------------------------------------------------------- */
/* State                                                                       */
/* -------------------------------------------------------------------------- */
let current = 0;               // active wizard page
let cachedResult = null;       // { outline, markdown }

/* -------------------------------------------------------------------------- */
/* Helper: update visible step                                                 */
/* -------------------------------------------------------------------------- */
function showStep(idx) {
  steps.forEach((s, i) => s.classList.toggle("active", i === idx));
  progress.forEach((p, i) => p.classList.toggle("active", i <= idx));
  prevBtn.disabled = idx === 0;
  nextBtn.textContent = idx === steps.length - 1 ? "Finish" : "Next";
}

/* -------------------------------------------------------------------------- */
/* Helper: render cached data                                                  */
/* -------------------------------------------------------------------------- */
function renderStep(idx) {
  if (!cachedResult) return;

  if (idx === 1) {             // Outline JSON pretty‑printed
    outlineEl.innerHTML = DOMPurify.sanitize(
      marked.parse("```json\n" +
        JSON.stringify(cachedResult.outline, null, 2) +
        "\n```")
    );
  } else if (idx === 2) {      // Draft Markdown rendered as HTML
    draftEl.innerHTML = DOMPurify.sanitize(
      marked.parse(cachedResult.markdown)
    );
  } else if (idx === 3) {      // Raw Markdown in textarea
    finalTA.value = cachedResult.markdown;
  }
}

/* -------------------------------------------------------------------------- */
/* Network: call /generate                                                     */
/* -------------------------------------------------------------------------- */
async function fetchTutorial() {
  const urlVal  = document.getElementById("source-input").value.trim();
  const fileObj = document.getElementById("file-input").files[0];

  if (!urlVal && !fileObj) {
    alert("Enter a URL or select a file.");
    return false;
  }

  nextBtn.disabled = true;

  // Build request payload
  let fetchOpts;
  if (fileObj) {
    const fd = new FormData();
    fd.append("file", fileObj);
    fetchOpts = { method: "POST", body: fd };
  } else {
    fetchOpts = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: urlVal })
    };
  }

  try {
    const r = await fetch("/generate", fetchOpts);
    if (!r.ok) throw new Error(`Server returned ${r.status}`);
    cachedResult = await r.json();
    return true;
  } catch (err) {
    console.error(err);
    alert("Error: " + err.message);
    return false;
  } finally {
    nextBtn.disabled = false;
  }
}

/* -------------------------------------------------------------------------- */
/* Wizard navigation                                                           */
/* -------------------------------------------------------------------------- */
nextBtn.addEventListener("click", async () => {
  // First “Next” triggers the backend call
  if (current === 0) {
    const ok = await fetchTutorial();
    if (!ok) return;
  }

  if (current < steps.length - 1) {
    current++;
    renderStep(current);
    showStep(current);
  } else {
    // Finished → trigger download
    document.getElementById("download-btn").click();
  }
});

prevBtn.addEventListener("click", () => {
  if (current > 0) {
    current--;
    showStep(current);
  }
});

/* -------------------------------------------------------------------------- */
/* Download final Markdown                                                     */
/* -------------------------------------------------------------------------- */
document.getElementById("download-btn").addEventListener("click", () => {
  const md = finalTA.value || "";
  const blob = new Blob([md], { type: "text/markdown" });
  const url  = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = "tutorial.md";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

/* Init */
showStep(current);
