const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const uploadStatus = document.getElementById("uploadStatus");
const questionInput = document.getElementById("questionInput");
const askBtn = document.getElementById("askBtn");
const retrieveBtn = document.getElementById("retrieveBtn");
const resetBtn = document.getElementById("resetBtn");
const copyLastAnswerBtn = document.getElementById("copyLastAnswerBtn");
const topKInput = document.getElementById("topK");
const chatMessages = document.getElementById("chatMessages");
const sourcesPanel = document.getElementById("sourcesPanel");
const metaPanel = document.getElementById("metaPanel");
const logsBox = document.getElementById("logsBox");

let lastBotAnswer = "";

function addMessage(text, role = "bot", meta = "") {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role}`;

  const box = document.createElement("div");

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  box.appendChild(bubble);

  if (meta) {
    const metaDiv = document.createElement("div");
    metaDiv.className = "bot-meta";
    metaDiv.textContent = meta;
    box.appendChild(metaDiv);
  }

  wrapper.appendChild(box);
  chatMessages.appendChild(wrapper);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setLoading(isLoading) {
  uploadBtn.disabled = isLoading;
  askBtn.disabled = isLoading;
  retrieveBtn.disabled = isLoading;
  resetBtn.disabled = isLoading;
  copyLastAnswerBtn.disabled = isLoading;
}

function renderSources(sources) {
  sourcesPanel.innerHTML = "<h3>Kaynak Parçalar</h3>";

  if (!sources || sources.length === 0) {
    sourcesPanel.innerHTML += "<p>Kaynak bulunamadı.</p>";
    return;
  }

  sources.forEach((src, idx) => {
    const details = document.createElement("details");
    details.className = "source-item";

    const summary = document.createElement("summary");
    summary.className = "source-summary";
    summary.innerHTML = `
      <div class="summary-title">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--accent)"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
        Kanıt Kartı ${idx + 1}
      </div>
      <svg class="summary-chevron" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
    `;

    const contentDiv = document.createElement("div");
    contentDiv.className = "source-content";

    const meta = document.createElement("div");
    meta.className = "source-meta";
    meta.textContent = `Kaynak ${idx + 1} | Sayfa: ${src.page ?? "-"} | Chunk ID: ${src.chunk_id}`;

    const pre = document.createElement("pre");
    pre.textContent = src.text;

    contentDiv.appendChild(meta);
    contentDiv.appendChild(pre);

    details.appendChild(summary);
    details.appendChild(contentDiv);

    sourcesPanel.appendChild(details);
  });
}

function renderMetaPanel(sourceCount, retrievedPages, promptContextLength) {
  metaPanel.innerHTML = `
    <h3>Son Yanıt Özeti</h3>
    <p><strong>Kaynak Sayısı:</strong> ${sourceCount}</p>
    <p><strong>Sayfalar:</strong> ${retrievedPages.length ? retrievedPages.join(", ") : "-"}</p>
    <p><strong>Bağlam Uzunluğu:</strong> ${promptContextLength}</p>
  `;
}

uploadBtn.addEventListener("click", async () => {
  const file = fileInput.files[0];
  if (!file) {
    uploadStatus.textContent = "Lütfen bir dosya seçin.";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    setLoading(true);
    uploadStatus.textContent = "Doküman işleniyor...";

    const response = await fetch("/ingest", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
      uploadStatus.textContent = data.detail || "Yükleme hatası";
      return;
    }

    uploadStatus.textContent = `${data.filename} işlendi | Sayfa: ${data.pages} | Chunk: ${data.total_chunks}`;
    addMessage(
      `Doküman indekslendi: ${data.filename}`,
      "bot",
      `Toplam sayfa: ${data.pages} | Toplam chunk: ${data.total_chunks}`
    );
  } catch (error) {
    uploadStatus.textContent = "Beklenmeyen bir hata oluştu.";
  } finally {
    setLoading(false);
  }
});

askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  const top_k = Number(topKInput.value || 6);

  if (!question) return;

  addMessage(question, "user");
  questionInput.value = "";

  try {
    setLoading(true);

    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k }),
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage(data.detail || "Soru sorulurken hata oluştu.", "bot");
      return;
    }

    lastBotAnswer = data.answer;

    addMessage(
      data.answer,
      "bot",
      `Kaynak sayısı: ${data.source_count} | Sayfalar: ${data.retrieved_pages.join(", ")} | Bağlam uzunluğu: ${data.prompt_context_length}`
    );

    renderSources(data.sources);
    renderMetaPanel(data.source_count, data.retrieved_pages, data.prompt_context_length);
  } catch (error) {
    addMessage("İstek sırasında beklenmeyen bir hata oluştu.", "bot");
  } finally {
    setLoading(false);
  }
});

retrieveBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim();
  const top_k = Number(topKInput.value || 6);

  if (!question) return;

  try {
    setLoading(true);

    const response = await fetch("/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k }),
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage(data.detail || "Retrieve sırasında hata oluştu.", "bot");
      return;
    }

    addMessage(
      "Retrieve tamamlandı. En alakalı kaynak parçalar aşağıda gösterildi.",
      "bot",
      `Toplam sonuç: ${data.total_results}`
    );

    renderSources(data.results);
  } catch (error) {
    addMessage("Retrieve isteği sırasında beklenmeyen bir hata oluştu.", "bot");
  } finally {
    setLoading(false);
  }
});

resetBtn.addEventListener("click", async () => {
  try {
    setLoading(true);

    const response = await fetch("/reset", {
      method: "POST",
    });

    const data = await response.json();

    if (!response.ok) {
      addMessage(data.detail || "Reset işlemi başarısız oldu.", "bot");
      return;
    }

    lastBotAnswer = "";
    addMessage("İndeks sıfırlandı. Yeni bir doküman yükleyebilirsiniz.", "bot");
    uploadStatus.textContent = "İndeks temizlendi.";
    renderSources([]);
    renderMetaPanel(0, [], 0);
  } catch (error) {
    addMessage("Reset işlemi sırasında beklenmeyen bir hata oluştu.", "bot");
  } finally {
    setLoading(false);
  }
});

copyLastAnswerBtn.addEventListener("click", async () => {
  if (!lastBotAnswer) {
    addMessage("Kopyalanacak bir bot cevabı bulunmuyor.", "bot");
    return;
  }

  try {
    await navigator.clipboard.writeText(lastBotAnswer);
    addMessage("Son bot cevabı panoya kopyalandı.", "bot");
  } catch (error) {
    addMessage("Kopyalama sırasında bir hata oluştu.", "bot");
  }
});

async function fetchLogs() {
  if (!logsBox) return;
  try {
    const res = await fetch("/logs");
    const data = await res.json();
    
    const isScrolledToBottom = logsBox.scrollHeight - logsBox.clientHeight <= logsBox.scrollTop + 5;
    
    logsBox.innerHTML = "";
    data.logs.forEach(log => {
      const row = document.createElement("div");
      row.className = "log-entry";
      const lvlClass = (log.level || "INFO").toLowerCase();
      
      row.innerHTML = `
        <span class="log-time">${log.timestamp}</span>
        <span class="log-level ${lvlClass}">[${log.level}]</span>
        <span class="log-msg">${log.name}: ${log.message}</span>
      `;
      logsBox.appendChild(row);
    });
    
    if (isScrolledToBottom) {
      logsBox.scrollTop = logsBox.scrollHeight;
    }
  } catch (err) {
    // silently fail
  }
}

if (logsBox) {
  setInterval(fetchLogs, 1000);
  fetchLogs();
}