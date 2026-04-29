import gurobipy as grb
from gurobipy import GRB

# Données 
horizon = 14
jours = list(range(horizon))
weekends = list(range(horizon // 7))
employees = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
postes = ["E", "L"]
duree_poste = {"E": 480, "L": 480}
incom = {'E': [], 'L': ['E']}

params = {
    'A': [3360, 4320, 5, 2, 2, 1], 'B': [3360, 4320, 5, 2, 2, 1],
    'C': [3360, 4320, 5, 2, 2, 1], 'D': [3360, 4320, 5, 2, 2, 1],
    'E': [3360, 4320, 5, 2, 2, 1], 'F': [3360, 4320, 5, 2, 2, 1],
    'G': [3360, 4320, 5, 2, 2, 1], 'H': [3360, 4320, 5, 2, 2, 1],
    'I': [3360, 4320, 5, 2, 2, 1], 'J': [3360, 4320, 5, 2, 2, 1],
    'K': [1200, 2160, 5, 1, 1, 1], 'L': [1200, 2160, 5, 1, 1, 1],
    'M': [1200, 2160, 5, 1, 1, 1], 'N': [1200, 2160, 5, 1, 1, 1]
}
mmax = {
    'A': {'E': 14, 'L': 14}, 'B': {'E': 14, 'L': 14}, 'C': {'E': 14, 'L': 14},
    'D': {'E': 14, 'L': 0},  'E': {'E': 0,  'L': 14}, 'F': {'E': 14, 'L': 14},
    'G': {'E': 14, 'L': 14}, 'H': {'E': 14, 'L': 14}, 'I': {'E': 14, 'L': 14},
    'J': {'E': 14, 'L': 14}, 'K': {'E': 0,  'L': 14}, 'L': {'E': 0,  'L': 14},
    'M': {'E': 14, 'L': 14}, 'N': {'E': 14, 'L': 14}
}
ujp = {
    (0,'E'):4, (0,'L'):4, (1,'E'):4, (1,'L'):3, (2,'E'):3, (2,'L'):6,
    (3,'E'):5, (3,'L'):4, (4,'E'):3, (4,'L'):4, (5,'E'):5, (5,'L'):5,
    (6,'E'):5, (6,'L'):5, (7,'E'):3, (7,'L'):2, (8,'E'):4, (8,'L'):4,
    (9,'E'):4, (9,'L'):4, (10,'E'):4, (10,'L'):3, (11,'E'):2, (11,'L'):3,
    (12,'E'):4, (12,'L'):3, (13,'E'):3, (13,'L'):5
}

days_off = {'A': [3], 'B': [1],'C': [2], 'D': [12], 'E': [1], 'F': [13], 'G': [9], 'H': [3], 'I': [0], 'J': [8], 'K': [5], 'L': [2], 'M': [8], 'N': [6]}

# Poids pour le manque et l'excédent de personnel
v_min = {(j, p): 100 for j in jours for p in postes}  # poids manque
v_max = {(j, p): 1 for j in jours for p in postes}    # poids excédent

# Demandes de postes (shift_on_requests)
shift_on_requests = [
    ('A',5,'L',1), ('A',6,'L',1), ('A',7,'L',1), ('A',8,'L',1), ('A',9,'L',1),
    ('B',7,'E',1), ('B',8,'E',1), ('B',9,'E',1), ('B',10,'E',1),
    ('C',8,'E',1), ('C',9,'E',1), ('C',10,'E',1), ('C',11,'E',1),
    ('D',1,'E',1), ('D',2,'E',1), ('D',3,'E',1),
    ('E',3,'L',1), ('E',4,'L',1), ('E',5,'L',1), ('E',6,'L',1), ('E',7,'L',1),
    ('E',12,'L',2), ('E',13,'L',2),
    ('F',3,'L',3), ('F',4,'L',3), ('F',5,'L',3),
    ('I',2,'L',3), ('I',3,'L',3), ('I',12,'E',2),
    ('J',11,'L',3),
    ('K',7,'L',1), ('K',8,'L',1), ('K',9,'L',1),
    ('L',3,'L',1), ('L',4,'L',1), ('L',10,'L',3), ('L',11,'L',3), ('L',12,'L',3), ('L',13,'L',3),
    ('M',3,'L',1), ('M',4,'L',1), ('M',5,'L',1), ('M',6,'L',1), ('M',7,'L',1),
    ('N',0,'E',2), ('N',1,'E',2), ('N',2,'E',2), ('N',8,'E',3), ('N',9,'E',3), ('N',10,'E',3)
]

# Demandes de ne PAS travailler (shift_off_requests)
shift_off_requests = [
    ('G',3,'E',2), ('G',4,'E',2), ('G',5,'E',2), ('G',6,'E',2), ('G',7,'E',2),
    ('H',1,'L',2),
    ('J',1,'E',1), ('J',2,'E',1), ('J',3,'E',1), ('J',4,'E',1), ('J',5,'E',1),
    ('M',11,'L',1)
]

# Modèle
model = grb.Model("Probleme")

# Variables
x = model.addVars(employees, jours, postes, vtype=GRB.BINARY, name="x")
w = model.addVars(employees, jours, vtype=GRB.BINARY, name="work")
y_minus = model.addVars(jours, postes, vtype=GRB.INTEGER, name="y_minus")
y_plus = model.addVars(jours, postes, vtype=GRB.INTEGER, name="y_plus")
we_worked = model.addVars(employees, weekends, vtype=GRB.BINARY, name="we")


# constraints
#c1
model.addConstrs((x.sum(e, j, '*') == w[e, j] for e in employees for j in jours), "MaxOneShift")

#c2
for e in employees:
    for j in range(horizon - 1):
        for p in postes:
            for p_next in incom[p]:
                model.addConstr(x[e, j, p] + x[e, j+1, p_next] <= 1, f"Incompatibility_{e}_{j}_{p}_{p_next}")

#c3
for e in employees:
    for p in postes:
        model.addConstr(x.sum(e, '*', p) <= mmax[e][p], name=f"C3_{e}_{p}")

#c4
for e in employees:
    total_min = grb.quicksum(x[e, j, p] * duree_poste[p] for j in jours for p in postes)
    model.addConstr(total_min >= params[e][0], f"MinTime_{e}")
    model.addConstr(total_min <= params[e][1], f"MaxTime_{e}")

# c5 c6 et c7
for e in employees:
    min_c = params[e][3]
    r_min = params[e][4]
    max_c = params[e][2]

    # C5 : Max consécutifs
    for j in range(horizon - max_c):
        model.addConstr(grb.quicksum(w[e, k] for k in range(j, j + max_c + 1)) <= max_c)

    # C6 : Min consécutifs — cas j=0
    model.addConstr(
        grb.quicksum(w[e, k] for k in range(min(min_c, horizon))) >= min_c * w[e, 0]
    )

    # C6 : cas général : détection d'une transition repos→travail en jour j
    # Si w[e,j-1]=0 et w[e,j]=1, alors on doit travailler au moins min_c jours
    for j in range(1, horizon):
        if j + min_c <= horizon:
            # Si on commence à travailler en j (w[e,j] - w[e,j-1] = 1)
            # alors on doit travailler les min_c jours suivants
            model.addConstr(
                grb.quicksum(w[e, k] for k in range(j, j + min_c)) >= min_c * (w[e, j] - w[e, j-1]),
                f"MinConsec_{e}_{j}"
            )
        else:
            # Cas où on est proche de la fin de l'horizon
            # On assure qu'on travaille tous les jours restants si on commence
            jours_restants = horizon - j
            model.addConstr(
                grb.quicksum(w[e, k] for k in range(j, horizon)) >= jours_restants * (w[e, j] - w[e, j-1]),
                f"MinConsec_End_{e}_{j}"
            )

    # C7
    # Cas spécial : si l'employé ne travaille pas dès le jour 0 (commence en repos)
    if r_min <= horizon:
        model.addConstr(
            grb.quicksum(1 - w[e, k] for k in range(min(r_min, horizon))) >= r_min * (1 - w[e, 0]),
            f"MinRest_Start_{e}"
        )
    
    # C7
    # Cas général : détection d'une transition travail→repos en jour j
    # Si w[e,j-1]=1 et w[e,j]=0, alors on doit être en repos au moins r_min jours
    for j in range(1, horizon):
        if j + r_min <= horizon:
            # Si on arrête de travailler en j (w[e,j-1] - w[e,j] = 1)
            # alors on doit être en repos les r_min jours suivants
            model.addConstr(
                grb.quicksum(1 - w[e, k] for k in range(j, j + r_min)) >= r_min * (w[e, j-1] - w[e, j]),
                f"MinRest_{e}_{j}"
            )
        else:
            # Cas où on est proche de la fin de l'horizon
            jours_restants = horizon - j
            model.addConstr(
                grb.quicksum(1 - w[e, k] for k in range(j, horizon)) >= jours_restants * (w[e, j-1] - w[e, j]),
                f"MinRest_End_{e}_{j}"
            )

# c8
for e in employees:
    for we in range(horizon // 7):  
        samedi  = we * 7 + 5
        dimanche = we * 7 + 6
        model.addConstr(we_worked[e, we] >= w[e, samedi])
        model.addConstr(we_worked[e, we] >= w[e, dimanche])
    model.addConstr(
        grb.quicksum(we_worked[e, we] for we in range(horizon // 7)) <= params[e][5]
    )

# C9 : Jours de congé imposés
for e, days in days_off.items():
    for j in days:
        model.addConstr(w[e, j] == 0, f"DayOff_{e}_{j}")

# C10 : Contraintes de couverture
for j in jours:
    for p in postes:
        # Nombre d'employés affectés au poste p le jour j
        assigned = grb.quicksum(x[e, j, p] for e in employees)
        required = ujp.get((j, p), 0)
        
        # assigned + y_minus - y_plus = required
        model.addConstr(
            assigned + y_minus[j, p] - y_plus[j, p] == required,
            f"Coverage_{j}_{p}"
        )


# Fonction objectif
objective = grb.LinExpr()

# Terme 1 : Pénalités pour manque de personnel
objective += grb.quicksum(
    v_min[j, p] * y_minus[j, p] for j in jours for p in postes
)

# Terme 2 : Pénalités pour excédent de personnel
objective += grb.quicksum(
    v_max[j, p] * y_plus[j, p] for j in jours for p in postes
)

# Terme 3 : Pénalités pour demandes de postes non satisfaites (shift_on_requests)
for e, j, p, weight in shift_on_requests:
    objective += weight * (1 - x[e, j, p])

# Terme 4 : Pénalités pour affectations non désirées (shift_off_requests)
for e, j, p, weight in shift_off_requests:
    objective += weight * x[e, j, p]

# Définir l'objectif
model.setObjective(objective, GRB.MINIMIZE)

# Résoudre le modèle
model.optimize()

# Affichage des résultats
if model.status == GRB.OPTIMAL:
    print(f"\n{'='*70}")
    print(f"SOLUTION OPTIMALE TROUVÉE")
    print(f"Valeur de l'objectif : {model.objVal:.2f}")
    print(f"{'='*70}\n")
    
    print("PLANNING DES EMPLOYÉS :")
    print(f"{'-'*70}")
    for e in employees:
        line = f"Employé {e:2s}: "
        for j in jours:
            assigned = [p for p in postes if x[e, j, p].X > 0.5]
            line += f"{assigned[0] if assigned else '--':2s} "
        print(line)
    
    print(f"\n{'='*70}")
    print("COUVERTURE DES POSTES :")
    print(f"{'='*70}")
    for j in jours:
        print(f"\nJour {j:2d}:")
        for p in postes:
            nb_assigned = int(sum(x[e, j, p].X for e in employees))
            required = ujp.get((j, p), 0)
            deficit = int(y_minus[j, p].X)
            surplus = int(y_plus[j, p].X)
            status = "✓" if deficit == 0 and surplus == 0 else "✗"
            print(f"  Poste {p}: {nb_assigned}/{required} (déficit={deficit}, surplus={surplus}) {status}")
else:
    print(f"Statut de résolution : {model.status}")
    if model.status == GRB.INFEASIBLE:
        print("Le modèle est infaisable")