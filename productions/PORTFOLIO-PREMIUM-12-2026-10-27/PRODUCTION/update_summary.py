import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = ["# Portfolio premium : état réel", "", "Photographies Pexels uniquement. Aucun showreel ni changement du site. Aucun film publié.",
        "", "Les coûts worker sont partiels, pas des factures. Les démarrages interrompus et les frais non ventilés sont conservés au journal global. Une classe B ou C n'autorise jamais une publication.",
        "", "| Film | Catégorie | Préparation | Génération | MP4 réel | Dépense estimée | Qualité | Défauts / réserve | Recommandation |",
        "|---|---|---|---|---|---|---|---|---|"]
ledger = []
for folder in sorted(ROOT.glob("[0-9][0-9]-*")):
    plan = json.loads((folder / "PRODUCTION_PLAN.json").read_text(encoding="utf-8"))
    status = json.loads((folder / "REPORTS/STATUS.json").read_text(encoding="utf-8"))
    brief = json.loads((ROOT / "PRODUCTION/campaign.json").read_text(encoding="utf-8"))
    concept = next(f for f in brief["films"] if f["id"] == folder.name)
    receipts = []
    for path in list((folder / "REPORTS").glob("shot-*-receipt.json")) + list((folder / "REPORTS/ATTEMPTS").glob("shot-*.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipts.append(receipt)
        ledger.append({"film": folder.name, "shot": receipt["shot"], "attempt": receipt["attempt"],
                       "call_id": receipt.get("call_id"), "status": receipt["status"],
                       "partial_worker_estimate_usd": receipt.get("partial_compute_estimate_usd"),
                       "actual_billed_usd": None, "receipt": str(path.relative_to(ROOT)).replace("\\", "/")})
    partial = sum(r.get("partial_compute_estimate_usd") or 0 for r in receipts)
    failed = sum(r["status"] == "failed" for r in receipts)
    complete = sum(r["status"] == "technically_checked_visual_review_pending" for r in receipts)
    web = folder / plan["output"]["web"]
    has_export = web.is_file() and web.stat().st_size > 0
    mp4 = f"[MP4]({folder.name}/EXPORTS/{web.name})" if has_export else f"Pas de final ; [test rejeté 5 s]({folder.name}/{status['benchmark_mp4']})" if status.get("benchmark_mp4") else "Aucun"
    generation = "MP4 exporté" if has_export else "Suspendu" if not plan["executable"] else f"{complete}/3 prises ; en cours" if receipts else "Non lancé"
    prep = "Concept complet ; production suspendue" if not plan["executable"] else "Sources, prompts et storyboard prêts"
    quality = status.get("quality") or "Non évalué"
    defects = "; ".join(status.get("defects", [])) or ("Casting réel et avatar non validés" if not plan["executable"] else "Revue du vrai MP4 en attente" if has_export else "Pas de jugement sans vidéo")
    cost = f"{partial:.4f} USD worker partiel" if receipts else "0 appel GPU"
    if failed:
        cost += f" ; {failed} démarrage interrompu non ventilé"
    recommendation = status.get("recommendation") or ("Conserver les crédits" if not plan["executable"] else "Prêt pour un prochain lot contrôlé")
    cells = [plan["title"], concept["category"], prep, generation, mp4, cost, quality, defects, recommendation]
    rows.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
budget = json.loads((ROOT / "PRODUCTION/BUDGET.json").read_text(encoding="utf-8"))
rows += ["", "## Résultat réel", "", "Douze concepts préparés. Neuf films montés : huit candidats B et un film C rejeté. BEAUTY ROUTINE est suspendu après deux tests sans MP4 final ; les UGC 09 et 10 ne sont pas lancés. Aucun classement A ni publication automatique.",
         "", "## Budget et preuve", "", f"Compte lucj76861. Solde initial : 29,80 USD ; usage initial : 0,20 USD. Dernier solde observé : {budget['latest_credit_usd_dashboard_rounded']:.2f} USD. Consommation de campagne estimée par différence : {budget['estimated_campaign_consumption_dashboard_usd']:.2f} USD. Réserve de 10 USD préservée, limite mensuelle workspace de 20 USD. Compteurs asynchrones, facture définitive indisponible. Voir PRODUCTION/FINANCIAL_REPORT.md et SPEND_LEDGER.json.",
         "", "## Préselection à inspecter", "", "Priorité : GOLDEN REVEAL pour le packshot doré, ARCHITECTURAL LIVING pour la stabilité de la pièce, ACCESSORY ICON pour la matière, PRODUCT ENERGY pour le montage Social Ads, TRANSFORMATION pour le changement d'ambiance. Leur classement A nécessite une lecture et une écoute critiques.",
         "", "SKINCARE SENSORIEL reste à vérifier sur la pipette ; DARK LUXURY sur la lisibilité des noirs et le contour lumineux ; FASHION CAMPAIGN sur le micro-motif textile et les raccords de pose. PROBLÈME / SOLUTION est écarté ; BEAUTY ROUTINE n'a pas de montage final. Les limites des personnages UGC ne sont pas considérées validées.",
         "", "## Récupération", "", "Les masters, versions web, miniatures Pexels, prises réelles, sources et rapports sont conservés dans chaque dossier. Le paquet DELIVERY/WEB fournit les versions préférées et isole les rejets et tests sans final."]
final_delivery = ROOT / "PRODUCTION/GITHUB_FINAL_DELIVERY.json"
if final_delivery.is_file():
    delivery = json.loads(final_delivery.read_text(encoding="utf-8"))
    rows += ["", f"[Archives GitHub finales]({delivery['run_url']}) : choisir WEB-PREVIEWS pour le visionnage ou CAMPAIGN-SOURCES pour la campagne complète. Expirations vérifiées dans PRODUCTION/GITHUB_FINAL_DELIVERY.json. Le paquet web a été téléchargé et ses SHA256 comparés aux vrais fichiers locaux."]
else:
    rows += ["", "Archives finales en préparation. L'archive des [quatre premiers films](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40654464396) est déjà disponible jusqu'au 26 janvier 2027 ; ses huit exports ont été réellement téléchargés et vérifiés par SHA256. Voir PRODUCTION/GITHUB_LOT_02_12_DELIVERY.json."]
rows += ["", "La revue visuelle repose sur des photogrammes des vrais MP4, par prise et montage, et des détails pleine définition. Elle ne remplace pas un visionnage continu avec écoute critique. Les contrôles automatiques vérifient la technique, sans valider l'esthétique. Les validations reçues pendant la production autorisent les lots suivants ; la sélection portfolio reste ultérieure."]
(ROOT / "PORTFOLIO_SUMMARY.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
report = {"updated_at": datetime.now(timezone.utc).isoformat(), "calls": ledger,
          "known_partial_worker_estimate_usd": round(sum(r["partial_worker_estimate_usd"] or 0 for r in ledger), 4),
          "actual_campaign_billed_usd": None, "failed_starts_included_in_call_count": True,
          "note": "No charge estimated as zero merely because a call failed; invoice and dashboard reconciliation required."}
(ROOT / "PRODUCTION/SPEND_LEDGER.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Résumé actualisé : 12 films, {len(ledger)} appels consignés, {report['known_partial_worker_estimate_usd']} USD d'estimation worker partielle.")
