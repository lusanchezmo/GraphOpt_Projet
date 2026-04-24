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
requests_on = [('A',5,'L',1), ('A',6,'L',1), ('N',8,'E',3)]
days_off = {'A': [3], 'B': [1], 'E': [1], 'I': [0]}



# Modèle
model = grb.Model("Probleme")

# Variables
x = model.addVars(employees, jours, postes, vtype=GRB.BINARY, name="x")
w = model.addVars(employees, jours, vtype=GRB.BINARY, name="work")
y_minus = model.addVars(jours, postes, vtype=GRB.INTEGER, name="y_minus")
y_plus = model.addVars(jours, postes, vtype=GRB.INTEGER, name="y_plus")
we_worked = model.addVars(employees, weekends, vtype=GRB.BINARY, name="we")

# constraints

model.addConstrs((x.sum(e, j, '*') == w[e, j] for e in employees for j in jours), "MaxOneShift")

for e in employees:
    for j in range(horizon - 1):
        for p in postes:
            for p_next in incom[p]:
                model.addConstr(x[e, j, p] + x[e, j+1, p_next] <= 1, f"Incompatibility_{e}_{j}_{p}_{p_next}")

for e in employees:
    for p in postes:
        model.addConstr(x.sum(e, '*', p) <= mmax[e][p], name=f"C3_{e}_{p}")

for e in employees:
    total_min = grb.quicksum(x[e, j, p] * duree_poste[p] for j in jours for p in postes)
    model.addConstr(total_min >= params[e][0], f"MinTime_{e}")
    model.addConstr(total_min <= params[e][1], f"MaxTime_{e}")

# c5 c6 et c7
for e in employees:
    min_c = params[e][3]
    r_min = params[e][4]
    max_c = params[e][2]

    # C5 : Max consécutifs — cas j=0
    for j in range(horizon - max_c):
        model.addConstr(grb.quicksum(w[e, k] for k in range(j, j + max_c + 1)) <= max_c)

    # C6 : Min consécutifs — cas j=0
    model.addConstr(
        grb.quicksum(w[e, k] for k in range(min(min_c, horizon))) >= min_c * w[e, 0]
    )
    # C6 : Min consécutifs — cas général
    for j in range(1, horizon - min_c + 1):
        model.addConstr(
            grb.quicksum(w[e, k] for k in range(j, j + min_c))
            >= min_c * (w[e, j] - w[e, j-1])
        )

    # C7 : Min repos consécutifs — cas j=0 (début de repos dès j=0)
    model.addConstr(
        grb.quicksum(1 - w[e, k] for k in range(min(r_min, horizon))) >= r_min * (1 - w[e, 0])
    )
    # C7 : Min repos consécutifs — cas général (transition travail→repos en j)
    for j in range(1, horizon - r_min + 1):
        model.addConstr(
            grb.quicksum(1 - w[e, k] for k in range(j, j + r_min))
            >= r_min * (w[e, j-1] - w[e, j])
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
