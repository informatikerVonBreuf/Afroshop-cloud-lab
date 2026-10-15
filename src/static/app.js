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
});
