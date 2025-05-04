// static/app.js

const steps = Array.from(document.querySelectorAll('.step'));
const progress = Array.from(document.querySelectorAll('.progress-step'));
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');

let current = 0;

function showStep(idx) {
  steps.forEach((s, i) => s.classList.toggle('active', i === idx));
  progress.forEach((p, i) => p.classList.toggle('active', i <= idx));
  prevBtn.disabled = idx === 0;
  nextBtn.textContent = idx === steps.length - 1 ? 'Finish' : 'Next';
}

async function fetchStep(stepIdx) {
  const src = document.getElementById('source-input').value.trim();
  if (!src) {
    alert('Please enter a valid source URI.');
    return;
  }

  nextBtn.disabled = true;
  let endpoint, resultKey, containerId;

  switch (stepIdx) {
    case 1:
      endpoint = '/generateOutline';
      resultKey = 'outline';
      containerId = 'render-outline';
      break;
    case 2:
      endpoint = '/generateDraft';
      resultKey = 'draft';
      containerId = 'render-draft';
      break;
    case 3:
      endpoint = '/generate';
      resultKey = 'tutorial';
      containerId = null;
      break;
    default:
      nextBtn.disabled = false;
      return;
  }

  try {
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ source: src })
    });
    if (!resp.ok) throw new Error(`Server returned ${resp.status}`);
    const data = await resp.json();

    if (containerId) {
      const html = DOMPurify.sanitize(marked.parse(data[resultKey]));
      document.getElementById(containerId).innerHTML = html;
    } else {
      document.getElementById('final-markdown').value = data[resultKey];
    }
  } catch (err) {
    console.error(err);
    alert('Error: ' + err.message);
  } finally {
    nextBtn.disabled = false;
  }
}

nextBtn.addEventListener('click', async () => {
  if (current < steps.length - 1) {
    // fetch next step’s data
    await fetchStep(current + 1);
    current++;
    showStep(current);
  }
});

prevBtn.addEventListener('click', () => {
  if (current > 0) {
    current--;
    showStep(current);
  }
});

// Download final markdown
document.getElementById('download-btn').addEventListener('click', () => {
  const md = document.getElementById('final-markdown').value;
  const blob = new Blob([md], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'tutorial.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});

showStep(current);
