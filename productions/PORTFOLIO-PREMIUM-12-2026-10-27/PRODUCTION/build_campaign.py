import concurrent.futures
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

from prepare_sources import download

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "PRODUCTION/campaign.json").read_text(encoding="utf-8"))
SIZE = (768, 1344)
REFERENCES = {
    "dior-dark": ("Dior, descriptions officielles Sauvage", "https://www.dior.com/couture/var/dior/storage/original/application/037cdc4dda4d7a6ee0b3068d8b2d56a2.pdf", "Progression d'ombre vers le produit et lisibilité du flacon. Référence textuelle consultée ; aucun plan, logo, musique ou talent repris."),
    "jadore": ("LVMH, film J'adore de Steven Klein", "https://www.lvmh.com/en/news-lvmh/rihanna-x-jadore-a-total-star-and-a-legendary-fragrance", "Lumière dorée et contraste du verre. Transposition en nature morte originale, sans Versailles, égérie ni collier. Page et images de campagne consultées, pas une analyse image par image du film."),
    "aesop-sensory": ("Bart Hess, Aesop Epistēmē", "https://www.barthess.com/aesop", "Attention aux sensations et aux micro-matières. Aucun effet de peau ou extrait protégé repris ; description et images du réalisateur consultées."),
    "aesop-magnify": ("Jessica N. Galvan, Aesop Skin Care+", "https://www.jessicangalvan.com/aesop-skincare-campaign", "Changement d'échelle et grossissement comme idée visuelle. Aucun bénéfice cosmétique de la campagne source transféré au produit générique."),
    "aesop-ritual": ("Jack Ball-Smith, The Skin at Ease", "https://jackballsmith.com/III-The-Skin-at-Ease", "Gestes calmes, lumière et cadrage rapproché. Présentation de campagne étudiée ; aucun témoignage ou claim de marque réutilisé."),
    "vitra": ("Vitra, Home Stories", "https://www.vitra.com/en-us/inspirations/home-stories", "Hiérarchie pièce / objet / détail et rôle de la lumière naturelle. Photographies et composition de page consultées, aucune propriété particulière du mobilier revendiquée."),
    "cos": ("COS, Spring Summer 2026", "https://www.cos.com/en-us/campaign/spring-summer-2026-womenswear", "Cadrage éditorial, silhouette retenue et matière. Page officielle et images de campagne consultées ; aucune tenue de marque ni prise de vue copiée."),
    "apple-performance": ("The One Club, AirPods Quiet the Noise", "https://www.oneclub.org/awards/theoneshow/-award/52183/airpods-quiet-the-noise/", "Clarté d'une idée publicitaire en un bénéfice visuel. Fiche de campagne consultée ; aucun effet de lévitation ni claim audio repris."),
    "apple-transformation": ("The Creatives Room, Apple Snap", "https://thecreativesroom.com/ref/snap", "Raccord de cadrage entre deux ambiances ; principe réinterprété sur un seul luminaire, sans chorégraphie ni décors de la campagne source."),
    "dyson": ("Moktan Productions, Dyson Hair Science", "https://www.moktanproductions.com/corporate-video-production/dyson-hair-science", "Lisibilité du produit et montage court à partir de détails. Stills et fiche de production consultés ; pas de reproduction du spot ni de ses revendications.")
}
MUSIC = {
    "reverie": "https://www.scottbuckley.com.au/library/wp-content/uploads/2020/03/sb_reverie.mp3",
    "catalyst": "https://www.scottbuckley.com.au/library/wp-content/uploads/2020/06/sb_catalyst.mp3"
}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def font(size, serif=False):
    candidates = (["C:/Windows/Fonts/georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"] if serif else
                  ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    return ImageFont.truetype(next(p for p in candidates if Path(p).is_file()), size)


def fit_text(draw, text, max_width, size, serif=False):
    while draw.textbbox((0, 0), text, font=font(size, serif))[2] > max_width:
        size -= 1
    return font(size, serif)


def grade(image, name):
    if name == "charcoal":
        image = ImageEnhance.Color(image).enhance(0)
        image = ImageEnhance.Brightness(image).enhance(0.38)
    elif name == "cool":
        image = ImageEnhance.Color(image).enhance(0.55)
        image = ImageEnhance.Brightness(image).enhance(0.88)
    elif name in ("amber", "warm-neutral", "cream"):
        image = ImageEnhance.Color(image).enhance(0.90)
    elif name == "punch":
        image = ImageEnhance.Color(image).enhance(1.04)
    return image


def main():
    candidates = {r["id"]: r for r in json.loads((ROOT / "PRODUCTION/asset_candidates.json").read_text(encoding="utf-8"))}
    wanted = sorted({shot["source"] for film in DATA["films"] for shot in film["shots"]})
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        records = list(pool.map(download, [candidates[i] for i in wanted]))
    sources = {r["id"]: r for r in records}
    credits_path = ROOT / "PRODUCTION/pexels-credits.json"
    credits = {r["id"]: r.get("authors", []) for r in json.loads(credits_path.read_text(encoding="utf-8"))} if credits_path.exists() else {}
    music_folder = ROOT / "PRODUCTION/MUSIC"
    music_folder.mkdir(exist_ok=True)
    for name, url in MUSIC.items():
        target = music_folder / f"{name}.mp3"
        if not target.exists():
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60) as response:
                target.write_bytes(response.read(30_000_001))
    overview = Image.new("RGB", (6 * 256, 2 * 480), "#191b1d")
    summary = ["# Portfolio premium : douze candidats", "", "Aucun film n'est validé pour publication par défaut. Sources : Pexels uniquement. Aucun MP4 de simulation.", "", "| Film | Catégorie | Préparation | Génération | MP4 réel | Dépense Modal | Qualité | Défauts / réserve | Recommandation |", "|---|---|---|---|---|---|---|---|---|"]
    for index, film in enumerate(DATA["films"]):
        folder = ROOT / film["id"]
        for name in ("ASSETS", "PROMPTS", "RENDERS", "EXPORTS", "REPORTS"):
            (folder / name).mkdir(parents=True, exist_ok=True)
        # Helios is referenced creatively; only the already verified two downloadable tracks are used at execution.
        execution_music = film["music"] if film["music"] in MUSIC else "reverie"
        shutil.copy2(music_folder / f"{execution_music}.mp3", folder / "ASSETS" / "music.mp3")
        plan = {"campaign": DATA["campaign_id"], "film_id": film["id"], "title": film["title"],
                "workspace": "lucj76861", "environment": "main", "mode": "existing_deployment_only",
                "target_duration_s": 22.5 if film.get("hold") else 17.5, "card_duration_s": 2.5,
                "output": {"master": "EXPORTS/" + film["id"].upper() + "-MASTER-1080x1920.mp4", "web": "EXPORTS/" + film["id"].upper() + "-WEB-720x1280.mp4", "fps": 24, "aspect": "9:16", "codec": "H.264/AAC", "pixel_format": "yuv420p", "audio_hz": 48000, "native_render_size": [768, 1344], "upscaled_master": True},
                "generation_status": "suspended" if film.get("hold") else "prepared_not_started",
                "preparation_status": "creative_complete_casting_and_voice_pending" if film.get("hold") else "prepared_sources_verified",
                "executable": not bool(film.get("hold")), "hold_reason": film.get("hold"),
                "pilot": film["id"] in DATA["pilots"], "human_review_required": True,
                "quality_grade": None, "publish": False, "max_concurrent_gpu": 1,
                "attempts_per_shot": 1, "automatic_retry": False,
                "client_deadline_per_shot_s": 600, "worker_timeout_note": "déploiement existant, timeout distant non changé ; le délai client ne plafonne pas la facture",
                "cancellation": {"local": "CTRL+C : annulation de l'appel actif avec terminate_containers=True", "github": "gh run cancel RUN_ID --repo saillardsimon71-del/UGCv2 puis python PRODUCTION/run_campaign.py cancel --film FILM", "remote": "modal.FunctionCall.from_id(call_id).cancel(terminate_containers=True)", "shared_app_stop": False},
                "workflow": ".github/workflows/portfolio-premium-12.yml", "github_run_id": None,
                "artifact_retention_days_requested": 90, "music": {"creative_reference": film["music"], "execution_track": execution_music, "start_s": min(film["music_start"], 135), "path": "ASSETS/music.mp3", "author": "Scott Buckley", "license": "CC BY 4.0", "page": f"https://www.scottbuckley.com.au/library/{execution_music}/", "attribution_required": True},
                "audio": {"source_generated_audio_used": False, "voice_script": film.get("script"), "voice_status": "not_licensed_or_generated" if film.get("hold") else "not_required", "sound_design": film["sound"], "target_lufs": -16, "max_true_peak_dbtp": -1.5},
                "edit_structure": film.get("edit_structure", []), "shots": []}
        board = [f"# {film['title']} : storyboard de production", "", f"Durée cible : {plan['target_duration_s']} s, vertical 9:16. Trois prises IA, puis carton CPU de 2,5 s. Recadrages issus de photographies réelles, aucun photomontage génératif.", ""]
        source_records = []
        sheet = Image.new("RGB", (4 * 384, 750), "#181818")
        sd = ImageDraw.Draw(sheet)
        for n, shot in enumerate(film["shots"]):
            source = sources[shot["source"]]
            original = ROOT / source["path"]
            original_target = folder / "ASSETS" / f"pexels-{shot['source']}.jpg"
            if not original_target.exists():
                shutil.copy2(original, original_target)
            with Image.open(original) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
                crop = tuple(round(v * d) for v, d in zip(shot["crop"], [im.width, im.height, im.width, im.height]))
                cropped = im.crop(crop)
                frame = grade(ImageOps.fit(cropped, SIZE, method=Image.Resampling.LANCZOS), shot["grade"])
            image_path = folder / "ASSETS" / f"shot-{shot['id']}-firstframe.png"
            frame.save(image_path, optimize=True)
            engine = shot.get("engine", "ltx")
            duration = [7, 6, 7][n] if film.get("hold") else 5
            payload = {"prompt": shot["prompt"], "duration_s": duration, "aspect_ratio": "9:16", "seed": 2026102700 + index * 10 + n,
                       "audio_mode": "silent", "image_strength": 0.9, "trace_id": f"sqv27-{index+1:02d}-{shot['id']}"}
            (folder / "PROMPTS" / f"shot-{shot['id']}.txt").write_text(shot["prompt"] + "\n", encoding="utf-8")
            write_json(folder / "PROMPTS" / f"shot-{shot['id']}-payload.json", payload)
            source_record = {**source, "author_evidence": credits.get(shot["source"], []), "crop_fraction": shot["crop"], "crop_pixels": crop,
                             "prepared_dimensions": SIZE, "firstframe": str(image_path.relative_to(folder)).replace("\\", "/"),
                             "firstframe_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(), "processing": "EXIF orientation, deterministic crop, Lanczos fit, simple grade; no generative image editing", "grade": shot["grade"], "license": "https://www.pexels.com/license/"}
            source_records.append(source_record)
            shot_plan = {"shot_id": shot["id"], "duration_requested_s": duration, "timeline_start_s": sum([7,6,7][:n]) if film.get("hold") else n*5,
                         "timeline_duration_s": duration, "native_frames": 1 + ((int(duration * 24) - 1 + 7)//8)*8 if engine == "ltx" else None,
                         "engine": "LTX-2.5 Distilled, ComfyUI 2 passes" if engine == "ltx" else "LongCat Video Avatar 1.5, INT8, 480p",
                         "app": "pvs-ltx" if engine == "ltx" else "pvs-longcat-avatar", "function": "render_clip" if engine == "ltx" else "render_avatar",
                         "gpu": "L40S" if engine == "ltx" else "A100-80GB", "source": source_record,
                         "framing": shot["framing"], "camera": shot["camera"], "lighting": film["light"], "action": shot["action"],
                         "preserve": film["preserve"], "prompt": shot["prompt"], "payload_file": f"PROMPTS/shot-{shot['id']}-payload.json",
                         "sound": shot["sound"], "transition": shot["cut"], "render_path": f"RENDERS/shot-{shot['id']}.mp4", "status": "suspended" if film.get("hold") else "ready",
                         "validation": ["Produit, acteur et décor identiques à la photographie d'entrée", "Pas de géométrie variable, texte parasite, scintillement ou objet ajouté", "Mouvement conforme à l'action et raccord lisible", "Vrai MP4 décodable, durée et conditionnement image documentés"]}
            plan["shots"].append(shot_plan)
            time_range = f"{shot_plan['timeline_start_s']:.1f}-{shot_plan['timeline_start_s']+duration:.1f} s"
            board.extend([f"## Plan {shot['id']} : {time_range}", "", f"- Description : {shot['action']}", f"- Cadrage : {shot['framing']}", f"- Caméra : {shot['camera']}", f"- Lumière : {film['light']}", f"- À préserver : {film['preserve']}", f"- Image initiale : [PNG réel](ASSETS/shot-{shot['id']}-firstframe.png), Pexels {shot['source']}.", f"- Moteur : {shot_plan['engine']} ; {shot_plan['app']}/{shot_plan['function']} ; {shot_plan['gpu']}.", f"- Son : {shot['sound']}", f"- Raccord : {shot['cut']}", "- Validation : fidélité à la référence, absence de texte généré, mouvement stable, raccord sans saut ; contrôle sur le vrai MP4.", "", "Prompt exact :", "", "```text", shot["prompt"], "```", ""])
            tile = ImageOps.contain(frame, (384, 672))
            sheet.paste(tile, (n * 384, 0))
            sd.text((n * 384 + 12, 688), f"PLAN {shot['id']} / {duration} s", font=font(20), fill="white")
        card = Image.new("RGB", (1080, 1920), film["card_bg"])
        cd = ImageDraw.Draw(card)
        cd.text((540, 810), film["signature"], font=fit_text(cd, film["signature"], 900, 110, film["serif"]), anchor="mm", fill=film["card_ink"])
        cd.line((390, 915, 690, 915), fill=film["card_ink"], width=2)
        cd.text((540, 1010), film["tagline"], font=fit_text(cd, film["tagline"], 900, 39), anchor="mm", fill=film["card_ink"])
        cd.text((540, 1660), "CONCEPT INDÉPENDANT", font=font(24), anchor="mm", fill=film["card_ink"])
        cd.text((540, 1710), "SITEQUIVEND.FR", font=font(25), anchor="mm", fill=film["card_ink"])
        if film.get("hold") or film.get("human_review"):
            cd.text((540, 1760), "MODÈLE DE STOCK / MISE EN SCÈNE", font=font(21), anchor="mm", fill=film["card_ink"])
        card.save(folder / "ASSETS/endcard.png")
        sheet.paste(card.resize((378, 672)), (3 * 384, 0))
        sd.text((3 * 384 + 12, 688), "CARTON / 2,5 s / CPU", font=font(20), fill="white")
        sheet.save(folder / "ASSETS/STORYBOARD.jpg", quality=92)
        overview.paste(ImageOps.fit(frame, (256, 448)), ((index % 6) * 256, (index // 6) * 480))
        od = ImageDraw.Draw(overview)
        od.text(((index % 6)*256+8, (index // 6)*480+454), f"{index+1:02d} {film['title'][:22]}", font=font(13), fill="white")
        board.extend([f"## Plan 04 : {plan['target_duration_s']-2.5:.1f}-{plan['target_duration_s']:.1f} s", "", f"Carton fixe CPU : {film['signature']} / {film['tagline']}. Image : ASSETS/endcard.png. Aucun moteur vidéo. Musique fondue sur 0,65 s. Validation : lisibilité, accents, absence de fausse collaboration et de résultat inventé.", ""])
        if film.get("hold"):
            board.extend(["## Suspension", "", film["hold"], "", "Les images présentes sont des références de casting, pas une personne fictive créée ni une autorisation de lui faire prononcer un texte.", "", "Script exact envisagé :", "", film["script"], "", "Sous-titres : transcription mot pour mot après production d'une voix autorisée ; aucune vitesse ou synchronisation déclarée avant écoute."])
        (folder / "STORYBOARD.md").write_text("\n".join(board).rstrip() + "\n", encoding="utf-8")
        (folder / "BRIEF.md").write_text(f"# {film['title']}\n\n{film['idea']}\n\nObjectif commercial : {film['commercial_goal']}\n\nPublic : marques e-commerce du secteur et agences Social Ads / production. Film de concept indépendant, sans commande ni collaboration de marque. Signature de création fictive : {film['signature']}, sans prétendre qu'un produit est commercialisé sous ce nom.\n\nProduit : {film['product']}\n\nDifférence dans l'univers : {film['difference']}\n\nFormat : vertical 9:16, {plan['target_duration_s']} s. Trois prises courtes et un carton. Musique et sound design. Aucune allégation mesurable ni avis client. Images sources Pexels, aucune image fixe IA.\n\n{film.get('hold','Validation des pilotes avant toute série ; publication uniquement après classement A et décision humaine.')}\n", encoding="utf-8")
        refs = "\n".join(f"- [{REFERENCES[k][0]}]({REFERENCES[k][1]}) : {REFERENCES[k][2]}" for k in film["references"])
        (folder / "CREATIVE_DIRECTION.md").write_text(f"# Direction créative\n\n{film['idea']}\n\nPalette : {', '.join(film['palette'])}.\n\nLumière : {film['light']}\n\nCaméra : trois échelles optiques, déplacements très courts ; pas de mouvement spectaculaire nécessaire. Étalonnage simple sans modifier le produit. Texte composé après rendu avec une police système librement utilisable par le système de production.\n\nContinuité : {film['preserve']}\n\nMontage : trois séquences de 5 s pour les films produit ; 2,5 s de signature. Le film performance recoupe ces séquences en gardant une lecture produit et une durée totale identique. Aucun arrêt sur image ne remplace une génération échouée.\n\nSon : {film['sound']} Piste exécutée : {execution_music.title()}, Scott Buckley, CC BY 4.0, crédit à conserver. Référence musicale créative : {film['music']}, pas une promesse de piste téléchargée.\n\n## Références étudiées\n\n{refs}\n\nCes sources sont des recherches de direction, pas des médias à insérer. Les analyses portent sur les pages, descriptions et images disponibles ; aucun visionnage intégral des publicités n'est prétendu. Les images effectivement animées sont listées dans ASSETS/SOURCES.json.\n", encoding="utf-8")
        write_json(folder / "ASSETS/SOURCES.json", source_records)
        write_json(folder / "PRODUCTION_PLAN.json", plan)
        cost = {"currency": "USD", "actual_billed_usd": None, "campaign_authorization_ceiling": 20, "effective_additional_ceiling_at_start": 19.8,
                "pilot_envelope_usd": 5, "film_expected_scenario_usd": None, "status": "scenario_not_invoice",
                "rate_source": "https://modal.com/pricing", "checked_date": "2026-10-27",
                "ltx_assumption": {"gpu_L40S_per_s": .000542, "cpu_8_cores_per_s": .0001048, "memory_64_GiB_per_s": .00014208, "combined_reserved_per_s": .00078888},
                "three_calls_at_120_to_300_seconds_usd": [.2840, .7100],
                "three_client_deadlines_600s_plus_180s_margin_scenario_usd": 1.5620,
                "not_a_cap": True, "unresolved": ["Temps de chargement et cold start facturés, non bornés par le délai client", "CPU et RAM peuvent être facturés au-delà de la réservation", "Facture inclut échecs, arrêt, stockage et éventuel egress", "Aucun build ni téléchargement de modèle autorisé par ce job"],
                "protection": "Limite mensuelle workspace abaissée à 20 USD, usage initial 0,20 USD ; un seul appel GPU, un essai, arrêt sur échec. Pas de série automatique.",
                "hold": film.get("hold"), "actual_source": "Dashboard Modal à relever avant et après chaque film. Les secondes retournées par le worker donnent uniquement une estimation partielle."}
        write_json(folder / "COST_ESTIMATE.json", cost)
        (folder / "QUALITY_CHECKLIST.md").write_text("# Contrôle de chaque prise et du montage\n\n- [x] Photographies Pexels réelles, originaux décodés, images initiales et empreintes conservées.\n- [ ] Inspection de chaque PNG initial à sa taille de production.\n- [ ] Vrai rendu distant, MP4 réel non vide, reçu d'appel et source envoyée conservés.\n- [ ] Conditionnement image attesté par métadonnées et graphe embarqué si disponible, puis comparaison du premier photogramme.\n- [ ] Décodage intégral sans erreur ; durée, dimensions, cadence, H.264 yuv420p et AAC 48 kHz corrects.\n- [ ] Produit et packaging fidèles, étiquette sans texte parasite, formes et matières stables.\n- [ ] Mains, visage, dents, lèvres et reflets stables si présents ; sinon non applicable motivé dans le rapport.\n- [ ] Aucun mouvement impossible, flou gênant, scintillement ou raccord incohérent.\n- [ ] Vrais fichiers inspectés plan par plan puis montage ; un contrôle automatique ne classe pas A.\n- [ ] Musique, sound design, crêtes et intelligibilité contrôlés ; écoute critique humaine séparée des mesures.\n- [ ] Texte et sous-titres exacts ; pas de faux client, faux résultat ou fausse collaboration.\n- [ ] Crédit musical et conditions Pexels joints à l'export.\n- [ ] Facturation relevée avec périmètre et incertitude ; aucun job GPU restant sans suivi.\n- [ ] MP4, miniature, sources et rapports récupérables ; expiration d'artefact vérifiée.\n\nClasse A : produit fidèle, qualité créative convaincante et validation artistique sur le vrai MP4. Classe B : prometteur, correction ou validation humaine encore nécessaire. Classe C : rejet. B et C ne sont jamais publiés automatiquement.\n", encoding="utf-8")
        credit_lines = [f"{r['id']} - {r['page']}" + (" - " + r['author_evidence'][0]['name'] if r['author_evidence'] else "") for r in source_records]
        (folder / "ASSETS/CREDITS.txt").write_text("Concept indépendant SiteQuiVend. Photographies Pexels animées par IA ; aucune image fixe générée.\n" + "\n".join(dict.fromkeys(credit_lines)) + f"\nPexels : https://www.pexels.com/license/\nMusic: '{execution_music.title()}' by Scott Buckley - released under CC BY 4.0. www.scottbuckley.com.au\nhttps://www.scottbuckley.com.au/library/{execution_music}/\nMusique recoupée, mixée et normalisée. Crédit à faire figurer dans toute publication ; sur YouTube dans la description.\nSound design original déterministe : SiteQuiVend, 2026.\nAucune personne représentée n'est présentée comme un client ou partenaire de SiteQuiVend.\n", encoding="utf-8")
        status_path = folder / "REPORTS/STATUS.json"
        if not status_path.exists():
            write_json(status_path, {"film": film["id"], "status": plan["generation_status"], "quality": None, "actual_billed_usd": None, "final_mp4": None, "defects": [], "review": "not_rendered", "hold": film.get("hold")})
        summary.append(f"| {index+1:02d} {film['title']} | {film['category']} | {'Concept + références ; casting/voix à valider' if film.get('hold') else 'Prêt, sources réelles préparées'} | {'Suspendu' if film.get('hold') else 'Non lancé'} | Aucun | 0 lancé ; facture n/a | Non évalué | {film.get('hold','Qualité à contrôler sur MP4 réel')} | {'Conserver les crédits' if film.get('hold') else 'Pilote contrôlé' if plan['pilot'] else 'Attendre les pilotes'} |")
    overview.save(ROOT / "STORYBOARDS-12.jpg", quality=92)
    (ROOT / "PORTFOLIO_SUMMARY.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    write_json(ROOT / "PRODUCTION/selected_sources.json", records)
    print("Préparés : 12 briefs, directions, storyboards, plans, checklists et coûts ; 36 PNG Pexels ; 12 cartons CPU. Aucun GPU.")


if __name__ == "__main__":
    main()
