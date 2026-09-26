document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");
    const sendButton = document.getElementById("send-button");
    const conversation = document.getElementById("conversation");
    const movieCountEl = document.getElementById("movie-count");
    const genreListEl = document.getElementById("genre-list");
    const genreCountEl = document.getElementById("genre-count");
    const recentListEl = document.getElementById("recent-list");
    const importButton = document.getElementById("import-button");
    const connectionStatusEl = document.getElementById("connection-status");
    const agentModeEl = document.getElementById("agent-mode");
    const mcpStatusEl = document.getElementById("mcp-status");

    let currentWatchContext = "solo";

    // Watch Context Selector Chips
    const contextChips = document.querySelectorAll(".context-chip");
    contextChips.forEach(chip => {
        chip.addEventListener("click", () => {
            contextChips.forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            currentWatchContext = chip.getAttribute("data-context") || "solo";
        });
    });

    if (messageInput) {
        messageInput.addEventListener("input", () => {
            messageInput.style.height = "auto";
            messageInput.style.height = `${Math.min(messageInput.scrollHeight, 120)}px`;
        });
    }

    async function loadOverview() {
        try {
            const response = await fetch("/api/overview");
            if (!response.ok) throw new Error("Failed to load overview");
            const data = await response.json();
            
            if (movieCountEl) movieCountEl.textContent = data.movie_count ? data.movie_count.toLocaleString() : "3,000+";
            if (agentModeEl) agentModeEl.textContent = "Multi-Agent Graph RAG Active";
            if (connectionStatusEl) {
                connectionStatusEl.innerHTML = `<span class="status-dot"></span> Connected to Neo4j`;
            }
            if (mcpStatusEl) {
                const mcpReady = data.mcp_status && data.mcp_status.connected;
                mcpStatusEl.innerHTML = `<span class="status-dot"></span> ${mcpReady ? "MCP & Graph RAG Active" : "Graph RAG Active"}`;
            }

            renderGenres(data.genres || []);
            renderHistory(data.history || []);
        } catch (err) {
            console.error("Overview error:", err);
            if (connectionStatusEl) {
                connectionStatusEl.innerHTML = `<span class="status-dot" style="background:#f43f5e"></span> Disconnected`;
            }
        }
    }

    function renderGenres(genres) {
        if (!genreListEl) return;
        genreListEl.innerHTML = "";
        if (genreCountEl) genreCountEl.textContent = `${genres.length} GENRES`;
        
        genres.forEach(genre => {
            const tag = document.createElement("button");
            tag.className = "genre-tag";
            tag.type = "button";
            tag.textContent = genre;
            tag.addEventListener("click", () => {
                if (messageInput) {
                    messageInput.value = `Find me top 5 ${genre} movies`;
                    messageInput.focus();
                }
            });
            genreListEl.appendChild(tag);
        });
    }

    function renderHistory(history) {
        if (!recentListEl) return;
        if (!history || history.length === 0) {
            recentListEl.innerHTML = `<p class="recent-empty">Your recent searches will be saved here.</p>`;
            return;
        }

        recentListEl.innerHTML = "";
        history.slice(0, 5).forEach(turn => {
            const item = document.createElement("div");
            item.className = "recent-item";
            item.style.padding = "8px 0";
            item.style.borderBottom = "1px solid var(--line)";
            item.style.cursor = "pointer";
            item.innerHTML = `<strong style="color:var(--ink);display:block;">${escapeHtml(turn.question)}</strong>`;
            item.addEventListener("click", () => {
                if (messageInput) {
                    messageInput.value = turn.question;
                    messageInput.focus();
                }
            });
            recentListEl.appendChild(item);
        });
    }

    function appendUserMessage(text) {
        const welcome = conversation.querySelector(".welcome-state");
        if (welcome) welcome.remove();

        const msgNode = document.createElement("div");
        msgNode.className = "user-message";
        msgNode.style.alignSelf = "flex-end";
        msgNode.style.background = "var(--purple)";
        msgNode.style.color = "#fff";
        msgNode.style.padding = "12px 18px";
        msgNode.style.borderRadius = "14px 14px 2px 14px";
        msgNode.style.maxWidth = "80%";
        msgNode.style.fontSize = "14px";
        msgNode.textContent = text;
        conversation.appendChild(msgNode);
        conversation.scrollTop = conversation.scrollHeight;
    }

    function renderAgentResponse(data) {
        const agentNode = document.createElement("div");
        agentNode.className = "agent-response";
        agentNode.style.alignSelf = "flex-start";
        agentNode.style.width = "100%";

        if (data.status === "BLOCKED") {
            agentNode.innerHTML = `
                <div class="guardrail-alert">
                    <strong>🛡️ P2 Harness Engineering Guardrail Alert</strong>
                    <p style="margin:6px 0 0 0;">${escapeHtml(data.reply)}</p>
                </div>
            `;
        } else {
            let html = `<div style="background:var(--surface-card);border:1px solid var(--line);border-radius:14px;padding:20px;">`;
            
            // Format summary text without duplicate lists
            const cleanSummary = escapeHtml(data.reply).replace(/\n/g, "<br>");
            html += `<p style="font-size:14px;line-height:1.6;margin:0 0 16px 0;color:var(--ink);">${cleanSummary}</p>`;

            if (data.movies && data.movies.length > 0) {
                html += `<div class="movie-cards-grid">`;
                const movieIds = data.movies.map(m => m.id);

                data.movies.forEach((movie, idx) => {
                    const rating = movie.rating ? `⭐ ${movie.rating}/10` : "Unrated";
                    const platform = movie.platform ? `🍿 ${movie.platform}` : "🎟️ Rental/VOD";
                    const score = movie.hybrid_score ? `${Math.round(movie.hybrid_score * 100)}% Match` : "Graph Match";
                    const genres = (movie.genres || []).join(", ");

                    html += `
                        <div class="movie-card">
                            <div class="movie-rank">#${idx + 1}</div>
                            <div class="movie-details">
                                <h4>${escapeHtml(movie.title)} (${movie.year || "N/A"})</h4>
                                <div class="movie-meta-row">
                                    <span class="rating-badge">${rating}</span>
                                    <span class="platform-badge">${platform}</span>
                                    <span style="color:var(--muted);">${escapeHtml(genres)}</span>
                                </div>
                            </div>
                            <div class="rag-score-badge">${score}</div>
                        </div>
                    `;
                });
                html += `</div>`;

                // Add Neo4j Subgraph Explorer button
                html += `
                    <div style="margin-top:16px;display:flex;justify-content:space-between;align-items:center;">
                        <a href="/graph" target="_blank" class="prompt-chip" style="text-decoration:none;display:inline-flex;align-items:center;gap:6px;">
                            🕸️ Open Interactive Knowledge Graph Explorer ↗
                        </a>
                    </div>
                `;
            }

            html += `</div>`;
            agentNode.innerHTML = html;
        }

        conversation.appendChild(agentNode);
        conversation.scrollTop = conversation.scrollHeight;
    }

    if (chatForm) {
        chatForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const question = messageInput.value.trim();
            if (!question) return;

            appendUserMessage(question);
            messageInput.value = "";
            messageInput.style.height = "auto";
            if (sendButton) sendButton.disabled = true;

            try {
                const response = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        question: question,
                        watch_context: currentWatchContext
                    })
                });

                if (!response.ok) throw new Error("Server error processing request");
                const data = await response.json();
                renderAgentResponse(data);
                if (data.history) renderHistory(data.history);
            } catch (err) {
                renderAgentResponse({
                    status: "ERROR",
                    reply: "⚠️ Unable to communicate with Moviemaxx services. Please verify Neo4j database connection."
                });
            } finally {
                if (sendButton) sendButton.disabled = false;
            }
        });
    }

    // Suggestion Buttons
    document.querySelectorAll(".suggestion-button, .prompt-chip").forEach(btn => {
        btn.addEventListener("click", () => {
            const q = btn.getAttribute("data-question");
            if (q && messageInput) {
                messageInput.value = q;
                chatForm.dispatchEvent(new Event("submit"));
            }
        });
    });

    if (importButton) {
        importButton.addEventListener("click", async () => {
            importButton.disabled = true;
            importButton.textContent = "Syncing Neo4j & RAG Index…";
            try {
                await fetch("/api/import", { method: "POST" });
                await loadOverview();
                alert("Catalog and Graph RAG index successfully re-synced with 3,000+ movies!");
            } catch (err) {
                alert("Catalog import failed. Check Neo4j credentials.");
            } finally {
                importButton.disabled = false;
                importButton.textContent = "↻ Sync CSV & RAG Index";
            }
        });
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    loadOverview();
});
