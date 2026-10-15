document.addEventListener('DOMContentLoaded', () => {
    const promptInput = document.getElementById('prompt-input');
    const skillToggle = document.getElementById('skill-toggle');
    const skillLabel = document.getElementById('skill-status-label');
    const btnSubmit = document.getElementById('btn-submit');
    const btnClear = document.getElementById('btn-clear');
    const samplesContainer = document.getElementById('samples-container');

    const verdictCard = document.getElementById('verdict-card');
    const verdictBadge = document.getElementById('verdict-badge');
    const threatBadge = document.getElementById('threat-badge');
    const riskScoreValue = document.getElementById('risk-score-value');
    const riskBarFill = document.getElementById('risk-bar-fill');
    const verdictExplanation = document.getElementById('verdict-explanation');
    const verdictResponse = document.getElementById('verdict-response');
    const jsonCode = document.getElementById('json-code');

    const statTotal = document.getElementById('stat-total');
    const statBlocked = document.getElementById('stat-blocked');
    const statAllowed = document.getElementById('stat-allowed');
    const statRate = document.getElementById('stat-rate');

    // Mise à jour du switch
    skillToggle.addEventListener('change', () => {
        if (skillToggle.checked) {
            skillLabel.textContent = "Skill Activé (PROTÉGÉ)";
            skillLabel.className = "skill-label active";
        } else {
            skillLabel.textContent = "Skill Désactivé (VULNÉRABLE)";
            skillLabel.className = "skill-label inactive";
        }
    });

    // Chargement des prompts d'exemple
    fetch('/api/samples')
        .then(res => res.json())
        .then(samples => {
            samplesContainer.innerHTML = '';
            samples.forEach(sample => {
                const btn = document.createElement('button');
                btn.className = `chip-btn ${sample.expected_verdict === 'BLOCKED' ? 'danger-chip' : ''}`;
                btn.textContent = `${sample.id}: ${sample.category}`;
                btn.title = sample.description;
                btn.addEventListener('click', () => {
                    promptInput.value = sample.prompt;
                    promptInput.focus();
                });
                samplesContainer.appendChild(btn);
            });
        })
        .catch(err => console.error("Erreur de chargement des samples", err));

    // Effacer
    btnClear.addEventListener('click', () => {
        promptInput.value = '';
        verdictCard.classList.add('hidden');
    });

    // Analyser
    btnSubmit.addEventListener('click', async () => {
        const text = promptInput.value.trim();
        if (!text) {
            alert("Veuillez saisir un prompt ou cliquer sur un scénario d'exemple.");
            return;
        }

        btnSubmit.disabled = true;
        btnSubmit.innerHTML = '<span class="btn-icon">⏳</span> Analyse en cours...';

        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: text,
                    use_skill: skillToggle.checked
                })
            });

            const data = await res.json();
            const analysis = data.analysis;
            const stats = data.current_stats;
            const telemetry = data.telemetry;

            // Afficher le verdict
            verdictCard.classList.remove('hidden');

            if (analysis.verdict === 'BLOCKED') {
                verdictBadge.textContent = 'BLOCKED (ATTAQUE NEUTRALISÉE)';
                verdictBadge.className = 'verdict-badge blocked';
                threatBadge.textContent = `Vecteur : ${analysis.attack_vector}`;
                riskBarFill.style.background = '#ef4444';
            } else {
                verdictBadge.textContent = analysis.mode === 'WITHOUT_SKILL' ? 'ALLOWED (AUCUN FILTRE)' : 'ALLOWED (REQUÊTE LÉGITIME)';
                verdictBadge.className = 'verdict-badge allowed';
                threatBadge.textContent = analysis.mode === 'WITHOUT_SKILL' ? 'Vulnérable' : 'Sain';
                riskBarFill.style.background = '#10b981';
            }

            const riskPct = Math.round(analysis.risk_score * 100);
            riskScoreValue.textContent = `${riskPct}%`;
            riskBarFill.style.width = `${riskPct}%`;

            verdictExplanation.textContent = analysis.explanation;
            verdictResponse.textContent = analysis.response_text;

            // Mettre à jour l'afficheur JSON Cloud Logging
            jsonCode.textContent = JSON.stringify(telemetry.payload, null, 2);

            // Mettre à jour les compteurs
            statTotal.textContent = stats.total_requests;
            statBlocked.textContent = stats.blocked_attacks;
            statAllowed.textContent = stats.allowed_requests;

            const rate = stats.total_requests > 0
                ? Math.round((stats.blocked_attacks / Math.max(1, stats.blocked_attacks + (stats.total_requests - stats.blocked_attacks - stats.allowed_requests))) * 100)
                : 100;
            statRate.textContent = `${rate}%`;

        } catch (error) {
            console.error("Erreur d'analyse", error);
            alert("Erreur lors de la communication avec l'API.");
        } finally {
            btnSubmit.disabled = false;
            btnSubmit.innerHTML = '<span class="btn-icon">⚡</span> Analyser le Prompt';
        }
    });

    // --- NAVIGATION PAR ONGLETS ---
    const tabBtnGuard = document.getElementById('tab-btn-guard');
    const tabBtnSearch = document.getElementById('tab-btn-search');
    const viewGuard = document.getElementById('view-guard');
    const viewSearch = document.getElementById('view-search');

    tabBtnGuard.addEventListener('click', () => {
        tabBtnGuard.classList.add('active');
        tabBtnSearch.classList.remove('active');
        viewGuard.classList.remove('hidden');
        viewSearch.classList.add('hidden');
    });

    tabBtnSearch.addEventListener('click', () => {
        tabBtnSearch.classList.add('active');
        tabBtnGuard.classList.remove('active');
        viewSearch.classList.remove('hidden');
        viewGuard.classList.add('hidden');
    });

    // --- RECHERCHE HYBRIDE BM25 + SÉMANTIQUE + RERANKER ---
    const searchInput = document.getElementById('search-query-input');
    const btnSearch = document.getElementById('btn-search');
    const searchResultsContainer = document.getElementById('search-results-container');
    const searchChips = document.querySelectorAll('.search-chip');

    searchChips.forEach(chip => {
        chip.addEventListener('click', () => {
            searchInput.value = chip.getAttribute('data-q');
            performHybridSearch();
        });
    });

    btnSearch.addEventListener('click', () => {
        performHybridSearch();
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') performHybridSearch();
    });

    async function performHybridSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            alert("Veuillez saisir une recherche.");
            return;
        }

        btnSearch.disabled = true;
        btnSearch.innerHTML = '<span>⏳</span> Recherche...';

        try {
            const res = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, top_k: 5 })
            });

            const data = await res.json();
            renderSearchResults(data.results);
        } catch (err) {
            console.error("Erreur recherche hybride", err);
            alert("Erreur lors de la recherche hybride.");
        } finally {
            btnSearch.disabled = false;
            btnSearch.innerHTML = '<span>🔍</span> Rechercher & Reranker';
        }
    }

    function renderSearchResults(results) {
        searchResultsContainer.innerHTML = '';
        if (!results || results.length === 0) {
            searchResultsContainer.innerHTML = '<p class="panel-desc">Aucun produit ne correspond à cette recherche.</p>';
            return;
        }

        results.forEach((r, idx) => {
            const item = r.item;
            const card = document.createElement('div');
            card.className = 'result-card';

            const geminiLiveBadge = r.is_gemini_live
                ? '<span class="score-pill rank-badge">✨ Embeddings Gemini Live</span>'
                : '<span class="score-pill" style="background:rgba(255,255,255,0.05);color:#94a3b8">⚙️ Embeddings Locaux</span>';

            card.innerHTML = `
                <div class="result-card-header">
                    <div>
                        <span class="result-title">#${idx + 1} ${item.name}</span>
                        <span class="result-category">${item.category}</span>
                    </div>
                    <span class="result-price">${item.price.toFixed(2)} €</span>
                </div>
                <p class="result-desc">${item.description}</p>
                <div class="scores-row">
                    <span class="score-pill rank-badge">Rang #${idx + 1}</span>
                    <span class="score-pill bm25">BM25 (Mots-clés) : ${r.bm25_score}</span>
                    <span class="score-pill semantic">Sémantique : ${r.semantic_score}</span>
                    <span class="score-pill rerank">Score Reranker : ${r.rerank_score}</span>
                    ${geminiLiveBadge}
                </div>
            `;
            searchResultsContainer.appendChild(card);
        });
    }
});
