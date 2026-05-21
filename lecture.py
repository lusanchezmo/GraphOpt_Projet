def transformer_donnees_fichier(chemin_fichier):
    
    def parser_section(contenu, debut, fin=None):
        """Extrait les lignes propres entre deux marqueurs de section"""
        try:
            idx_debut = contenu.index(debut)
        except ValueError:
            return []
        
        idx_fin = len(contenu)
        for i in range(idx_debut + 1, len(contenu)):
            if fin and contenu[i] == fin:
                idx_fin = i
                break
            elif not fin and contenu[i].startswith('SECTION_'):
                idx_fin = i
                break
        
        lignes = []
        for ligne in contenu[idx_debut + 1:idx_fin]:
            ligne_propre = ligne.strip()
            if ligne_propre and not ligne_propre.startswith('#'):
                if ',' in ligne_propre:
                    parties = [p.strip() for p in ligne_propre.split(',')]
                    lignes.append(parties)
                else:
                    lignes.append(ligne_propre)
        return lignes

    # 1. lire le fichier .txt
    if isinstance(chemin_fichier, str):
        with open(chemin_fichier, 'r', encoding='utf-8') as f:
            lignes = f.readlines()
    else:
        lignes = chemin_fichier
        
    contenu = [l.rstrip('\n').strip() for l in lignes]

    # SECTION_HORIZON
    donnees_horizon = parser_section(contenu, 'SECTION_HORIZON', 'SECTION_SHIFTS')
    horizon = int(donnees_horizon[0][0]) if (donnees_horizon and isinstance(donnees_horizon[0], list)) else (int(donnees_horizon[0]) if donnees_horizon else 0)

    # SECTION_SHIFTS
    donnees_shifts = parser_section(contenu, 'SECTION_SHIFTS', 'SECTION_STAFF')
    postes = [s[0] for s in donnees_shifts]
    duree_poste = {s[0]: int(s[1]) for s in donnees_shifts}
    
    incom = {}
    for s in donnees_shifts:
        if len(s) >= 3 and s[2]:
            incom[s[0]] = s[2].split('|') if '|' in s[2] else [s[2]]
        else:
            incom[s[0]] = []

    # SECTION_STAFF
    donnees_staff = parser_section(contenu, 'SECTION_STAFF', 'SECTION_DAYS_OFF')
    employees = [p[0] for p in donnees_staff]
    
    params = {}
    mmax = {}
    for p in donnees_staff:
        emp_id = p[0]
        
        # Parsear mmax (MaxShifts format: E=14|L=14)
        chaine_mmax = p[1]
        dict_mmax = {}
        for element in chaine_mmax.split('|'):
            if '=' in element:
                poste_id, val = element.split('=')
                dict_mmax[poste_id] = int(val)
        mmax[emp_id] = dict_mmax
        
        # Parsear params: [MinTotalMinutes, MaxTotalMinutes, MaxConsecutiveShifts, 
        #                  MinConsecutiveShifts, MinConsecutiveDaysOff, MaxWeekends]
        params[emp_id] = [
            int(p[3]),  # MinTotalMinutes      !!! ATTENTION : inversement avec MaxTotalMinutes
            int(p[2]),  # MaxTotalMinutes
            int(p[4]),  # MaxConsecutiveShifts
            int(p[5]),  # MinConsecutiveShifts
            int(p[6]),  # MinConsecutiveDaysOff
            int(p[7])   # MaxWeekends
        ]

    # SECTION_DAYS_OFF
    donnees_days_off = parser_section(contenu, 'SECTION_DAYS_OFF', 'SECTION_SHIFT_ON_REQUESTS')
    days_off = {}
    for d in donnees_days_off:
        emp_id = d[0]
        days_off[emp_id] = [int(x) for x in d[1:]]

    # SECTION_SHIFT_ON_REQUESTS
    donnees_on = parser_section(contenu, 'SECTION_SHIFT_ON_REQUESTS', 'SECTION_SHIFT_OFF_REQUESTS')
    shift_on_requests = []
    for d in donnees_on:
        shift_on_requests.append((d[0], int(d[1]), d[2], int(d[3])))

    # SECTION_SHIFT_OFF_REQUESTS
    donnees_off = parser_section(contenu, 'SECTION_SHIFT_OFF_REQUESTS', 'SECTION_COVER')
    shift_off_requests = []
    for d in donnees_off:
        shift_off_requests.append((d[0], int(d[1]), d[2], int(d[3])))

    # SECTION_COVER
    donnees_cover = parser_section(contenu, 'SECTION_COVER', None)
    ujp = {}
    for c in donnees_cover:
        j = int(c[0])
        p = c[1]
        req = int(c[2])
        
        ujp[(j, p)] = req

    return {
        'horizon': horizon,
        'employees': employees,
        'postes': postes,
        'duree_poste': duree_poste,
        'incom': incom,
        'params': params,
        'mmax': mmax,
        'ujp': ujp,
        'days_off': days_off,
        'shift_on_requests': shift_on_requests,
        'shift_off_requests': shift_off_requests
    }