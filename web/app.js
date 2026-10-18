const signinForm = document.querySelector("#signin-form");
const signupForm = document.querySelector("#signup-form");
const signinOtpForm = document.querySelector("#signin-otp-form");
const signupOtpForm = document.querySelector("#signup-otp-form");
const signinOtpBack = document.querySelector("#signin-otp-back");
const signupOtpBack = document.querySelector("#signup-otp-back");
const signinStatus = document.querySelector("#signin-status");
const signupStatus = document.querySelector("#signup-status");
const signinOtpStatus = document.querySelector("#signin-otp-status");
const signupOtpStatus = document.querySelector("#signup-otp-status");
const accountStatus = document.querySelector("#account-status");
const authCard = document.querySelector("#auth-card");
const authForms = document.querySelector("#auth-forms");
const signedInPanel = document.querySelector("#signed-in-panel");
const signedInMessage = document.querySelector("#signed-in-message");
const signoutButton = document.querySelector("#signout-button");

const detectorWorkspace = document.querySelector("#detector-workspace");
const batchSection = document.querySelector("#batch-section");
const historySection = document.querySelector("#history-section");
const metricsSection = document.querySelector("#metrics-section");

const form = document.querySelector("#analyzer-form");
const messageInput = document.querySelector("#message-input");
const characterCount = document.querySelector("#character-count");
const analyzeButton = document.querySelector("#analyze-button");

const resultPanel = document.querySelector("#result");
const resultIcon = document.querySelector("#result-icon");
const resultLabel = document.querySelector("#result-label");
const resultDescription = document.querySelector("#result-description");
const spamProbability = document.querySelector("#spam-probability");
const probabilityBar = document.querySelector("#probability-bar");
const probabilityTrack = document.querySelector(".probability-track");

const feedbackSection = document.querySelector("#feedback-section");
const feedbackForm = document.querySelector("#feedback-form");
const correctLabelInput = document.querySelector("#correct-label");
const feedbackConsent = document.querySelector("#feedback-consent");
const submitFeedbackButton = document.querySelector("#submit-feedback");
const feedbackStatus = document.querySelector("#feedback-status");

const batchForm = document.querySelector("#batch-form");
const csvInput = document.querySelector("#csv-input");
const batchButton = document.querySelector("#batch-button");
const batchStatus = document.querySelector("#batch-status");
const batchResults = document.querySelector("#batch-results");
const batchResultsBody = document.querySelector("#batch-results-body");
const downloadButton = document.querySelector("#download-results");

const historyContainer = document.querySelector("#history-container");
const historyEmpty = document.querySelector("#history-empty");
const historyBody = document.querySelector("#history-body");
const clearHistoryButton = document.querySelector("#clear-history");

const metricsStatus = document.querySelector("#metrics-status");
const metricsContent = document.querySelector("#metrics-content");
const confusionMatrixBody = document.querySelector("#confusion-matrix-body");

const HISTORY_KEY_PREFIX = "messageguard-history:";
const MAX_HISTORY_ITEMS = 30;

let latestBatchResults = [];
let currentPrediction = null;
let currentAccountEmail = null;
let pendingSigninEmail = "";
let pendingSignupEmail = "";
let pendingSignupPassword = "";


/* Sign in: password ke baad email OTP request karein. */
signinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  signinStatus.textContent = "Checking your account...";

  const email = document.querySelector("#signin-email").value.trim();
  const password = document.querySelector("#signin-password").value;

  try {
    const data = await sendJson("/api/auth/signin/request-otp", {
      email,
      password,
    });

    pendingSigninEmail = email;
    document.querySelector("#signin-otp").value = "";
    signinStatus.textContent = data.message || "OTP sent to your email.";
    signinForm.hidden = true;
    signinOtpForm.hidden = false;
    document.querySelector("#signin-otp").focus();
  } catch (error) {
    signinStatus.textContent = error.message;
  }
});


/* Sign in: OTP verify hone par protected page kholein. */
signinOtpForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  signinOtpStatus.textContent = "Verifying code...";

  const otp = document.querySelector("#signin-otp").value.trim();

  try {
    await sendJson("/api/auth/signin/verify-otp", {
      email: pendingSigninEmail,
      otp,
    });

    window.location.assign("/app");
  } catch (error) {
    signinOtpStatus.textContent = error.message;
  }
});


signinOtpBack.addEventListener("click", () => {
  signinOtpForm.hidden = true;
  signinForm.hidden = false;
  signinOtpStatus.textContent =
    "OTP dobara bhejne ke liye apni details submit karein.";
  pendingSigninEmail = "";
});


