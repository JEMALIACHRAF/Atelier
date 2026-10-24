s = open('build_report.py', encoding='utf8').read()


def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b, 1)


rep('para("Sur donnees publiques, aucune avance de Capgemini Invent n\'est etablie ; le defi principal est d\'etre visible.", italic=True, size=13)',
    'para("Sur donnees publiques, Invent n\'a aucune avance IA etablie en Europe ; son vrai defi est d\'etre visible.", italic=True, size=13)')
# exec summary
rep('cette invisibilite est en soi un probleme de positionnement [D66, S66, S67].")',
    'cette invisibilite est en soi un probleme de positionnement [D66, S66, S67].")\npara("Un seul signal d\'avance apparait, la souverainete europeenne, et il ne contredit pas la these : il existe au niveau groupe, pas Invent [D66], et il est non conclusif. Le groupe compte 2 partenaires souverains distincts (Mistral, Bleu) et 1 offre combinee (SAP-Bleu-Mistral) [D22, non verifie a la source primaire], contre 1 partenariat pour Accenture [D23] ; BCG X et Deloitte sont data not found ; McKinsey liste Mistral et Aleph Alpha dans son ecosysteme [D24, D63]. Ce n\'est pas une avance etablie.")')
rep('"Non conclusive (indicatif 3, parite avec Deloitte) [D59, D62]"', '"Non conclusive (indicatif 3, parite indicative avec Deloitte seulement) [D59, D62]"')
rep('Elle est contestee par l\'accord Accenture-Mistral de fevrier 2026 [S18] et par l\'avance de McKinsey sur la remuneration au resultat [D42].',
    'Elle est contestee par l\'accord Accenture-Mistral de fevrier 2026 [S18] et par l\'avance de McKinsey sur la remuneration au resultat [D42, non verifie a la source primaire].')
rep('rich([("Recommandation principale : ", True), ("relancer l\'etude en mode standard (4 semaines) avant toute communication de positionnement.", False)])',
    'rich([("4 decisions pour Invent (section 7) : ", True), ("(1) lancer un chantier d\'attribution a 6 mois (baseline 0 actif IA attribue [D66], cible >= 2) ; (2) soumettre l\'angle souverain agentique au test go/no-go (T1-T2 2027) ; (3) ne pas construire le positionnement sur l\'echelle ni sur le seul outcome-based ; (4) relancer l\'etude en mode standard (4 semaines) avant toute communication de positionnement.", False)])')
# D2/H2.2
rep('McKinsey affiche des alliances avec les 3 hyperscalers sans termes [D63]; BCG X [D64]', 'McKinsey affiche des alliances avec les 3 hyperscalers sans termes [D63]; BCG X [D64]') if False else None
rep('"3 liens souverains groupe vs 1 Accenture [D22, D23] ; rien attribue a Invent [D66] ; contre-indice S18."',
    '"Groupe : 2 partenaires souverains distincts + 1 offre combinee [D22, non verifie a la source primaire] vs 1 Accenture [D23] ; McKinsey liste Mistral et Aleph Alpha (listing, pas accord) [D24, D63] ; rien attribue a Invent [D66] ; contre-indice S18."')
rep('McKinsey ~1/3 du revenu [D42, S37, non verifie] ; autres ND', 'McKinsey ~1/3 du revenu [D42, S37, non verifie a la source primaire] ; autres ND')
# section 5
rep('(Mistral, Bleu, SAP-Bleu-Mistral [D22 ; S7-S9])', '(2 partenaires souverains distincts, Mistral et Bleu, plus 1 offre combinee SAP-Bleu-Mistral [D22 ; S7-S9, non verifie a la source primaire])')
rep('"Le groupe a 3 liens souverains contre 1 pour Accenture ; BCG X, McKinsey et Deloitte : data not found [D22, D23, D24].",',
    '"Le groupe compte 2 partenaires souverains distincts (Mistral, Bleu) et 1 offre combinee (SAP-Bleu-Mistral) [D22, non verifie a la source primaire], contre 1 partenariat pour Accenture [D23] ; BCG X et Deloitte : data not found [D24].",')
rep('    "65 % des repondants', '    "McKinsey liste Mistral AI et Aleph Alpha dans son ecosysteme : un listing, pas un accord, mais les concurrents ne sont pas absents du terrain souverain [D24, D63].",\n    "65 % des repondants')
rep('[D42, S37, non verifie au primaire] et a lance', '[D42, S37, non verifie a la source primaire] et a lance')
# section 6
rep('("Souverainete :", "l\'avantage suppose du groupe s\'erode (accord Accenture-Mistral [S18])."),',
    '("Souverainete :", "l\'avantage suppose du groupe s\'erode (accord Accenture-Mistral [S18], etude Accenture [S19]) ; McKinsey liste Mistral et Aleph Alpha (listing, pas accord) [D24, D63] ; le comptage du groupe est 2 partenaires distincts + 1 offre combinee, pas 3 partenaires independants [D22, non verifie a la source primaire]."),')
rep('("Outcome-based :", "McKinsey ~1/3 du revenu [D42] ;', '("Outcome-based :", "McKinsey ~1/3 du revenu [D42, non verifie a la source primaire] ;')
# section 7 / 8
i = s.index('# 7 limites'); j = s.index('# annex methodo')
new = open('report_7_8.txt', encoding='utf8').read()
s = s[:i] + new + s[j:]
rep('d.add_heading("Annexe A. Methodologie et limites", 1)', 'd.add_heading("9. Annexes", 1)\nd.add_heading("Annexe A. Methodologie et limites", 2)')
rep('d.add_heading("Annexe B. Bibliographie (67 sources)", 1)', 'd.add_heading("Annexe B. Bibliographie (67 sources)", 2)')
rep('ce qui est a reverifier', 'ce qui est a reverifier') if False else None
open('build_report.py', 'w', encoding='utf8').write(s)
