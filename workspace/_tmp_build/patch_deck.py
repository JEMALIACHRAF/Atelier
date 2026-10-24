s = open('build_deck.py', encoding='utf8').read()


def rep(a, b):
    global s
    assert a in s, a[:70]
    s = s.replace(a, b, 1)


rep('"Sur donnees publiques, Capgemini Invent n\'a aucune avance IA etablie en Europe : son vrai defi est d\'etre visible", 28', '"Sur donnees publiques, Invent n\'a aucune avance IA etablie en Europe ; son vrai defi est d\'etre visible", 27')
rep('Pre-brief express : les lacunes de donnees sont affichees, pas comblees.", 14', 'Pre-brief express : les lacunes de donnees sont affichees, pas comblees.", 13')
rep('tb(s, 0.7, 0.5, 11,', 'tb(s, 0.7, 3.2, 11.9, 0.45, "Un seul signal d\'avance, la souverainete, existe au niveau groupe et reste non conclusif [D22, D24].", 13, True, RGBColor(0xf0, 0xb0, 0x80))\ntb(s, 0.7, 0.5, 11,')
rep('"IA agentique souveraine europeenne : 3 liens souverains au niveau groupe vs 1 chez Accenture [D22, D23], mais non attribues a Invent [D66]."', '"IA agentique souveraine europeenne : 2 partenaires souverains + 1 offre combinee au niveau groupe [D22, non verifie au primaire] vs 1 chez Accenture [D23] ; McKinsey liste Mistral et Aleph Alpha [D24, D63] ; rien n\'est attribue a Invent [D66]."')
rep('rect(s, x, 3.7, 3.85, 2.6', 'rect(s, x, 3.75, 3.85, 2.75')
rep('tb(s, x + 0.2, 3.9, 3.5, 0.5, h, 16', 'tb(s, x + 0.2, 3.95, 3.5, 0.5, h, 16')
rep('tb(s, x + 0.2, 4.6, 3.5, 1.7, b, 12.5', 'tb(s, x + 0.2, 4.55, 3.5, 1.9, b, 11.5')
rep('rect(s, x, 3.7, 3.85, 0.07, ORG)', 'rect(s, x, 3.75, 3.85, 0.07, ORG)')
rep("L'agentique est devenue un prerequis : 4 cabinets sur 5 ont une offre nommee, aucun n'atteint le niveau 4", "L'agentique est devenue un prerequis : 4 acteurs sur 5 (Capgemini compte au niveau groupe) ont une offre nommee, aucun n'atteint le niveau 4 ; Invent strict n'en a aucune attribuee")
rep("En visibilite, McKinsey est le seul acteur confirme a VivaTech 2025 ; Capgemini publie via le CRI, pas via Invent", "McKinsey est le seul des 5 confirme partenaire VivaTech 2025, Capgemini en est absent ; conferences et reprises presse restent non mesurees")
rep("Face aux 77 000 experts IA d'Accenture, Invent ne peut pas jouer l'echelle : seul retard robuste du benchmark", "Face aux 77 000 professionnels data & IA d'Accenture (definition large, groupe, monde) [D30], Invent ne peut pas jouer l'echelle")
rep('"3 liens souverains groupe (Mistral, Bleu, SAP-Bleu-Mistral) vs 1 Accenture [D22, D23]. Priorite au CMD 2026 [D47]. Demande : 62 % [D45], 61 % [D46], 48 % citent la conformite [D45]."', '"Groupe : 2 partenaires souverains distincts (Mistral, Bleu) + 1 offre combinee SAP-Bleu-Mistral [D22, NON VERIFIE au primaire] vs 1 partenariat Accenture [D23]. Priorite au CMD 2026 [D47]. Demande : 62 % [D45], 61 % [D46], 48 % citent la conformite [D45]."')
rep('"Accord Accenture-Mistral, fev. 2026 [D23, S18]. 62 % issu d\'une etude Accenture ; 65 % ne peuvent pas se passer de non-europeens ; aucune etude independante sur l\'AI Act [D45, DP17]. McKinsey ~1/3 outcome-based [D42]. Actifs non attribues [D66]."', '"Accord Accenture-Mistral, fev. 2026 [D23, S18]. McKinsey liste Mistral et Aleph Alpha (listing, pas accord) [D24, D63]. 62 % = etude Accenture ; 65 % ne peuvent pas se passer de non-europeens ; pas d\'etude independante sur l\'AI Act [D45, DP17]. McKinsey ~1/3 outcome-based [D42, NON VERIFIE au primaire]. Non attribue a Invent [D66]."')
rep('callout(s, 4.75, 2.35, 4.0, 3.0, "Contre", ', 'callout(s, 4.75, 2.35, 4.0, 3.1, "Contre", ')
rep('CRIT, 11)', 'CRIT, 10)')
rep('Source : D22-D24, D42, D45-D47, D66', 'Source : D22-D24, D42, D45-D47, D63, D66')
rep('D45 = etude commanditee par Accenture ; D42 non verifie au primaire.', 'D45 = etude commanditee par Accenture ; D22 (S7-S9) et D42 (S37) non verifies au primaire.')
i = s.index('# 9\n'); j = s.index('prs.save')
new = open('slides_9_10.txt', encoding='utf8').read()
s = s[:i] + new + s[j:]
open('build_deck.py', 'w', encoding='utf8').write(s)
