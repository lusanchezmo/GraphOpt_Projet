import os
os.environ['GRB_LICENSE_FILE'] = 'C:\\gurobi1302\\win64\\bin\\gurobi.lic' # !!! ATTENTION : change this path 

import gurobipy as grb
from gurobipy import GRB
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timedelta

nom_fichier = './instances/instance2.txt'
from verification import verification_independante_totale
from lecture import transformer_donnees_fichier


# Données 
donnees = transformer_donnees_fichier(nom_fichier)

# Datos transformados
horizon = donnees['horizon']
jours = list(range(horizon))
weekends = list(range(horizon // 7))

employees = donnees['employees']
postes = donnees['postes']
duree_poste = donnees['duree_poste']
incom = donnees['incom']
params = donnees['params']
mmax = donnees['mmax']
ujp = donnees['ujp']
days_off = donnees['days_off']

# Poids pour le manque et l'excédent de personnel
v_min = {(j, p): 100 for j in jours for p in postes}
v_max = {(j, p): 1 for j in jours for p in postes}

# Demandes de postes (shift_on_requests)
shift_on_requests = donnees['shift_on_requests']

# Demandes de ne PAS travailler (shift_off_requests)
shift_off_requests = donnees['shift_off_requests']




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
            days_off2 = j in days_off.get(e, [])
            line += "XX " if days_off2 else f"{assigned[0] if assigned else '--':2s} "
            #line += f"{assigned[0] if assigned else '--':2s} "
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
            #print(f"  Poste {p}: {nb_assigned}/{required} (déficit={deficit}, surplus={surplus}) {status}")
else:
    print(f"Statut de résolution : {model.status}")
    if model.status == GRB.INFEASIBLE:
        print("Le modèle est infaisable")


# Lancement de l'audit
if model.status == GRB.OPTIMAL:
    verification_independante_totale(employees, jours, postes, params, mmax, duree_poste, incom, ujp, days_off, x)
    
#_________________________________________debut_sauvegarde_______________________________________________

# ==========================================================
# OUTILS XML
# ==========================================================

def prettify(elem):
    rough_string = ET.tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")


def day_to_date(start_date, day):
    return (
        start_date + timedelta(days=day)
    ).strftime("%Y-%m-%d")


# ==========================================================
# EXPORT .ROS
# ==========================================================

def export_solution_to_ros(
    filename,
    start_date,
    horizon,
    employees,
    postes,
    duree_poste,
    ujp,
    assignments
):

    root = ET.Element(
        "SchedulingPeriod",
        {
            "xmlns:xsi":
                "http://www.w3.org/2001/XMLSchema-instance",

            "xsi:noNamespaceSchemaLocation":
                "SchedulingPeriod-3.0.xsd"
        }
    )

    # ======================================================
    # DATES
    # ======================================================

    ET.SubElement(
        root,
        "StartDate"
    ).text = start_date.strftime("%Y-%m-%d")

    ET.SubElement(
        root,
        "EndDate"
    ).text = (
        start_date + timedelta(days=horizon - 1)
    ).strftime("%Y-%m-%d")

    # ======================================================
    # SHIFT TYPES
    # ======================================================

    shift_types = ET.SubElement(root, "ShiftTypes")

    for p in postes:

        shift = ET.SubElement(
            shift_types,
            "Shift",
            {"ID": p}
        )

        ET.SubElement(
            shift,
            "Label"
        ).text = p

        ET.SubElement(
            shift,
            "Duration"
        ).text = str(duree_poste[p])

    # ======================================================
    # EMPLOYEES
    # ======================================================

    employees_xml = ET.SubElement(
        root,
        "Employees"
    )
    for e in employees:

        emp = ET.SubElement(
            employees_xml,
            "Employee",
            {"ID": e}
        )

        ET.SubElement(
            emp,
            "Name"
        ).text = e

    # ======================================================
    # COVER REQUIREMENTS
    # ======================================================

    cover_xml = ET.SubElement(
        root,
        "CoverRequirements"
    )

    for j in range(horizon):

        day_xml = ET.SubElement(
            cover_xml,
            "CoverReq"
        )

        ET.SubElement(
            day_xml,
            "Date"
        ).text = day_to_date(start_date, j)

        for p in postes:

            cover = ET.SubElement(
                day_xml,
                "Cover"
            )

            ET.SubElement(
                cover,
                "Shift"
            ).text = p

            ET.SubElement(
                cover,
                "CoverResource"
            ).text = str(ujp[(j, p)])

    # ======================================================
    # ASSIGNMENTS
    # ======================================================

    assignments_xml = ET.SubElement(
    root,
    "FixedAssignments"
)


    for (e, j, p) in assignments:

        employee_xml = ET.SubElement(
            assignments_xml,
            "Employee"
        )

        ET.SubElement(
            employee_xml,
            "EmployeeID"
        ).text = e

        assign_xml = ET.SubElement(
            employee_xml,
            "Assign"
        )

        ET.SubElement(
            assign_xml,
            "Date"
        ).text = day_to_date(start_date, j)

        ET.SubElement(
            assign_xml,
            "Shift"
        ).text = p

    # ======================================================
    # SAVE
    # ======================================================

    xml_string = prettify(root)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_string)

    print(f"\n[OK] Fichier .ros genere : {filename}")


if model.status == GRB.OPTIMAL:
        # =====================================================
    # EXTRACTION DES AFFECTATIONS
    # =====================================================

    assignments = []

    for e in employees:
        for j in jours:
            for p in postes:

                if x[e, j, p].X > 0.5:

                    assignments.append((e, j, p))

    # =====================================================
    # EXPORT XML .ROS
    # =====================================================

    start_date = datetime(2026, 5, 4)

    export_solution_to_ros(
        filename=nom_fichier[12:21]+'_solution.ros', # './instances/instance2.txt'
        start_date=start_date,
        horizon=horizon,
        employees=employees,
        postes=postes,
        duree_poste=duree_poste,
        ujp=ujp,
        assignments=assignments
    )
    #_________________________________________fin_sauvegarde_______________________________________________