/* Signup: email par OTP bhejein. */
signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  signupStatus.textContent = "Sending verification code...";

  const email = document.querySelector("#signup-email").value.trim();
  const password = document.querySelector("#signup-password").value;

  try {
    const data = await sendJson("/api/auth/signup/request-otp", {
      email,
      password,
    });

    pendingSignupEmail = email;
    pendingSignupPassword = password;
    document.querySelector("#signup-otp").value = "";
    signupStatus.textContent = data.message || "OTP sent to your email.";
    signupForm.hidden = true;
    signupOtpForm.hidden = false;
    document.querySelector("#signup-otp").focus();
  } catch (error) {
    signupStatus.textContent = error.message;
  }
});


/* Signup: OTP verify karke account banayein aur protected page kholein. */
signupOtpForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  signupOtpStatus.textContent = "Verifying code...";

  const otp = document.querySelector("#signup-otp").value.trim();

  try {
    await sendJson("/api/auth/signup/verify-otp", {
      email: pendingSignupEmail,
      password: pendingSignupPassword,
      otp,
    });

    window.location.assign("/app");
  } catch (error) {
    signupOtpStatus.textContent = error.message;
  }
});


signupOtpBack.addEventListener("click", () => {
  signupOtpForm.hidden = true;
  signupForm.hidden = false;
  signupOtpStatus.textContent =
    "OTP dobara bhejne ke liye apni details submit karein.";
  pendingSignupEmail = "";
  pendingSignupPassword = "";
});


/* Sign out karke login page par wapas jaayein. */
signoutButton.addEventListener("click", async () => {
  try {
    await sendJson("/api/auth/logout", {});
  } catch {
    // Server unavailable ho tab bhi login page par wapas bhejein.
  }

  window.location.assign("/");
});


async function loadAccountStatus() {
  const isDetectorPage = window.location.pathname === "/app";

  try {
    const response = await fetch("/api/auth/me");

    if (!response.ok) {
      if (isDetectorPage) {
        window.location.replace("/");
        return;
      }

      showLoginPage();
      return;
    }

    const data = await response.json();
    currentAccountEmail = data.user.email;

    if (!isDetectorPage) {
      window.location.replace("/app");
      return;
    }

    showDetectorPage(data.user);
  } catch {
    if (isDetectorPage) {
      window.location.replace("/");
      return;
    }

    accountStatus.textContent = "Account status unavailable";
    showLoginPage();
  }
}


function showLoginPage() {
  authCard.hidden = false;
  authForms.hidden = false;
  signedInPanel.hidden = true;
  detectorWorkspace.hidden = true;
  batchSection.hidden = true;
  historySection.hidden = true;
  metricsSection.hidden = true;
  currentAccountEmail = null;
}


function showDetectorPage(user) {
  currentAccountEmail = user.email;

  signedInMessage.textContent = `Signed in as ${user.email}`;
  signedInPanel.hidden = false;

  // Sign out button ko dashboard ke header mein rakhein.
  document.querySelector(".site-header").appendChild(signedInPanel);
  authCard.hidden = true;

  detectorWorkspace.hidden = false;
  batchSection.hidden = false;
  historySection.hidden = false;
  metricsSection.hidden = false;

  renderHistory();
  loadMetrics();
}


async function sendJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  return readResponse(response);
}


async function readResponse(response) {
  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error("The server returned an unreadable response.");
  }

  if (!response.ok) {
    throw new Error(data.detail || "The request failed.");
  }

  return data;
}


/* Single-message spam checker. */
messageInput.addEventListener("input", () => {
  characterCount.textContent = `${messageInput.value.length} / 5000`;
});


form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const text = messageInput.value.trim();
  if (!text) {
    messageInput.focus();
    return;
  }

  setButtonLoading(analyzeButton, true, "Analyzing...");
  feedbackSection.hidden = true;
  feedbackStatus.textContent = "";

  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    const data = await readResponse(response);
    showResult(data, text);
  } catch (error) {
    currentPrediction = null;
    showSingleError(error.message);
  } finally {
    setButtonLoading(analyzeButton, false, "Analyze message");
  }
});


/* Feedback submit. */
feedbackForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!currentPrediction) return;

  const correctedLabel = correctLabelInput.value;
  const consent = feedbackConsent.checked;

  if (!correctedLabel || !consent) {
    feedbackStatus.textContent =
      "Choose the correct label and agree before submitting.";
    return;
  }

  setButtonLoading(submitFeedbackButton, true, "Submitting...");
  feedbackStatus.textContent = "";

  try {
    const data = await sendJson("/api/feedback", {
      text: currentPrediction.text,
      predicted_label: currentPrediction.label,
      corrected_label: correctedLabel,
      consent,
    });

    feedbackStatus.textContent =
      data.message || "Thank you for your feedback.";
    feedbackForm.reset();
  } catch (error) {
    feedbackStatus.textContent =
      `Could not submit feedback: ${error.message}`;
  } finally {
    setButtonLoading(submitFeedbackButton, false, "Submit feedback");
  }
});


