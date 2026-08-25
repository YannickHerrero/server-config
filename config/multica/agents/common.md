# Cadre d'execution commun

Tu travailles sur le serveur personnel de Yannick depuis une tache Multica. Comprends les demandes en francais ou en anglais et reponds a Yannick en francais. Le code, les noms de branches, les commits et les commandes restent en anglais.

Au debut de chaque tache:

1. Lis le brief Multica injecte dans `AGENTS.md`, puis toutes les instructions du projet applicables.
2. Identifie exactement l'issue, le projet, le repo, la branche par defaut et ton role dans le pipeline.
3. Lance `multica-project-config get` pour lire la politique locale du repo original. Si la commande echoue, arrete les actions irreversibles et explique ce qui manque.
4. Inspecte l'etat Git avant toute modification. Ne restaure, ne stage et ne modifie jamais des changements qui ne viennent pas de ta tache.

Regles non negociables:

- Ne committe jamais `.multica/`, meme avec `git add -f`. Verifie la liste des fichiers stages et celle de la PR.
- Ne stocke aucun secret, token, session ou credential dans Git, Multica, un commentaire ou `project.yaml`.
- N'emploie pas `pkill`, `killall` ni un kill par motif. Lance les serveurs avec `multica-run run -- <commande>`, consulte-les avec `multica-run list` et arrete uniquement leur `run_id` avec `multica-run stop <run_id>`.
- Lance Gradle, l'emulateur Android, Chromium et les builds Docker avec `multica-heavy-run -- <commande>`.
- N'utilise que les ports fournis par `MULTICA_PORT`, `MULTICA_PORT_BASE` et `MULTICA_PORT_END`.
- Detecte la branche par defaut. Ne suppose jamais qu'elle s'appelle `main`.
- Respecte les verrous, checks et procedures du repo. Une instruction du projet plus stricte gagne toujours.
- Utilise les commentaires et metadata de l'issue pour les handoffs. Les cles communes sont `pipeline_status`, `pr_url`, `branch`, `qa_verdict`, `merge_commit` et `deployment_status`.
- Une tache declenchee par un commentaire doit repondre dans le thread demande par le brief Multica.
- Ne deploie, ne merge ou ne pousse que si ton role et la politique locale l'autorisent explicitement.

Avant de terminer, nettoie tes processus, resume les preuves obtenues, distingue les tests automatiques des controles manuels et transmets l'issue au prochain agent indique par ton role.
