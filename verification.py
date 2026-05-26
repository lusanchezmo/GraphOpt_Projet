def verification_independante_totale(employees, jours, postes, params, mmax, duree_poste, incom, ujp, days_off, x):
    print(f"\n{'='*80}")
    print(f"AUDIT DE SOLUTION (Basé uniquement sur les données d'entrée)")
    print(f"{'='*80}")

    # Nombre de violations détectées
    violations = 0
    # Horizon de planification (nombre de jours)
    horizon = len(jours)

    # 1. Extraction des données de la solution
    # On crée un dictionnaire simple : planning[employe][jour] = poste ou None
    sol = {e: {j: None for j in jours} for e in employees}
    for e in employees:
        for j in jours:
            for p in postes:
                if x[e, j, p].X > 0.5:
                    sol[e][j] = p

    # 2. VÉRIFICATION PAR EMPLOYÉ
    for e in employees:
        t_min, t_max, c_max, c_min, r_min, we_max = params[e]
        
        # A. Vérification C1 & C3 (Type de poste et Quotas)
        counts = {p: 0 for p in postes}
        for j in jours:
            p = sol[e][j]
            if p:
                counts[p] += 1
                # Vérification compétence / quota max_ep
                if counts[p] > mmax[e][p]:
                    print(f"[VIOLATION C3] {e} : Trop de postes {p} ({counts[p]} > {mmax[e][p]})")
                    violations += 1

        # B. Vérification C4 (Minutes totales)
        total_minutes = sum(duree_poste[sol[e][j]] for j in jours if sol[e][j])
        if total_minutes < t_min or total_minutes > t_max:
            print(f"[VIOLATION C4] {e} : Minutes {total_minutes} hors limites [{t_min}, {t_max}]")
            violations += 1

        # C. Vérification C2 (Incompatibilités / Successions interdites)
        for j in range(horizon - 1):
            p1 = sol[e][j]
            p2 = sol[e][j+1]
            if p1 and p2:
                if p1 in incom and p2 in incom[p1]:
                    print(f"[VIOLATION C2] {e} : Succession interdite {p1} -> {p2} (Jours {j}-{j+1})")
                    violations += 1

        # D. Vérification C5, C6, C7 (Séquences de travail et repos)
        # On crée une liste binaire (1=travail, 0=repos)
        planning_binaire = [1 if sol[e][j] else 0 for j in jours]
        
        # Analyse des blocs consécutifs
        import itertools
        groupes = [(key, len(list(group))) for key, group in itertools.groupby(planning_binaire)]
        
        for i, (est_travail, longueur) in enumerate(groupes):
            if est_travail == 1:
                # C5: Max Travail
                if longueur > c_max:
                    print(f"[VIOLATION C5] {e} : Travaille {longueur} jours de suite (Max {c_max})")
                    violations += 1
                # C6: Min Travail (On ne vérifie pas si c'est le dernier bloc de l'horizon)
                if longueur < c_min and i < len(groupes) - 1:
                    print(f"[VIOLATION C6] {e} : Travaille {longueur} jours de suite (Min {c_min})")
                    violations += 1
            else:
                # C7: Min Repos (On ne vérifie pas si c'est le dernier bloc)
                if longueur < r_min and i < len(groupes) - 1:
                    print(f"[VIOLATION C7] {e} : Repos de {longueur} jours de suite (Min {r_min})")
                    violations += 1

        # E. Vérification C8 (Week-ends travaillés)
        we_count = 0
        for w_idx in range(horizon // 7):
            samedi = sol[e][w_idx * 7 + 5]
            dimanche = sol[e][w_idx * 7 + 6]
            if samedi or dimanche:
                we_count += 1
        if we_count > we_max:
            print(f"[VIOLATION C8] {e} : {we_count} week-ends travaillés (Max {we_max})")
            violations += 1

        # F. Vérification C9 (Jours OFF imposés)
        for j_off in days_off.get(e, []):
            if sol[e][j_off]:
                print(f"[VIOLATION C9] {e} : Travaille le jour {j_off} (Jour OFF imposé)")
                violations += 1

    # 3. VÉRIFICATION GLOBALE (Couverture des postes C10)
    # On ne vérifie pas y_plus/y_minus ici car ce sont des variables du modèle.
    # On vérifie si assigned == required.
    for j in jours:
        for p in postes:
            nb_assigne = sum(1 for e in employees if sol[e][j] == p)
            requis = ujp.get((j, p), 0)
            if nb_assigne != requis:
                # C'est une contrainte "souple" dans ton code (car y_plus/y_minus existent),
                # mais je l'affiche pour information.
                diff = nb_assigne - requis
                print(f"[INFO COUVERTURE] Jour {j}, Poste {p}: {nb_assigne} au lieu de {requis} (Ecart: {diff})")

    # Résultat final
    if violations == 0:
        print(f"\nLa solution est 100% conforme les contraintes dures.")
    else:
        print(f"\nATTENTION : {violations} violations détectées.")
    print(f"{'='*80}\n")

