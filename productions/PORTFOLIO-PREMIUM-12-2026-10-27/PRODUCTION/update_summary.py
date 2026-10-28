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
    mp4 = f"[MP4]({folder.name}/EXPORTS/{web.name})" if has_export else "Aucun"
    generation = "MP4 exporté" if has_export else "Suspendu" if not plan["executable"] else f"{complete}/3 prises ; en cours" if receipts else "Non lancé"
    prep = "Concept complet ; casting/voix non validés" if not plan["executable"] else "Sources, prompts et storyboard prêts"
    quality = status.get("quality") or "Non évalué"
    defects = "; ".join(status.get("defects", [])) or ("Casting réel et avatar non validés" if not plan["executable"] else "Revue du vrai MP4 en attente" if has_export else "Pas de jugement sans vidéo")
    cost = f"{partial:.4f} USD worker partiel" if receipts else "0 appel GPU"
    if failed:
        cost += f" ; {failed} démarrage interrompu non ventilé"
    recommendation = status.get("recommendation") or ("Conserver les crédits" if not plan["executable"] else "Prêt pour un prochain lot contrôlé")
    cells = [plan["title"], concept["category"], prep, generation, mp4, cost, quality, defects, recommendation]
    rows.append("| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |")
rows += ["", "## Budget et preuve", "", "Compte : lucj76861. Solde initial observé : 29,80 USD ; usage initial du cycle : 0,20 USD. Limite mensuelle abaissée à 20 USD, réserve visée : 10 USD. Budget additionnel effectif initial : 19,80 USD ; enveloppe pilotes : 5 USD. Voir PRODUCTION/BUDGET.json et les relevés de consommation. Les compteurs du dashboard peuvent se mettre à jour à des rythmes différents : aucune facture définitive n'est déclarée.",
         "", "## Récupération", "", "Préparations complètes : [artefact GitHub](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40569251898), expiration vérifiée au 25 janvier 2027. Les nouveaux exports sont également conservés localement. Les [vrais pilotes archivés](https://github.com/saillardsimon71-del/UGCv2/actions/runs/40576929268) expirent le 25 janvier 2027 à 20:18 UTC ; leurs quatre exports ont été réellement téléchargés et leurs SHA256 vérifiés. Voir PRODUCTION/GITHUB_PILOT_DELIVERY.json.",
         "", "Relevé du 28 octobre : solde 28,55 USD, consommation de campagne estimée à 1,25 USD, dont 0,65 USD pour le lot GOLDEN REVEAL + ACCESSORY ICON. Compteurs asynchrones, facture définitive indisponible. Les six prises de ce lot ont abouti sans relance ; les deux V2 ont uniquement été montées sur CPU.",
         "", "Les pilotes 03 et 05 ont reçu une validation humaine pour poursuivre la production. Les films 02 et 12 ont également reçu une validation humaine pour poursuivre avec le lot 07 + 08. La sélection portfolio reste ultérieure.",
         "", "La qualité visuelle est contrôlée sur des photogrammes extraits des vrais MP4, par prise et montage. Une validation humaine en lecture continue et une écoute critique restent nécessaires avant sélection portfolio. Les contrôles techniques ne constituent pas une validation esthétique."]
(ROOT / "PORTFOLIO_SUMMARY.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
report = {"updated_at": datetime.now(timezone.utc).isoformat(), "calls": ledger,
          "known_partial_worker_estimate_usd": round(sum(r["partial_worker_estimate_usd"] or 0 for r in ledger), 4),
          "actual_campaign_billed_usd": None, "failed_starts_included_in_call_count": True,
          "note": "No charge estimated as zero merely because a call failed; invoice and dashboard reconciliation required."}
(ROOT / "PRODUCTION/SPEND_LEDGER.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Résumé actualisé : 12 films, {len(ledger)} appels consignés, {report['known_partial_worker_estimate_usd']} USD d'estimation worker partielle.")