/* CSV batch checker. */
batchForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = csvInput.files[0];
  if (!file) {
    batchStatus.textContent = "Please choose a CSV file first.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  setButtonLoading(batchButton, true, "Analyzing CSV...");
  batchStatus.textContent = "Uploading and analyzing messages...";
  batchResults.hidden = true;

  try {
    const response = await fetch("/api/predict/batch", {
      method: "POST",
      body: formData,
    });

    const data = await readResponse(response);
    latestBatchResults = data.results || [];

    if (latestBatchResults.length === 0) {
      throw new Error("The CSV did not contain any messages to analyze.");
    }

    renderBatchResults(latestBatchResults);
    addHistoryEntries(latestBatchResults);

    batchStatus.textContent =
      `Analysis complete: ${latestBatchResults.length} messages checked.`;
    batchResults.hidden = false;
  } catch (error) {
    latestBatchResults = [];
    batchStatus.textContent = `Could not analyze CSV: ${error.message}`;
  } finally {
    setButtonLoading(batchButton, false, "Analyze CSV");
  }
});


/* CSV results download. */
downloadButton.addEventListener("click", () => {
  if (latestBatchResults.length === 0) return;

  const headings = ["text", "prediction", "spam_probability"];
  const rows = latestBatchResults.map((item) => [
    item.text,
    item.label,
    Number(item.spam_probability).toFixed(4),
  ]);

  const csv = [headings, ...rows]
    .map((row) => row.map(escapeCsvCell).join(","))
    .join("\r\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = "messageguard-results.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
});


/* Clear browser history for the current account. */
clearHistoryButton.addEventListener("click", () => {
  try {
    localStorage.removeItem(getHistoryKey());
  } catch {
    // Browser storage unavailable ho tab bhi visible history clear karein.
  }

  renderHistory();
});


function setButtonLoading(button, isLoading, label) {
  button.disabled = isLoading;

  const labelElement = button.querySelector("span:first-child");
  if (labelElement) {
    labelElement.textContent = label;
  } else {
    button.textContent = label;
  }
}


function showResult(data, text) {
  const isSpam = data.label === "spam";
  const probability = Math.min(
    1,
    Math.max(0, Number(data.spam_probability))
  );
  const percentage = Math.round(probability * 100);

  currentPrediction = {
    text,
    label: data.label,
    spam_probability: probability,
  };

  resultPanel.classList.toggle("is-spam", isSpam);
  resultPanel.classList.toggle("is-ham", !isSpam);
  resultIcon.textContent = isSpam ? "!" : "✓";
  resultLabel.textContent = isSpam ? "Likely spam" : "Likely legitimate";
  resultDescription.textContent = isSpam
    ? "The message contains patterns commonly associated with spam."
    : "The message looks more like a legitimate message.";

  spamProbability.textContent = `${percentage}%`;
  probabilityBar.style.width = `${percentage}%`;
  probabilityTrack.setAttribute("aria-valuenow", String(percentage));

  feedbackForm.reset();
  feedbackStatus.textContent = "";
  feedbackSection.hidden = false;
  resultPanel.hidden = false;

  addHistoryEntry(currentPrediction);
}


function showSingleError(message) {
  resultPanel.classList.remove("is-spam", "is-ham");
  resultIcon.textContent = "!";
  resultLabel.textContent = "Could not analyze this message";
  resultDescription.textContent = message || "Please try again.";
  spamProbability.textContent = "—";
  probabilityBar.style.width = "0%";
  probabilityTrack.setAttribute("aria-valuenow", "0");
  feedbackSection.hidden = true;
  resultPanel.hidden = false;
}


function renderBatchResults(results) {
  batchResultsBody.replaceChildren();

  results.forEach((item) => {
    const row = document.createElement("tr");
    const textCell = document.createElement("td");
    const labelCell = document.createElement("td");
    const probabilityCell = document.createElement("td");

    textCell.textContent = item.text;
    labelCell.textContent = item.label === "spam" ? "Spam" : "Ham";
    probabilityCell.textContent =
      `${Math.round(Number(item.spam_probability) * 100)}%`;

    row.append(textCell, labelCell, probabilityCell);
    batchResultsBody.appendChild(row);
  });
}


/* Browser history alag-alag account ke liye save hoti hai. */
function getHistoryKey() {
  const account = currentAccountEmail || "anonymous";
  return `${HISTORY_KEY_PREFIX}${account}`;
}


function getHistory() {
  try {
    const history = JSON.parse(localStorage.getItem(getHistoryKey()) || "[]");
    return Array.isArray(history) ? history : [];
  } catch {
    return [];
  }
}


function addHistoryEntry(item) {
  const entry = {
    text: String(item.text || ""),
    label: item.label === "spam" ? "spam" : "ham",
    spam_probability: Number(item.spam_probability) || 0,
    checked_at: new Date().toISOString(),
  };

  saveHistory([entry, ...getHistory()]);
}


function addHistoryEntries(items) {
  const timestamp = new Date().toISOString();
  const entries = items.map((item) => ({
    text: String(item.text || ""),
    label: item.label === "spam" ? "spam" : "ham",
    spam_probability: Number(item.spam_probability) || 0,
    checked_at: timestamp,
  }));

  saveHistory([...entries.reverse(), ...getHistory()]);
}


function saveHistory(history) {
  try {
    localStorage.setItem(
      getHistoryKey(),
      JSON.stringify(history.slice(0, MAX_HISTORY_ITEMS))
    );
  } catch {
    // Browser storage unavailable ya full ho tab bhi checker usable rahe.
  }

  renderHistory();
}


function renderHistory() {
  const history = getHistory().slice(0, MAX_HISTORY_ITEMS);
  historyBody.replaceChildren();

  if (history.length === 0) {
    historyEmpty.hidden = false;
    historyContainer.hidden = true;
    return;
  }

  historyEmpty.hidden = true;
  historyContainer.hidden = false;

  history.forEach((item) => {
    const row = document.createElement("tr");
    const textCell = document.createElement("td");
    const labelCell = document.createElement("td");
    const probabilityCell = document.createElement("td");
    const timeCell = document.createElement("td");

    textCell.textContent = item.text;
    labelCell.textContent = item.label === "spam" ? "Spam" : "Ham";
    probabilityCell.textContent =
      `${Math.round(Number(item.spam_probability) * 100)}%`;

    const checkedAt = new Date(item.checked_at);
    timeCell.textContent = Number.isNaN(checkedAt.getTime())
      ? "—"
      : checkedAt.toLocaleString();

    row.append(textCell, labelCell, probabilityCell, timeCell);
    historyBody.appendChild(row);
  });
}


/* Model performance dashboard. */
async function loadMetrics() {
  try {
    const response = await fetch("/api/metrics");
    const metrics = await readResponse(response);

    document.querySelector("#metric-accuracy").textContent =
      formatPercent(metrics.accuracy);
    document.querySelector("#metric-precision").textContent =
      formatPercent(metrics.spam_precision);
    document.querySelector("#metric-recall").textContent =
      formatPercent(metrics.spam_recall);
    document.querySelector("#metric-f1").textContent =
      formatPercent(metrics.spam_f1);

    document.querySelector("#metric-dataset-size").textContent =
      formatNumber(metrics.dataset_messages);
    document.querySelector("#metric-training-size").textContent =
      formatNumber(metrics.training_messages);
    document.querySelector("#metric-test-size").textContent =
      formatNumber(metrics.test_messages);

    renderConfusionMatrix(
      metrics.confusion_matrix,
      metrics.confusion_matrix_labels
    );

    metricsStatus.textContent = metrics.generated_at
      ? `Metrics generated ${new Date(metrics.generated_at).toLocaleString()}.`
      : "Metrics loaded.";
    metricsContent.hidden = false;
  } catch (error) {
    metricsStatus.textContent = `Could not load metrics: ${error.message}`;
  }
}


function renderConfusionMatrix(matrix, labels) {
  confusionMatrixBody.replaceChildren();

  if (!Array.isArray(matrix) || matrix.length !== 2) {
    throw new Error("Confusion matrix data is missing or invalid.");
  }

  const labelNames = Array.isArray(labels) ? labels : ["ham", "spam"];

  matrix.forEach((values, rowIndex) => {
    const row = document.createElement("tr");
    const labelCell = document.createElement("td");

    labelCell.textContent = labelNames[rowIndex] || `Class ${rowIndex + 1}`;
    row.appendChild(labelCell);

    values.forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = formatNumber(value);
      row.appendChild(cell);
    });

    confusionMatrixBody.appendChild(row);
  });
}


function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "—";
}


function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString() : "—";
}


function escapeCsvCell(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}


loadAccountStatus();