const connectionStatus = document.querySelector("#connection-status");
const movieCount = document.querySelector("#movie-count");
const catalogCaption = document.querySelector("#catalog-caption");
const genreCount = document.querySelector("#genre-count");
const genreList = document.querySelector("#genre-list");
const recentList = document.querySelector("#recent-list");
const conversation = document.querySelector("#conversation");
const welcomeState = conversation.querySelector(".welcome-state");
const retrievalBanner = document.querySelector("#retrieval-banner");
const agentMode = document.querySelector("#agent-mode");
const importButton = document.querySelector("#import-button");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
let overview = null;
input.disabled = true;
sendButton.disabled = true;

function element(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
}

function showError(message) {
    retrievalBanner.hidden = false;
    retrievalBanner.className = "retrieval-banner error-banner";
    retrievalBanner.textContent = message;
}

async function requestJson(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
    return payload;
}

function renderGenres(genres) {
    genreCount.textContent = `${genres.length} GENRES`;
    genreList.replaceChildren();
    for (const genre of genres.slice(0, 12)) {
        const button = element("button", "genre-chip", genre);
        button.type = "button";
        button.addEventListener("click", () => askQuestion(`Recommend highly rated ${genre} movies`));
        genreList.append(button);
    }
}

function renderRecent(history) {
    recentList.replaceChildren();
    if (!history.length) {
        recentList.append(element("p", "recent-empty", "Your questions and recommendations will be remembered here."));
        return;
    }
    for (const turn of history.slice(0, 4)) {
        const item = element("button", "recent-item", turn.question);
        item.type = "button";
        item.title = "Ask a follow-up based on this graph memory";
        item.addEventListener("click", () => askQuestion(`Show me more like those from: ${turn.question}`));
        recentList.append(item);
    }
}

function renderMovieCards(movies) {
    const section = element("section", "recommendation-block");
    const heading = element("div", "recommendation-heading");
    heading.append(element("span", "node-label", "PICKS FROM THE GRAPH"));
    heading.append(element("span", "result-count", `${movies.length} ${movies.length === 1 ? "FILM" : "FILMS"}`));
    section.append(heading);

    if (!movies.length) {
        section.append(element("p", "no-results", "No matching films came back from the graph. Try another genre, performer, or year."));
        return section;
    }

    const grid = element("div", "movie-grid");
    for (const movie of movies) {
        const card = element("article", "movie-card");
        const top = element("div", "movie-card-top");
        top.append(element("span", "movie-year", movie.year || "FILM"));
        top.append(element("span", "movie-rating", movie.rating ? `★ ${Number(movie.rating).toFixed(1)}` : "UNRATED"));
        card.append(top);
        card.append(element("h4", "movie-title", movie.title));
        const details = [movie.language, movie.runtime ? `${movie.runtime} min` : null, movie.verdict]
            .filter(Boolean)
            .join(" · ");
        card.append(element("p", "movie-details", details || movie.industry || "Bollywood"));

        if (movie.theme) card.append(element("p", "movie-theme", movie.theme));
        if (movie.director) card.append(element("p", "movie-credit", `Directed by ${movie.director}`));
        if (movie.cast?.length) card.append(element("p", "movie-credit", movie.cast.join(" · ")));

        const tags = element("div", "movie-tags");
        for (const genre of (movie.genres || []).slice(0, 3)) tags.append(element("span", "movie-tag", genre));
        if (movie.platform) tags.append(element("span", "movie-tag platform-tag", movie.platform));
        card.append(tags);
        grid.append(card);
    }
    section.append(grid);
    return section;
}

