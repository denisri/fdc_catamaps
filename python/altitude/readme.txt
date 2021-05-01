source:
https://fr-fr.topographic-map.com/maps/r3/Paris/
filtre: carto/light
zoom à fond
snapshots avec échelle
fichier .json fait main pour chacun avec alt min et max

assemblage en svg: assemblage.svg

filtrage en enlevant l'intensité:
filt_intens.py

réécriture du svg avec les cartes transformées:

replace_svg.py

ouvrir altitude/real/assemblage.svg
sélectionner le groupe, sauver la sélection en .png:
altitude/real/alt_image.png