function renderConversation(history) {
    if (!history.length) {
        conversation.replaceChildren(welcomeState.cloneNode(true));
        conversation.querySelectorAll("[data-question]").forEach((button) => {
            button.addEventListener("click", () => askQuestion(button.dataset.question));
        });
        return;
    }

    conversation.replaceChildren();
    const chronological = [...history].reverse();
    chronological.forEach((turn, index) => {
        const exchange = element("article", "exchange");
        const customerRow = element("div", "message-row customer-row");
        customerRow.append(element("span", "message-avatar", "YOU"));
        const customerContent = element("div", "message-content");
        customerContent.append(element("span", "message-label", "YOUR QUESTION"));
        customerContent.append(element("p", "message-bubble customer-bubble", turn.question));
        customerRow.append(customerContent);
        exchange.append(customerRow);

        const agentRow = element("div", "message-row agent-row");
        agentRow.append(element("span", "agent-avatar", "M"));
        const agentContent = element("div", "message-content");
        agentContent.append(element("span", "message-label", "MOVIEMAXX · GRAPH GUIDE"));
        agentContent.append(element("p", "message-bubble agent-bubble", turn.answer));
        agentRow.append(agentContent);
        exchange.append(agentRow);
        if (index === chronological.length - 1) exchange.append(renderMovieCards(turn.movies || []));
        conversation.append(exchange);
    });
    conversation.scrollTop = conversation.scrollHeight;
}

function renderOverview() {
    if (!overview) return;
    movieCount.textContent = Number(overview.movie_count).toLocaleString();
    catalogCaption.textContent = `${overview.genres.length} connected genres · cast, directors, and streaming links`;
    renderGenres(overview.genres);
    renderRecent(overview.history);
    renderConversation(overview.history);
}

function setAgentMode(mode) {
    agentMode.textContent = mode === "groq" ? "Groq · graph grounded" : "Local graph guide";
}

async function loadOverview() {
    try {
        const health = await requestJson("/api/health");
        setAgentMode(health.agent_mode);
        overview = await requestJson("/api/overview");
        connectionStatus.innerHTML = '<span class="status-dot"></span> Neo4j connected';
        connectionStatus.classList.add("is-connected");
        renderOverview();
        input.disabled = false;
        sendButton.disabled = false;
    } catch (error) {
        connectionStatus.innerHTML = '<span class="status-dot"></span> Neo4j unavailable';
        connectionStatus.classList.add("is-offline");
        catalogCaption.textContent = "Connect Neo4j to import and search the movie graph.";
        showError(error.message);
    }
}

async function askQuestion(question) {
    const text = question.trim();
    if (!text || sendButton.disabled) return;
    input.value = "";
    input.style.height = "auto";
    sendButton.disabled = true;
    importButton.disabled = true;
    retrievalBanner.hidden = false;
    retrievalBanner.className = "retrieval-banner";
    retrievalBanner.textContent = "Searching connected movie, genre, and people nodes…";
    try {
        const result = await requestJson("/api/chat", {
            method: "POST",
            body: JSON.stringify({ question: text }),
        });
        overview.history = result.history;
        setAgentMode(result.agent_mode);
        retrievalBanner.textContent = overview.history.length > 1
            ? "Neo4j memory retrieved · prior searches and recommendations used for context"
            : "Neo4j graph searched · recommendations saved for your next question";
        renderRecent(overview.history);
        renderConversation(overview.history);
        input.focus();
    } catch (error) {
        showError(error.message);
    } finally {
        sendButton.disabled = false;
        importButton.disabled = false;
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    askQuestion(input.value);
});

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
});

document.querySelectorAll("[data-question]").forEach((button) => {
    button.addEventListener("click", () => askQuestion(button.dataset.question));
});

importButton.addEventListener("click", async () => {
    importButton.disabled = true;
    importButton.classList.add("is-loading");
    catalogCaption.textContent = "Reading the CSV and syncing graph relationships…";
    try {
        overview = await requestJson("/api/import", { method: "POST" });
        renderOverview();
        retrievalBanner.hidden = false;
        retrievalBanner.className = "retrieval-banner";
        retrievalBanner.textContent = `${Number(overview.movie_count).toLocaleString()} movies synced from CSV into Neo4j.`;
    } catch (error) {
        showError(error.message);
        catalogCaption.textContent = "Catalog sync failed.";
    } finally {
        importButton.disabled = false;
        importButton.classList.remove("is-loading");
    }
});

loadOverview();
